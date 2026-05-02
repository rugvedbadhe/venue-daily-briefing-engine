"""
preprocessor.py
---------------
Day classifier and dynamic target adjuster.

Answers: "Are we measuring today's performance against
the right benchmark?"

A flat daily target is misleading — Fridays naturally
outperform Mondays. This module classifies the day type
and adjusts the target using empirically-defined multipliers
so performance is always contextually appropriate.
"""

import datetime

# ── DAY TYPE MULTIPLIERS ─────────────────────────────────────────
# These represent how much revenue a given day type typically
# generates relative to the baseline (Tuesday = 1.0).
# Tune these to match real venue history.
DAY_MULTIPLIERS = {
    "Monday":        0.88,
    "Tuesday":       1.00,   # baseline
    "Wednesday":     1.05,
    "Thursday":      1.15,
    "Friday":        1.45,
    "Saturday":      1.75,
    "Sunday":        1.30,
    "Public Holiday": 1.20,  # depends on venue — adjust per property
    "Post-Event":    1.35,
    "Pre-Event":     1.25,
}

# ── PUBLIC HOLIDAYS (AU) ─────────────────────────────────────────
# Extend this list as needed for your state
AU_PUBLIC_HOLIDAYS_2026 = {
    datetime.date(2026, 1, 1),   # New Year's Day
    datetime.date(2026, 1, 26),  # Australia Day
    datetime.date(2026, 4, 3),   # Good Friday
    datetime.date(2026, 4, 6),   # Easter Monday
    datetime.date(2026, 4, 25),  # ANZAC Day
    datetime.date(2026, 6, 8),   # King's Birthday (NSW)
    datetime.date(2026, 8, 3),   # Bank Holiday (NSW)
    datetime.date(2026, 10, 5),  # Labour Day (NSW)
    datetime.date(2026, 12, 25), # Christmas Day
    datetime.date(2026, 12, 26), # Boxing Day
    datetime.date(2026, 12, 28), # Boxing Day substitute
}


def classify_day(report_date: datetime.date, special_event: str = "") -> str:
    """
    Classify the day type based on date and optional event context.

    Args:
        report_date: The date being reported on
        special_event: Free text from the weather/events field

    Returns:
        Day type string (e.g. "Friday", "Public Holiday", "Post-Event")
    """
    # Check public holiday first — overrides weekday classification
    if report_date in AU_PUBLIC_HOLIDAYS_2026:
        return "Public Holiday"

    # Check for event context in free text
    event_lower = special_event.lower()
    post_event_keywords = ["post-event", "post event", "after the game",
                           "after the concert", "day after", "recovery"]
    pre_event_keywords  = ["pre-event", "pre event", "before the game",
                           "concert tonight", "event tonight", "finals tonight",
                           "game tonight"]

    for kw in post_event_keywords:
        if kw in event_lower:
            return "Post-Event"
    for kw in pre_event_keywords:
        if kw in event_lower:
            return "Pre-Event"

    # Default to weekday name
    return report_date.strftime("%A")


def adjust_target(base_target: float, day_type: str) -> float:
    """
    Adjust the flat revenue target based on day type.

    Args:
        base_target: The manager-entered daily target ($)
        day_type: Classified day type string

    Returns:
        Adjusted target ($) rounded to nearest dollar
    """
    multiplier = DAY_MULTIPLIERS.get(day_type, 1.0)
    return round(base_target * multiplier)


def preprocess(
    report_date: datetime.date,
    base_target: float,
    special_event: str = ""
) -> dict:
    """
    Run full pre-processing pipeline.

    Returns a context dict consumed by the analyser.
    """
    day_type   = classify_day(report_date, special_event)
    adj_target = adjust_target(base_target, day_type)
    multiplier = DAY_MULTIPLIERS.get(day_type, 1.0)

    return {
        "day_type":          day_type,
        "day_of_week":       report_date.strftime("%A"),
        "is_weekend":        report_date.weekday() >= 5,
        "is_public_holiday": report_date in AU_PUBLIC_HOLIDAYS_2026,
        "base_target":       base_target,
        "adjusted_target":   adj_target,
        "multiplier":        multiplier,
    }
