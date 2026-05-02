"""
analyser.py
-----------
Four-algorithm analytics engine.

Algorithms:
  1. Weighted Performance Scorer  — overall 0-100 score + tier
  2. Z-Score Anomaly Detector     — statistical outlier vs 30-day history
  3. Linear Regression Trend      — NumPy slope over last 7 days
  4. Keyword Sentiment Classifier — operational mood from staff notes
"""

import csv
import datetime
import math
import os
import numpy as np
from pathlib import Path

# ── PATHS ────────────────────────────────────────────────────────
BASE_DIR    = Path(__file__).resolve().parent.parent
HISTORY_CSV = BASE_DIR / "data" / "history.csv"

# ── 1. WEIGHTED PERFORMANCE SCORER ───────────────────────────────
# Weights must sum to 1.0
WEIGHTS = {
    "revenue_variance": 0.50,   # most important signal
    "covers_variance":  0.30,
    "avg_spend":        0.20,
}

TIER_THRESHOLDS = {
    "Exceptional": 85,
    "Strong":      70,
    "On Track":    55,
    "Below":       40,
    "Critical":     0,
}

# Benchmark avg spend per cover ($) — adjust per venue
AVG_SPEND_BENCHMARK = 45.0


def _score_component(actual: float, target: float) -> float:
    """
    Score a single metric component on a 0-100 scale.
    Linear interpolation: at target = 70 pts, at +20% = 100, at -30% = 0.
    """
    if target <= 0:
        return 50.0
    ratio = actual / target
    # Map ratio to 0-100: ratio=1.0 → 70, ratio=1.2 → 100, ratio=0.7 → 0
    score = (ratio - 0.7) / (1.2 - 0.7) * 100
    return max(0.0, min(100.0, score))


def weighted_score(
    revenue_actual:  float,
    adjusted_target: float,
    covers:          int,
    expected_covers: int,
    avg_spend:       float,
) -> dict:
    """
    Compute weighted performance score.

    Args:
        revenue_actual:  Today's actual revenue
        adjusted_target: Day-type-adjusted revenue target
        covers:          Actual covers served
        expected_covers: Expected covers (derived from target / avg_spend_benchmark)
        avg_spend:       Actual average spend per cover

    Returns:
        dict with score, tier, component scores, and variance values
    """
    rev_score     = _score_component(revenue_actual, adjusted_target)
    covers_score  = _score_component(covers, expected_covers) if expected_covers > 0 else 50.0
    spend_score   = _score_component(avg_spend, AVG_SPEND_BENCHMARK)

    total = (
        rev_score    * WEIGHTS["revenue_variance"] +
        covers_score * WEIGHTS["covers_variance"]  +
        spend_score  * WEIGHTS["avg_spend"]
    )
    total = round(total, 1)

    # Determine tier
    tier = "Critical"
    for label, threshold in TIER_THRESHOLDS.items():
        if total >= threshold:
            tier = label
            break

    variance_abs = revenue_actual - adjusted_target
    variance_pct = (variance_abs / adjusted_target * 100) if adjusted_target > 0 else 0.0

    return {
        "score":             total,
        "tier":              tier,
        "revenue_score":     round(rev_score, 1),
        "covers_score":      round(covers_score, 1),
        "spend_score":       round(spend_score, 1),
        "variance_abs":      round(variance_abs),
        "variance_pct":      round(variance_pct, 1),
        "avg_spend":         round(avg_spend, 2),
        "avg_spend_vs_bench": round(avg_spend - AVG_SPEND_BENCHMARK, 2),
    }


# ── 2. Z-SCORE ANOMALY DETECTOR ──────────────────────────────────
Z_THRESHOLD = 1.5   # flag if |z| > 1.5 standard deviations


def _load_history(field: str = "revenue") -> list[float]:
    """Load historical values from CSV for the specified field."""
    if not HISTORY_CSV.exists():
        return []
    values = []
    with open(HISTORY_CSV, newline="") as f:
        reader = csv.DictReader(f)
        for row in reader:
            try:
                values.append(float(row[field]))
            except (KeyError, ValueError):
                pass
    return values


def z_score_anomaly(today_value: float, field: str = "revenue") -> dict:
    """
    Compare today's value against 30-day rolling history using Z-score.

    Z = (x - μ) / σ

    Args:
        today_value: Today's actual value (revenue or covers)
        field:       Which historical field to compare against

    Returns:
        dict with z_score, is_anomaly, direction, mean, std
    """
    history = _load_history(field)

    if len(history) < 7:
        return {
            "z_score":    0.0,
            "is_anomaly": False,
            "direction":  "neutral",
            "mean":       today_value,
            "std":        0.0,
            "note":       "Insufficient history (<7 days)",
        }

    arr  = np.array(history)
    mean = float(np.mean(arr))
    std  = float(np.std(arr))

    if std == 0:
        z = 0.0
    else:
        z = (today_value - mean) / std

    is_anomaly = abs(z) > Z_THRESHOLD
    direction  = "above" if z > 0 else "below"

    return {
        "z_score":    round(z, 2),
        "is_anomaly": is_anomaly,
        "direction":  direction,
        "mean":       round(mean),
        "std":        round(std),
        "pct_vs_mean": round((today_value - mean) / mean * 100, 1) if mean > 0 else 0.0,
    }


# ── 3. LINEAR REGRESSION TREND ───────────────────────────────────
TREND_WINDOW = 7   # days to use for regression


def linear_trend(field: str = "revenue") -> dict:
    """
    Fit a linear regression over the last N days of history.

    Uses NumPy polyfit (degree 1) — fits y = mx + b where x is day
    index (0, 1, ... N-1) and y is the field value.

    Returns slope m: positive = upward trend, negative = downward.
    """
    history = _load_history(field)

    if len(history) < TREND_WINDOW:
        return {
            "slope":        0.0,
            "trend":        "insufficient data",
            "trend_label":  "Unknown",
            "r_squared":    0.0,
            "window_days":  TREND_WINDOW,
        }

    window = np.array(history[-TREND_WINDOW:])
    x      = np.arange(len(window), dtype=float)
    y      = window

    # polyfit returns [slope, intercept]
    coeffs     = np.polyfit(x, y, 1)
    slope      = float(coeffs[0])
    intercept  = float(coeffs[1])

    # R-squared — how well the line fits
    y_pred     = slope * x + intercept
    ss_res     = float(np.sum((y - y_pred) ** 2))
    ss_tot     = float(np.sum((y - np.mean(y)) ** 2))
    r_squared  = 1 - (ss_res / ss_tot) if ss_tot > 0 else 0.0

    # Classify trend direction and strength
    if abs(slope) < 50:
        trend_label = "Stable"
        trend       = "stable"
    elif slope > 0:
        trend_label = "Improving" if slope > 200 else "Slightly Improving"
        trend       = "improving"
    else:
        trend_label = "Declining" if slope < -200 else "Slightly Declining"
        trend       = "declining"

    return {
        "slope":        round(slope),
        "trend":        trend,
        "trend_label":  trend_label,
        "r_squared":    round(r_squared, 3),
        "window_days":  TREND_WINDOW,
    }


# ── 4. KEYWORD SENTIMENT CLASSIFIER ──────────────────────────────
NEGATIVE_KEYWORDS = [
    "sick", "call in", "called in", "short-staffed", "short staffed",
    "understaffed", "no show", "no-show", "complaint", "complaints",
    "incident", "fight", "altercation", "broken", "not working",
    "late", "walked out", "quit", "refused", "spill", "injury",
    "theft", "missing", "overcharged", "error", "mistake",
]

POSITIVE_KEYWORDS = [
    "smooth", "great team", "full team", "no issues", "no complaints",
    "excellent", "efficient", "positive feedback", "great feedback",
    "good service", "busy", "on time", "early", "ahead of schedule",
    "team player", "went well", "no incidents",
]


def sentiment_classify(text: str) -> dict:
    """
    Rule-based keyword sentiment classifier.

    Scans free text for positive and negative signal words.
    Returns a sentiment score and matched keywords.

    Score: starts at 50 (neutral), +10 per positive, -10 per negative
    Clamped to 0-100.
    """
    if not text or not text.strip():
        return {
            "sentiment":          "neutral",
            "sentiment_score":    50,
            "positive_hits":      [],
            "negative_hits":      [],
            "negative_count":     0,
            "positive_count":     0,
        }

    text_lower = text.lower()
    pos_hits = [kw for kw in POSITIVE_KEYWORDS if kw in text_lower]
    neg_hits = [kw for kw in NEGATIVE_KEYWORDS if kw in text_lower]

    score = 50 + (len(pos_hits) * 10) - (len(neg_hits) * 10)
    score = max(0, min(100, score))

    if score >= 65:
        sentiment = "positive"
    elif score <= 35:
        sentiment = "negative"
    else:
        sentiment = "neutral"

    return {
        "sentiment":       sentiment,
        "sentiment_score": score,
        "positive_hits":   pos_hits,
        "negative_hits":   neg_hits,
        "negative_count":  len(neg_hits),
        "positive_count":  len(pos_hits),
    }


# ── MASTER ANALYSER ───────────────────────────────────────────────
def analyse(
    revenue_actual:  float,
    adjusted_target: float,
    covers:          int,
    staff_notes:     str,
) -> dict:
    """
    Run all four algorithms and return a unified signals dict.

    This is the single entry point consumed by generator.py
    """
    avg_spend       = (revenue_actual / covers) if covers > 0 else 0.0
    expected_covers = int(adjusted_target / AVG_SPEND_BENCHMARK)

    perf    = weighted_score(revenue_actual, adjusted_target, covers, expected_covers, avg_spend)
    anomaly = z_score_anomaly(revenue_actual, "revenue")
    trend   = linear_trend("revenue")
    sentiment = sentiment_classify(staff_notes)

    return {
        "performance": perf,
        "anomaly":     anomaly,
        "trend":       trend,
        "sentiment":   sentiment,
        "meta": {
            "revenue_actual":  revenue_actual,
            "adjusted_target": adjusted_target,
            "covers":          covers,
            "avg_spend":       round(avg_spend, 2),
            "expected_covers": expected_covers,
        }
    }
