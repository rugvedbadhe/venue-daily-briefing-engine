# Venue Daily Briefing Generator
**Built by Rugved Badhe · Python · Streamlit · No external AI APIs**

A rule-based analytics engine that transforms raw venue performance data into sharp, structured executive briefings — deterministically, with no AI black box.

## What it does
Input yesterday's venue data and the engine runs five algorithms to interpret performance and generate a structured briefing:

**Performance Summary** · **Operational Highlights** · **Flags & Action Items** · **Today's Outlook**

## The Engine — Five Algorithms

### 1. Day Classifier & Dynamic Target Adjuster (`preprocessor.py`)
Classifies the day type (Weekday / Weekend / Public Holiday / Post-Event / Pre-Event) and adjusts the flat revenue target using empirically-defined day-type multipliers. Performance is always measured against a contextually appropriate benchmark — not a misleading flat number.

### 2. Weighted Performance Scorer (`analyser.py`)
Combines three metrics into a single 0–100 performance score with a tier label (Critical → Exceptional):
- Revenue vs adjusted target (50% weight)
- Covers vs expected throughput (30% weight)
- Average spend vs benchmark (20% weight)

### 3. Z-Score Anomaly Detector (`analyser.py`)
Compares today's revenue against a 30-day rolling baseline using Z-score statistics:
`Z = (x - μ) / σ`
If |Z| > 1.5, the day is flagged as statistically anomalous — above or below the norm.

### 4. Linear Regression Trend Detector (`analyser.py`)
Fits a degree-1 polynomial (NumPy polyfit) over the last 7 days of revenue data. The slope determines trend direction and strength:
- Slope > +200/day → Improving
- Slope < -200/day → Declining
- |slope| < 50/day → Stable

### 5. Keyword Sentiment Classifier (`analyser.py`)
Rule-based NLP on staff notes. Scans for positive and negative signal keywords and returns a sentiment score (0–100) with matched keywords — passed directly into the briefing as operational context.

## Architecture

```
User inputs (Streamlit)
    ↓
preprocessor.py   — Day classifier, dynamic target adjuster
    ↓
analyser.py       — Weighted scorer, Z-score, regression, sentiment
    ↓
generator.py      — Signal-driven template engine
    ↓
Formatted executive briefing
```

Every output sentence is traceable to a specific input signal and algorithm decision. No randomness. No black box.

## Run Locally

```bash
pip install -r requirements.txt
streamlit run app.py
```

