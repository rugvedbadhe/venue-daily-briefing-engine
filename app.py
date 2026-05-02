"""
app.py
------
Venue Daily Briefing Generator
Built by Rugved Badhe

Streamlit UI that wires together the three-module engine:
  preprocessor → analyser → generator

No external AI APIs. All intelligence is in the engine.
"""

import streamlit as st
import datetime
import csv
import os
from pathlib import Path
from engine import preprocess, analyse, generate_briefing

# ── PAGE CONFIG ──────────────────────────────────────────────────
st.set_page_config(
    page_title="Venue Daily Briefing",
    page_icon="🏨",
    layout="wide",
    initial_sidebar_state="collapsed"
)

BASE_DIR    = Path(__file__).resolve().parent
HISTORY_CSV = BASE_DIR / "data" / "history.csv"

# ── STYLES ───────────────────────────────────────────────────────
st.markdown("""
<style>
@import url('https://fonts.googleapis.com/css2?family=Playfair+Display:wght@400;600;700&family=DM+Sans:wght@300;400;500&display=swap');

html, body, [class*="css"] { font-family: 'DM Sans', sans-serif; }

.stApp { background: #0f0e0c; color: #e8e2d9; }

.hero { text-align:center; padding:48px 0 32px 0; border-bottom:1px solid #2a2520; margin-bottom:40px; }
.hero-eyebrow { font-size:11px; font-weight:500; letter-spacing:0.2em; text-transform:uppercase; color:#c9a96e; margin-bottom:12px; }
.hero-title { font-family:'Playfair Display',serif; font-size:42px; font-weight:700; color:#f5f0e8; margin:0 0 10px 0; line-height:1.15; }
.hero-sub { font-size:14px; color:#6b6459; margin:0; }

.section-label { font-size:10px; font-weight:500; letter-spacing:0.15em; text-transform:uppercase; color:#c9a96e; margin-bottom:16px; margin-top:28px; padding-bottom:8px; border-bottom:1px solid #2a2520; }

.stTextInput>div>div>input,
.stTextArea>div>div>textarea,
.stNumberInput>div>div>input {
    background:#1a1814 !important; border:1px solid #2a2520 !important;
    border-radius:6px !important; color:#e8e2d9 !important;
    font-family:'DM Sans',sans-serif !important;
}
.stTextInput>div>div>input:focus,
.stTextArea>div>div>textarea:focus {
    border-color:#c9a96e !important; box-shadow:0 0 0 1px #c9a96e33 !important;
}

.stButton>button {
    background:#c9a96e !important; color:#0f0e0c !important;
    border:none !important; border-radius:6px !important;
    font-family:'DM Sans',sans-serif !important; font-weight:600 !important;
    font-size:14px !important; letter-spacing:0.05em !important;
    padding:14px 32px !important; width:100% !important;
}
.stButton>button:hover { background:#dfc08a !important; }

.briefing-card { background:#1a1814; border:1px solid #2a2520; border-radius:12px; padding:36px 40px; margin-top:32px; }
.briefing-header { display:flex; justify-content:space-between; align-items:flex-start; margin-bottom:28px; padding-bottom:20px; border-bottom:1px solid #2a2520; }
.briefing-venue { font-family:'Playfair Display',serif; font-size:22px; color:#f5f0e8; margin:0 0 4px 0; }
.briefing-date { font-size:12px; color:#6b6459; letter-spacing:0.08em; }
.briefing-badge { background:#c9a96e22; border:1px solid #c9a96e44; color:#c9a96e; font-size:10px; font-weight:600; letter-spacing:0.12em; text-transform:uppercase; padding:4px 12px; border-radius:20px; }

.metrics-row { display:flex; gap:12px; margin-bottom:28px; flex-wrap:wrap; }
.metric-pill { background:#0f0e0c; border:1px solid #2a2520; border-radius:8px; padding:12px 16px; flex:1; min-width:120px; }
.metric-label { font-size:10px; color:#6b6459; letter-spacing:0.1em; text-transform:uppercase; margin-bottom:4px; }
.metric-value { font-family:'Playfair Display',serif; font-size:20px; color:#f5f0e8; }
.metric-value.positive { color:#7dcea0; }
.metric-value.negative { color:#e87d7d; }

.section-head { font-size:10px; font-weight:600; letter-spacing:0.15em; text-transform:uppercase; color:#c9a96e; margin:24px 0 10px 0; }
.briefing-para { color:#c8c0b4; font-size:14px; line-height:1.8; margin-bottom:12px; }
.briefing-bullet { color:#c8c0b4; font-size:14px; line-height:1.8; padding-left:16px; margin-bottom:6px; }
.briefing-bullet::before { content:"▸ "; color:#c9a96e; }

.score-pill { display:inline-block; padding:6px 16px; border-radius:20px; font-size:12px; font-weight:600; margin-bottom:20px; }
.score-Exceptional { background:#7dcea022; color:#7dcea0; border:1px solid #7dcea044; }
.score-Strong      { background:#7dcea022; color:#7dcea0; border:1px solid #7dcea044; }
.score-On-Track    { background:#c9a96e22; color:#c9a96e; border:1px solid #c9a96e44; }
.score-Below       { background:#e87d4422; color:#e87d44; border:1px solid #e87d4444; }
.score-Critical    { background:#e87d7d22; color:#e87d7d; border:1px solid #e87d7d44; }

label, .stLabel { color:#9b9086 !important; font-size:13px !important; }
</style>
""", unsafe_allow_html=True)

# ── HERO ─────────────────────────────────────────────────────────
st.markdown("""
<div class="hero">
    <div class="hero-eyebrow">Analytics Engine · Five Algorithms · Zero AI APIs</div>
    <div class="hero-title">Venue Daily Briefing</div>
    <p class="hero-sub">Rule-based intelligence that turns raw venue data into sharp executive briefings</p>
</div>
""", unsafe_allow_html=True)

# ── FORM ──────────────────────────────────────────────────────────
col1, col2 = st.columns([1, 1], gap="large")

with col1:
    st.markdown('<div class="section-label">Venue Details</div>', unsafe_allow_html=True)
    venue_name   = st.text_input("Venue Name", placeholder="e.g. The Rydalmere Arms")
    report_date  = st.date_input("Report Date", value=datetime.date.today())
    manager_name = st.text_input("Manager on Duty", placeholder="e.g. Sarah Mitchell")

    st.markdown('<div class="section-label">Financial Performance</div>', unsafe_allow_html=True)
    c1, c2 = st.columns(2)
    with c1:
        revenue_actual = st.number_input("Actual Revenue ($)", min_value=0, value=0, step=500)
    with c2:
        revenue_target = st.number_input("Base Daily Target ($)", min_value=0, value=0, step=500)
    covers     = st.number_input("Total Covers Served", min_value=0, value=0, step=10)
    top_sellers = st.text_area("Top Selling Items", placeholder="e.g. Wagyu burger x42, House red x38", height=80)

with col2:
    st.markdown('<div class="section-label">Operations & Context</div>', unsafe_allow_html=True)
    staff_notes       = st.text_area("Staff & Incidents", placeholder="e.g. 2 staff called in sick. No incidents.", height=80)
    weather_events    = st.text_area("Weather / Special Events", placeholder="e.g. Public holiday, footy finals nearby", height=80)
    upcoming_bookings = st.text_area("Today's Upcoming Bookings", placeholder="e.g. 3 group bookings, private function 7pm", height=80)
    additional_notes  = st.text_area("Additional Notes", placeholder="e.g. Cellar delivery arriving 10am", height=80)

# ── GENERATE ──────────────────────────────────────────────────────
st.markdown("<br>", unsafe_allow_html=True)
generate = st.button("⚡ Generate Executive Briefing")

if generate:
    if not venue_name:
        st.error("Please enter a venue name.")
    elif revenue_actual == 0:
        st.warning("Revenue is zero — please enter yesterday's actual revenue.")
    else:
        with st.spinner("Running analytics engine..."):

            # ── RUN ENGINE ───────────────────────────────────────
            pre     = preprocess(report_date, float(revenue_target), weather_events)
            signals = analyse(float(revenue_actual), pre["adjusted_target"], int(covers), staff_notes)
            briefing = generate_briefing(
                venue_name, report_date, manager_name,
                top_sellers, weather_events, upcoming_bookings,
                additional_notes, pre, signals
            )

            # ── APPEND TO HISTORY ─────────────────────────────────
            try:
                with open(HISTORY_CSV, "a", newline="") as f:
                    writer = csv.writer(f)
                    writer.writerow([report_date.isoformat(), revenue_actual, covers])
            except Exception:
                pass

            # ── RENDER OUTPUT ─────────────────────────────────────
            perf     = signals["performance"]
            anomaly  = signals["anomaly"]
            meta_out = briefing["meta"]

            var_abs  = perf["variance_abs"]
            var_pct  = perf["variance_pct"]
            avg_sp   = meta_out.get("avg_spend", signals["meta"]["avg_spend"])
            tier     = meta_out["tier"]
            score    = meta_out["score"]
            adj_tgt  = pre["adjusted_target"]
            day_type = pre["day_type"]

            var_class  = "positive" if var_abs >= 0 else "negative"
            var_symbol = "▲" if var_abs >= 0 else "▼"
            tier_cls   = tier.replace(" ", "-")

            st.markdown(f"""
<div class="briefing-card">
  <div class="briefing-header">
    <div>
      <div class="briefing-venue">{venue_name}</div>
      <div class="briefing-date">
        {report_date.strftime('%A, %d %B %Y').upper()}
        &nbsp;·&nbsp; DAILY EXECUTIVE BRIEFING
        &nbsp;·&nbsp; MOD: {manager_name or 'Not specified'}
      </div>
    </div>
    <div class="briefing-badge">CONFIDENTIAL</div>
  </div>

  <div class="metrics-row">
    <div class="metric-pill">
      <div class="metric-label">Revenue</div>
      <div class="metric-value">${int(revenue_actual):,}</div>
    </div>
    <div class="metric-pill">
      <div class="metric-label">{day_type} Target</div>
      <div class="metric-value">${int(adj_tgt):,}</div>
    </div>
    <div class="metric-pill">
      <div class="metric-label">vs Target</div>
      <div class="metric-value {var_class}">{var_symbol} ${abs(int(var_abs)):,} ({var_pct:+.1f}%)</div>
    </div>
    <div class="metric-pill">
      <div class="metric-label">Covers</div>
      <div class="metric-value">{covers}</div>
    </div>
    <div class="metric-pill">
      <div class="metric-label">Avg Spend</div>
      <div class="metric-value">${signals['meta']['avg_spend']:.0f}</div>
    </div>
  </div>

  <div class="score-pill score-{tier_cls}">
    Performance Score: {score}/100 &nbsp;·&nbsp; {tier}
  </div>

  <div class="section-head">Performance Summary</div>
  <div class="briefing-para">{briefing['performance_summary']}</div>

  <div class="section-head">Operational Highlights</div>
  {''.join(f'<div class="briefing-bullet">{h}</div>' for h in briefing['operational_highlights'])}

  <div class="section-head">Flags &amp; Action Items</div>
  {''.join(f'<div class="briefing-bullet">{f}</div>' for f in briefing['flags_and_actions'])}

  <div class="section-head">Today\'s Outlook &amp; Priority</div>
  <div class="briefing-para">{briefing['todays_outlook']}</div>

</div>
""", unsafe_allow_html=True)

            # ── DOWNLOAD ──────────────────────────────────────────
            txt = f"""VENUE DAILY BRIEFING
{venue_name} — {report_date.strftime('%d %B %Y')}
Generated by Venue Briefing Engine (Rugved Badhe)
{'='*60}

PERFORMANCE SUMMARY
{briefing['performance_summary']}

OPERATIONAL HIGHLIGHTS
{''.join(f'  • {h}' + chr(10) for h in briefing['operational_highlights'])}
FLAGS & ACTION ITEMS
{''.join(f'  • {f}' + chr(10) for f in briefing['flags_and_actions'])}
TODAY'S OUTLOOK & PRIORITY
{briefing['todays_outlook']}

{'='*60}
Score: {score}/100 ({tier})  |  Day Type: {day_type}  |  Adj. Target: ${int(adj_tgt):,}
"""
            st.download_button(
                "↓ Download Briefing (.txt)",
                data=txt,
                file_name=f"briefing_{venue_name.replace(' ','_')}_{report_date}.txt",
                mime="text/plain"
            )

# ── FOOTER ────────────────────────────────────────────────────────
st.markdown("<br><br>", unsafe_allow_html=True)
st.markdown("""
<div style="text-align:center;color:#3a3530;font-size:11px;letter-spacing:0.08em;padding:20px 0;border-top:1px solid #1a1814;">
  BUILT BY RUGVED BADHE &nbsp;·&nbsp; WEIGHTED SCORER · Z-SCORE · LINEAR REGRESSION · SENTIMENT · DAY CLASSIFIER &nbsp;·&nbsp; 2026
</div>
""", unsafe_allow_html=True)
