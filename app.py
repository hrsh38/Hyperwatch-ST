import streamlit as st
from supabase import create_client
from streamlit_echarts import st_echarts
import pandas as pd
from datetime import datetime, timedelta
import pytz

st.set_page_config(page_title="Hyperwatch – ECharts Dashboard", layout="wide")

# === Supabase ===
SUPABASE_URL = st.secrets["SUPABASE_URL"]
SUPABASE_KEY = st.secrets["SUPABASE_KEY"]
supabase = create_client(SUPABASE_URL, SUPABASE_KEY)


# ---------------------------------------------------
# Load snapshots
# ---------------------------------------------------
@st.cache_data(ttl=300)
def load_snapshots():
    resp = (
        supabase.table("cohort_snapshots")
        .select("*")
        .order("timestamp", desc=False)
        .execute()
    )
    df = pd.DataFrame(resp.data)
    if df.empty:
        return df

    # Convert UTC → EST
    df["timestamp"] = pd.to_datetime(df["timestamp"], utc=True)
    df["timestamp"] = df["timestamp"].dt.tz_convert("America/New_York")

    # Format to 12-hour time
    df["time"] = df["timestamp"].dt.strftime("%Y-%m-%d %I:%M:%S")

    return df


df = load_snapshots()

if df.empty:
    st.error("cohort_snapshots table is empty.")
    st.stop()

df = df.sort_values("timestamp")
# Sidebar refresh button
if st.sidebar.button("🔄 Refresh Data"):
    load_snapshots.clear()      # clears cache
    st.experimental_rerun()     # reloads app instantly
# ---------------------------------------------------
# TRADINGVIEW-STYLE DATE / TIME RANGE CONTROLS
# ---------------------------------------------------

st.sidebar.subheader("Time Range")

tv_presets = {
    "1H": timedelta(hours=1),
    "3H": timedelta(hours=3),
    "6H": timedelta(hours=6),
    "12H": timedelta(hours=12),
    "24H": timedelta(hours=24),
    "3D": timedelta(days=3),
    "1W": timedelta(days=7),
    "1M": timedelta(days=30),
    "All": None
}

preset = st.sidebar.selectbox("Quick Range", list(tv_presets.keys()), index=8)

# Calendar picker (TradingView style)
start_date, end_date = st.sidebar.date_input(
    "Custom Date Range",
    value=(df["timestamp"].min().date(), df["timestamp"].max().date())
)

# Apply preset first (overrides calendar)
if tv_presets[preset] is not None:
    cutoff = df["timestamp"].max() - tv_presets[preset]
    df = df[df["timestamp"] >= cutoff]
else:
    # Custom Calendar Range
    start_dt = pd.Timestamp(start_date).tz_localize("America/New_York")
    end_dt = pd.Timestamp(end_date).tz_localize("America/New_York") + timedelta(days=1)
    df = df[(df["timestamp"] >= start_dt) & (df["timestamp"] <= end_dt)]

# ---------------------------------------------------
# PRICE ASSET SELECTOR (BTC / ETH / SOL)
# ---------------------------------------------------
st.sidebar.subheader("Price Asset")

asset_choice = st.sidebar.radio(
    "Show Price For:",
    ["btc", "eth", "sol"],
    index=0
)

asset_labels = {
    "btc": "BTC Price",
    "eth": "ETH Price",
    "sol": "SOL Price"
}

price_colors = {
    "btc": "#00B7FF",
    "eth": "#AA6BFF",
    "sol": "#00FFAB"
}
def classify_bias(value):
    if value <= -0.60:
        return "Very Bearish", "#D32F2F"   # strong red
    elif value <= -0.20:
        return "Bearish", "#F57C00"        # orange-red
    elif value <= 0.20:
        return "Neutral", "#757575"        # gray
    elif value <= 0.60:
        return "Bullish", "#4CAF50"        # green
    else:
        return "Very Bullish", "#2ECC71"   # bright green

cohort_colors = {
    "fish": "#1f77b4",         # blue
    "dolphin": "#ff7f0e",      # orange
    "apex_predator": "#2ca02c",# green
    "small_whale": "#d62728",  # red
    "whale": "#9467bd",        # purple
    "tidal_whale": "#8c564b",  # brown
    "leviathan": "#e377c2"     # pink
}

# ---------------------------------------------------
# Determine time & price padding
# ---------------------------------------------------
min_time = df["time"].iloc[0]
max_time = df["time"].iloc[-1]

min_price = df[asset_choice].min()
max_price = df[asset_choice].max()
padding = (max_price - min_price) * 0.03

y_min = float(min_price - padding)
y_max = float(max_price + padding)


# ---------------------------------------------------
# Sidebar cohort selector
# ---------------------------------------------------
cohort_columns = [
    "fish", "dolphin", "apex_predator",
    "small_whale", "whale", "tidal_whale", "leviathan"
]

# selected = st.sidebar.multiselect(
#     "Choose cohort segments",
#     cohort_columns,
#     default=cohort_columns
# )

show_markers = st.sidebar.checkbox("Show snapshot markers", value=False)


# ---------------------------------------------------
# KPI CARDS FOR COHORTS
# ---------------------------------------------------

cohort_emojis = {
    "fish": "🐟",
    "dolphin": "🐬",
    "apex_predator": "🦈",
    "small_whale": "🐋",
    "whale": "🐳",
    "tidal_whale": "🌊🐋",
    "leviathan": "🐉"
}

cohort_defs = {
    "fish": "$250 – $10k",
    "dolphin": "$10k – $50k",
    "apex_predator": "$50k – $100k",
    "small_whale": "$100k – $500k",
    "whale": "$500k – $1M",
    "tidal_whale": "$1M – $5M",
    "leviathan": "$5M+"
}

latest_row = df.iloc[-1]
kpi_cols = st.columns(len(cohort_columns))

for i, seg in enumerate(cohort_columns):
    bias_value = float(latest_row[seg])
    label, color = classify_bias(bias_value)

    emoji = cohort_emojis[seg]
    name = seg.replace("_", " ").title()
    range_text = cohort_defs[seg]

    html = (
        f"<div style='background-color:#111;padding:15px;border-radius:10px;text-align:center;"
        f"border:1px solid #222;box-shadow:0px 0px 8px rgba(0,0,0,0.3);margin-bottom:20px;'>"
        f"<div style='font-size:18px;font-weight:600;color:white;'>{emoji} {name}</div>"
        f"<div style='font-size:13px;color:#aaa;margin-bottom:6px;'>{range_text}</div>"
        f"<div style='font-size:26px;font-weight:700;color:{color};margin-top:3px;'>{label}</div>"
        f"<div style='font-size:15px;color:#bbb;margin-top:2px;'>{bias_value:.3f}</div>"
        f"</div>"
    )

    with kpi_cols[i]:
        st.markdown(html, unsafe_allow_html=True)

# ---------------------------------------------------
# Build series list
# ---------------------------------------------------
series = []

# ++++++++++++++++++++++++++++++
# PRICE LINE (btc / eth / sol)
# ++++++++++++++++++++++++++++++
price_series = {
    "name": asset_choice.upper(),
    "type": "line",
    "smooth": True,
    "yAxisIndex": 0,
    "symbol": "circle" if show_markers else "none",
    "symbolSize": 6,
    "data": [
        [row["time"], float(row[asset_choice])]
        for _, row in df.iterrows()
    ],
    "lineStyle": {
        "width": 5,
        "color": price_colors[asset_choice],
        "shadowColor": price_colors[asset_choice] + "90",
        "shadowBlur": 20,
    },
    "areaStyle": {
        "color": price_colors[asset_choice] + "20"
    }
}

series.append(price_series)

# ++++++++++++++++++++++++++++++
# OPTIONAL PRICE MARKERS
# ++++++++++++++++++++++++++++++
if show_markers:
    series.append({
        "name": "snapshot",
        "type": "scatter",
        "yAxisIndex": 0,
        "symbolSize": 10,
        "itemStyle": {"color": "#FFD700"},
        "data": [
            [row["time"], float(row[asset_choice])]
            for _, row in df.iterrows()
        ],
    })

# ++++++++++++++++++++++++++++++
# COHORT LINES — MUTED + THIN
# ++++++++++++++++++++++++++++++
for seg in cohort_columns:
    color = cohort_colors[seg]

    cohort_line = {
        "name": seg,
        "type": "line",
        "smooth": True,
        "yAxisIndex": 1,
        "symbol": "none",

        # MOST IMPORTANT FIX:
        "itemStyle": {"color": color},
        "lineStyle": {
            "width": 1.5,
            "opacity": 0.70,
            "color": color,
        },

        "data": [
            [row["time"], float(row[seg])]
            for _, row in df.iterrows()
            if row[seg] is not None
        ]
    }

    series.append(cohort_line)


# ---------------------------------------------------
# ECharts Configuration
# ---------------------------------------------------
options = {
    "backgroundColor": "#000",
    "tooltip": {"trigger": "axis"},
    "legend": {
        "textStyle": {"color": "#ddd"},
        "top": 10
    },
    "dataZoom": [
        {"type": "inside"},
        {"type": "slider", "height": 20}
    ],
    "xAxis": {
        "type": "time",
        "boundaryGap": False,
        "axisLabel": {"color": "#bbb", "rotate": 45},
        "min": min_time,
        "max": max_time,
    },
    "yAxis": [
        {
            # =============================
            # PRICE AXIS (btc / eth / sol)
            # =============================
            "type": "value",
            "name": asset_labels[asset_choice],
            "axisLabel": {"color": price_colors[asset_choice]},
            "splitLine": {"lineStyle": {"color": "#1e1e1e"}},
            "scale": True,
            "min": y_min,
            "max": y_max
        },
        {
            "type": "value",
            "name": "Cohort Bias",
            "axisLabel": {"color": "#bbb"},
            "splitLine": {"show": False},
            "scale": True,
        }
    ],
    "series": series
}

st_echarts(options=options, height="650px")
