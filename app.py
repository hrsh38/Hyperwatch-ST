import streamlit as st
from supabase import create_client
import pandas as pd
from datetime import datetime, timedelta
from streamlit_lightweight_charts import renderLightweightCharts

st.set_page_config(page_title="Hyperwatch – Candlestick Dashboard", layout="wide")

# === Supabase ===
SUPABASE_URL = st.secrets["SUPABASE_URL"]
SUPABASE_KEY = st.secrets["SUPABASE_KEY"]
supabase = create_client(SUPABASE_URL, SUPABASE_KEY)


# ---------------------------------------------------
# Load candlestick data
# ---------------------------------------------------
@st.cache_data(ttl=300)
def load_candlestick_data():
    resp = (
        supabase.table("candlestick_data")
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

    return df


# Sidebar refresh button
if st.sidebar.button("🔄 Refresh Data"):
    try:
        load_candlestick_data.clear()
    except Exception:
        try:
            st.cache_data.clear()
        except Exception:
            pass
    st.rerun()

# Load data
df = load_candlestick_data()

if df.empty:
    st.error("candlestick_data table is empty.")
    st.stop()

df = df.sort_values("timestamp")

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

# Calendar picker
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
    "btc": "BTC",
    "eth": "ETH",
    "sol": "SOL"
}

def classify_bias(value):
    if value <= -0.60:
        return "Very Bearish", "#D32F2F"
    elif value <= -0.20:
        return "Bearish", "#F57C00"
    elif value <= 0.20:
        return "Neutral", "#757575"
    elif value <= 0.60:
        return "Bullish", "#4CAF50"
    else:
        return "Very Bullish", "#2ECC71"

cohort_colors = {
    "fish": "#1f77b4",
    "dolphin": "#ff7f0e",
    "apex_predator": "#2ca02c",
    "small_whale": "#d62728",
    "whale": "#9467bd",
    "tidal_whale": "#8c564b",
    "leviathan": "#e377c2"
}

# ---------------------------------------------------
# Sidebar options
# ---------------------------------------------------
cohort_columns = [
    "fish", "dolphin", "apex_predator",
    "small_whale", "whale", "tidal_whale", "leviathan"
]

show_cohorts = st.sidebar.checkbox("Show Cohort Lines", value=True)

selected_cohorts = []
if show_cohorts:
    selected_cohorts = st.sidebar.multiselect(
        "Select Cohorts",
        cohort_columns,
        default=cohort_columns
    )

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
# PREPARE DATA FOR LIGHTWEIGHT CHARTS
# ---------------------------------------------------

# Convert timestamp to Unix timestamp (seconds)
df['time'] = df['timestamp'].astype('int64') // 10**9

# Prepare candlestick data
candlestick_data = []
for _, row in df.iterrows():
    candlestick_data.append({
        'time': int(row['time']),
        'open': float(row[f'{asset_choice}_open']),
        'high': float(row[f'{asset_choice}_high']),
        'low': float(row[f'{asset_choice}_low']),
        'close': float(row[f'{asset_choice}_close'])
    })

# Calculate cohort bias range
cohort_values = []
for seg in cohort_columns:
    cohort_values.extend(df[seg].dropna().tolist())

if cohort_values:
    cohort_min = min(cohort_values)
    cohort_max = max(cohort_values)
    
    # Add ±0.3 padding
    right_axis_min = cohort_min - 0.3
    right_axis_max = cohort_max + 0.3
else:
    right_axis_min = -1.5
    right_axis_max = 1.5

print(f"Right axis range: {right_axis_min:.2f} to {right_axis_max:.2f}")

# Prepare cohort line data
cohort_series = []
if show_cohorts and selected_cohorts:
    for seg in selected_cohorts:
        line_data = []
        for _, row in df.iterrows():
            line_data.append({
                'time': int(row['time']),
                'value': float(row[seg])
            })
        
        cohort_series.append({
            'type': 'Line',
            'data': line_data,
            'options': {
                'color': cohort_colors[seg],
                'lineWidth': 2,
                'title': seg.replace('_', ' ').title(),
                'priceScaleId': 'left'
            }
        })

# ---------------------------------------------------
# CREATE LIGHTWEIGHT CHART
# ---------------------------------------------------

chartOptions = {
    'layout': {
        'background': {'color': '#000000'},
        'textColor': '#d1d4dc',
    },
    'grid': {
        'vertLines': {'color': '#1e1e1e'},
        'horzLines': {'color': '#1e1e1e'},
    },
    'crosshair': {
        'mode': 0
    },
    'rightPriceScale': {
        'visible': True,
        'borderColor': '#2B2B43',
    },
    'leftPriceScale': {
        'visible': True,
        'borderColor': '#2B2B43',
    },
    'timeScale': {
        'borderColor': '#2B2B43',
        'timeVisible': True,
        'secondsVisible': False,
    },
    'height': 600,
}

# Main candlestick series
seriesCandlestickChart = [
    {
        'type': 'Candlestick',
        'data': candlestick_data,
        'options': {
            'upColor': '#00C087',
            'downColor': '#EF5350',
            'borderVisible': False,
            'wickUpColor': '#00C087',
            'wickDownColor': '#EF5350',
            'priceScaleId': 'right'  # Price on right side
        }
    }
]

# Add cohort lines
seriesCandlestickChart.extend(cohort_series)

st.subheader(f"{asset_labels[asset_choice]} Candlestick Chart")

renderLightweightCharts([
    {
        "chart": chartOptions,
        "series": seriesCandlestickChart
    }
], 'candlestick')

# ---------------------------------------------------
# DATA TABLE (Optional)
# ---------------------------------------------------
if st.sidebar.checkbox("Show Raw Data", value=False):
    st.subheader("Raw Candlestick Data")
    st.dataframe(df)