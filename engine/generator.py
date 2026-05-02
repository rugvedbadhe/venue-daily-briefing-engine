"""
generator.py
------------
Signal-driven template engine.

Takes the structured signals dict from analyser.py and maps
signal combinations to pre-written sentence templates — building
a coherent, natural-sounding executive briefing with zero AI.

Every output sentence is deterministic and traceable to a
specific input signal and algorithm decision.
"""

from __future__ import annotations
import datetime
import random


# ── TEMPLATE LIBRARY ─────────────────────────────────────────────
# Each key maps a signal state to a list of template strings.
# {placeholders} are filled at render time.
# Multiple templates per state add natural variation.

PERFORMANCE_SUMMARY = {
    "Exceptional": [
        "{venue} delivered an exceptional result on {date}, with revenue of ${revenue:,} against an adjusted target of ${target:,} — a {variance_pct:+.1f}% variance. Performance score: {score}/100.",
        "Outstanding trading at {venue} on {date}: ${revenue:,} revenue, {variance_pct:+.1f}% above the day-adjusted target of ${target:,}. Performance score {score}/100.",
    ],
    "Strong": [
        "{venue} had a strong day on {date}, achieving ${revenue:,} revenue against a {day_type} target of ${target:,} ({variance_pct:+.1f}%). Performance score: {score}/100.",
        "Solid trading at {venue} on {date} — ${revenue:,} revenue, {variance_pct:+.1f}% ahead of the adjusted {day_type} target. Score: {score}/100.",
    ],
    "On Track": [
        "{venue} tracked close to target on {date}, generating ${revenue:,} against a {day_type} target of ${target:,} ({variance_pct:+.1f}%). Performance score: {score}/100.",
        "Performance at {venue} on {date} was broadly on track — ${revenue:,} revenue, {variance_pct:+.1f}% versus the adjusted target. Score: {score}/100.",
    ],
    "Below": [
        "{venue} underperformed on {date}, with revenue of ${revenue:,} falling {variance_pct:.1f}% short of the {day_type} target of ${target:,}. Performance score: {score}/100.",
        "Below-target trading at {venue} on {date}: ${revenue:,} against an adjusted {day_type} target of ${target:,}, a gap of ${variance_abs:,}. Score: {score}/100.",
    ],
    "Critical": [
        "{venue} had a critical underperformance on {date} — ${revenue:,} revenue, {variance_pct:.1f}% below the {day_type} target of ${target:,}. Immediate review recommended. Score: {score}/100.",
        "Significant shortfall at {venue} on {date}: ${revenue:,} actual versus ${target:,} adjusted target ({variance_pct:.1f}%). Performance score: {score}/100 — critical.",
    ],
}

ANOMALY_TEMPLATES = {
    "above": "Revenue was statistically anomalous — {pct_vs_mean:+.1f}% above the 30-day rolling mean of ${mean:,} (Z-score: {z:.2f}).",
    "below": "Revenue was statistically anomalous — {pct_vs_mean:.1f}% below the 30-day rolling mean of ${mean:,} (Z-score: {z:.2f}). Investigate root cause.",
}

TREND_TEMPLATES = {
    "improving":           "7-day revenue trend is improving (slope: +${slope:,}/day), suggesting positive momentum heading into the week.",
    "slightly_improving":  "7-day revenue trend shows a slight upward slope (+${slope:,}/day) — encouraging but not yet significant.",
    "stable":              "7-day revenue trend is stable — consistent trading pattern with no material directional shift.",
    "slightly_declining":  "7-day revenue trend shows a slight downward slope (-${slope:,}/day) — worth monitoring over the next 48 hours.",
    "declining":           "7-day revenue trend is declining (slope: -${slope:,}/day). Three-day review recommended to identify contributing factors.",
}

COVERS_TEMPLATES = {
    "above":  "{covers} covers served, {pct:+.0f}% above expected ({expected} covers at benchmark avg spend).",
    "on":     "{covers} covers served, in line with expected throughput for a {day_type}.",
    "below":  "{covers} covers served, {pct:.0f}% below expected throughput ({expected} covers). Consider whether staffing, capacity or demand was the limiting factor.",
}

AVG_SPEND_TEMPLATES = {
    "high":    "Average spend of ${avg_spend:.2f} per cover — ${diff:+.2f} above the ${benchmark:.0f} benchmark. Strong upsell or premium mix contributing.",
    "on":      "Average spend of ${avg_spend:.2f} per cover — in line with the ${benchmark:.0f} benchmark.",
    "low":     "Average spend of ${avg_spend:.2f} per cover — ${diff:.2f} below the ${benchmark:.0f} benchmark. Review menu mix and upsell performance.",
}

SENTIMENT_TEMPLATES = {
    "positive": "Staff notes are positive — {pos_hits}. Operational conditions were favourable.",
    "neutral":  "Staff notes are neutral. No significant operational issues flagged.",
    "negative": "Staff notes flagged {count} operational concern(s): {neg_hits}. Follow up required.",
}

ACTION_TEMPLATES = {
    "below_revenue":    "Revenue shortfall of ${gap:,} ({pct:.1f}% below adjusted target) — review booking, staffing, and cover data for contributing factors.",
    "critical_revenue": "URGENT: Revenue ${gap:,} below critical threshold. Management review required before end of day.",
    "anomaly_below":    "Statistical anomaly flagged: today's revenue was {pct:.1f}% below the 30-day mean (Z={z:.2f}). Compare against same day last week.",
    "declining_trend":  "Revenue trend declining over 7 days (slope: -${slope:,}/day). Recommend trend review at next management meeting.",
    "negative_staff":   "Operational flags from staff notes: {neg_hits}. Ensure follow-up documented in incident log.",
    "low_covers":       "Cover count below expected ({covers} vs {expected} expected). Check reservation fulfilment and walk-in conversion.",
    "low_avg_spend":    "Average spend ${avg_spend:.2f} below ${benchmark:.0f} benchmark. Review upsell training and menu positioning.",
}

OUTLOOK_TEMPLATES = {
    "busy":    "Today's bookings ({bookings}) indicate a {day_type} with above-average volume. Prioritise floor coverage and kitchen readiness from open.",
    "normal":  "Today's bookings ({bookings}) suggest a typical {day_type}. Maintain standard operating cadence.",
    "quiet":   "Today's bookings ({bookings}) suggest a quieter {day_type}. Opportunity to focus on staff training, deep cleaning, or prep work.",
    "unknown": "Booking volumes not provided. Brief the team on yesterday's performance and set the target for today.",
}

PRIORITY_TEMPLATES = {
    "Exceptional": "Priority: maintain momentum — brief the team on yesterday's result and set the tone for today.",
    "Strong":      "Priority: sustain performance — identify what drove yesterday's result and replicate it today.",
    "On Track":    "Priority: close the small gap — focus on upsell, covers conversion, and consistent service delivery.",
    "Below":       "Priority: recover — address the contributing factors from yesterday and reset expectations with the team.",
    "Critical":    "Priority: immediate recovery plan required — management to review staffing, covers, and revenue data before open.",
}


# ── HELPER FUNCTIONS ─────────────────────────────────────────────
def _pick(templates: list[str], seed: int = 0) -> str:
    """Pick deterministically from a list using day-based seed."""
    random.seed(seed)
    return random.choice(templates)


def _covers_state(covers: int, expected: int) -> str:
    if expected == 0:
        return "on"
    pct = (covers - expected) / expected * 100
    if pct > 10:
        return "above"
    elif pct < -10:
        return "below"
    return "on"


def _spend_state(avg_spend: float, benchmark: float = 45.0) -> str:
    diff = avg_spend - benchmark
    if diff > 3:
        return "high"
    elif diff < -3:
        return "low"
    return "on"


def _trend_key(trend: dict) -> str:
    t = trend.get("trend", "stable")
    if t == "improving":
        return "improving" if abs(trend.get("slope", 0)) > 200 else "slightly_improving"
    elif t == "declining":
        return "declining" if abs(trend.get("slope", 0)) > 200 else "slightly_declining"
    return "stable"


def _bookings_state(bookings_text: str) -> str:
    if not bookings_text or not bookings_text.strip():
        return "unknown"
    low_kw  = ["quiet", "slow", "light", "few", "no bookings"]
    busy_kw = ["full", "busy", "private function", "large group", "sold out", "packed"]
    bl      = bookings_text.lower()
    if any(kw in bl for kw in busy_kw):
        return "busy"
    if any(kw in bl for kw in low_kw):
        return "quiet"
    return "normal"


# ── MASTER GENERATOR ─────────────────────────────────────────────
def generate_briefing(
    venue_name:      str,
    report_date:     datetime.date,
    manager_name:    str,
    top_sellers:     str,
    weather_events:  str,
    upcoming_bookings: str,
    additional_notes: str,
    pre:             dict,   # from preprocessor
    signals:         dict,   # from analyser
) -> dict:
    """
    Generate the full structured executive briefing from signals.

    Returns a dict with four sections:
      - performance_summary
      - operational_highlights (list)
      - flags_and_actions (list)
      - todays_outlook
    """
    perf      = signals["performance"]
    anomaly   = signals["anomaly"]
    trend     = signals["trend"]
    sentiment = signals["sentiment"]
    meta      = signals["meta"]

    tier        = perf["tier"]
    score       = perf["score"]
    revenue     = meta["revenue_actual"]
    target      = meta["adjusted_target"]
    covers      = meta["covers"]
    expected    = meta["expected_covers"]
    avg_spend   = meta["avg_spend"]
    var_abs     = perf["variance_abs"]
    var_pct     = perf["variance_pct"]
    day_type    = pre["day_type"]
    seed        = report_date.toordinal()

    # ── SECTION 1: PERFORMANCE SUMMARY ───────────────────────────
    summary_tmpl = _pick(PERFORMANCE_SUMMARY[tier], seed)
    summary = summary_tmpl.format(
        venue=venue_name,
        date=report_date.strftime("%A, %d %B %Y"),
        revenue=int(revenue),
        target=int(target),
        variance_pct=var_pct,
        variance_abs=abs(int(var_abs)),
        score=score,
        day_type=day_type,
    )

    # Add anomaly sentence if flagged
    if anomaly.get("is_anomaly"):
        a_tmpl = ANOMALY_TEMPLATES[anomaly["direction"]]
        summary += " " + a_tmpl.format(
            pct_vs_mean=anomaly["pct_vs_mean"],
            mean=int(anomaly["mean"]),
            z=anomaly["z_score"],
        )

    # ── SECTION 2: OPERATIONAL HIGHLIGHTS ────────────────────────
    highlights = []

    # Covers
    c_state = _covers_state(covers, expected)
    c_pct   = ((covers - expected) / expected * 100) if expected > 0 else 0
    highlights.append(COVERS_TEMPLATES[c_state].format(
        covers=covers, pct=c_pct, expected=expected, day_type=day_type
    ))

    # Average spend
    s_state = _spend_state(avg_spend)
    highlights.append(AVG_SPEND_TEMPLATES[s_state].format(
        avg_spend=avg_spend, diff=avg_spend - 45.0, benchmark=45.0
    ))

    # Top sellers
    if top_sellers and top_sellers.strip():
        highlights.append(f"Top sellers: {top_sellers}.")

    # Revenue trend
    t_key = _trend_key(trend)
    highlights.append(TREND_TEMPLATES[t_key].format(
        slope=abs(int(trend.get("slope", 0)))
    ))

    # Staff sentiment
    s_tmpl = SENTIMENT_TEMPLATES[sentiment["sentiment"]]
    if sentiment["sentiment"] == "negative":
        highlights.append(s_tmpl.format(
            count=sentiment["negative_count"],
            neg_hits=", ".join(sentiment["negative_hits"])
        ))
    elif sentiment["sentiment"] == "positive":
        highlights.append(s_tmpl.format(
            pos_hits=", ".join(sentiment["positive_hits"])
        ))
    else:
        highlights.append(s_tmpl)

    # Weather / events
    if weather_events and weather_events.strip():
        highlights.append(f"Context: {weather_events}.")

    # ── SECTION 3: FLAGS & ACTION ITEMS ──────────────────────────
    flags = []

    if tier == "Critical":
        flags.append(ACTION_TEMPLATES["critical_revenue"].format(
            gap=abs(int(var_abs)), pct=abs(var_pct)
        ))
    elif tier == "Below":
        flags.append(ACTION_TEMPLATES["below_revenue"].format(
            gap=abs(int(var_abs)), pct=abs(var_pct)
        ))

    if anomaly.get("is_anomaly") and anomaly["direction"] == "below":
        flags.append(ACTION_TEMPLATES["anomaly_below"].format(
            pct=abs(anomaly["pct_vs_mean"]),
            z=abs(anomaly["z_score"])
        ))

    if trend.get("trend") in ("declining",):
        flags.append(ACTION_TEMPLATES["declining_trend"].format(
            slope=abs(int(trend.get("slope", 0)))
        ))

    if sentiment["sentiment"] == "negative" and sentiment["negative_hits"]:
        flags.append(ACTION_TEMPLATES["negative_staff"].format(
            neg_hits=", ".join(sentiment["negative_hits"])
        ))

    if c_state == "below":
        flags.append(ACTION_TEMPLATES["low_covers"].format(
            covers=covers, expected=expected
        ))

    if s_state == "low":
        flags.append(ACTION_TEMPLATES["low_avg_spend"].format(
            avg_spend=avg_spend, benchmark=45.0
        ))

    if additional_notes and additional_notes.strip():
        flags.append(f"Note: {additional_notes}")

    if not flags:
        flags.append("No critical flags. Maintain current operating standards.")

    # ── SECTION 4: TODAY'S OUTLOOK ────────────────────────────────
    b_state  = _bookings_state(upcoming_bookings)
    bookings = upcoming_bookings if upcoming_bookings else "no bookings logged"
    outlook  = OUTLOOK_TEMPLATES[b_state].format(
        bookings=bookings, day_type=report_date.strftime("%A")
    )
    outlook += " " + PRIORITY_TEMPLATES[tier]

    return {
        "performance_summary":   summary,
        "operational_highlights": highlights,
        "flags_and_actions":     flags,
        "todays_outlook":        outlook,
        "meta": {
            "score":    score,
            "tier":     tier,
            "day_type": day_type,
            "manager":  manager_name or "Not specified",
        }
    }
