import streamlit as st
from supabase import create_client
import pandas as pd
from datetime import datetime, timedelta
from streamlit_lightweight_charts import renderLightweightCharts
import plotly.graph_objects as go
from plotly.subplots import make_subplots

st.set_page_config(page_title="Hyperwatch Analytics", layout="wide", initial_sidebar_state="expanded")

# === Supabase ===
SUPABASE_URL = st.secrets["SUPABASE_URL"]
SUPABASE_KEY = st.secrets["SUPABASE_KEY"]
supabase = create_client(SUPABASE_URL, SUPABASE_KEY)

# === Constants ===
cohort_columns = ["fish", "dolphin", "apex_predator", "small_whale", "whale", "tidal_whale", "leviathan"]
cohort_names = {
    "fish": "Fish",
    "dolphin": "Dolphin", 
    "apex_predator": "Apex Predator",
    "small_whale": "Small Whale",
    "whale": "Whale",
    "tidal_whale": "Tidal Whale",
    "leviathan": "Leviathan"
}

cohort_emojis = {
    "fish": "🐟",
    "dolphin": "🐬",
    "apex_predator": "🦈",
    "small_whale": "🐋",
    "whale": "🐳",
    "tidal_whale": "🌊",
    "leviathan": "🐉"
}

cohort_ranges = {
    "fish": "$250 – $10k",
    "dolphin": "$10k – $50k",
    "apex_predator": "$50k – $100k",
    "small_whale": "$100k – $500k",
    "whale": "$500k – $1M",
    "tidal_whale": "$1M – $5M",
    "leviathan": "$5M+"
}

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
# Data Loading
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
    df["timestamp"] = pd.to_datetime(df["timestamp"], utc=True)
    df["timestamp"] = df["timestamp"].dt.tz_convert("America/New_York")
    return df

# ---------------------------------------------------
# Sidebar
# ---------------------------------------------------
st.sidebar.title("⚙️ Controls")

if st.sidebar.button("🔄 Refresh Data"):
    try:
        load_candlestick_data.clear()
    except:
        try:
            st.cache_data.clear()
        except:
            pass
    st.rerun()

df = load_candlestick_data()

if df.empty:
    st.error("No data available.")
    st.stop()

df = df.sort_values("timestamp")

# Time Range
st.sidebar.subheader("📅 Time Range")
tv_presets = {
    "1H": timedelta(hours=1),
    "3H": timedelta(hours=3),
    "6H": timedelta(hours=6),
    "12H": timedelta(hours=12),
    "24H": timedelta(hours=24),
    "3D": timedelta(days=3),
    "1W": timedelta(days=7),
    "All": None
}

preset_keys = list(tv_presets.keys())
default_index = len(preset_keys) - 1 if len(preset_keys) > 0 else 0

preset = st.sidebar.selectbox("Quick Range", preset_keys, index=default_index)

if tv_presets[preset] is not None:
    cutoff = df["timestamp"].max() - tv_presets[preset]
    df = df[df["timestamp"] >= cutoff]

# Asset Selector
st.sidebar.subheader("💰 Asset")
asset_choice = st.sidebar.radio("Price Asset", ["btc", "eth", "sol"], index=0)

# Cohort Reference Guide
st.sidebar.markdown("---")
st.sidebar.subheader("📚 Cohort Guide")

cohort_info = {
    "fish": ("🐟", "$250 – $10k", "Retail traders"),
    "dolphin": ("🐬", "$10k – $50k", "Active retail"),
    "apex_predator": ("🦈", "$50k – $100k", "Serious traders"),
    "small_whale": ("🐋", "$100k – $500k", "Small institutions"),
    "whale": ("🐳", "$500k – $1M", "Institutions"),
    "tidal_whale": ("🌊", "$1M – $5M", "Large funds"),
    "leviathan": ("🐉", "$5M+", "Market makers")
}

for seg, (emoji, range_val, desc) in cohort_info.items():
    st.sidebar.markdown(
        f"""
        <div style='background-color:#1a1a2e; padding:8px; border-radius:6px; margin-bottom:8px; border-left:3px solid {cohort_colors[seg]};'>
            <div style='font-size:18px;'>{emoji} <strong>{cohort_names[seg]}</strong></div>
            <div style='font-size:12px; color:#aaa;'>{range_val}</div>
            <div style='font-size:11px; color:#888; font-style:italic;'>{desc}</div>
        </div>
        """,
        unsafe_allow_html=True
    )

# ---------------------------------------------------
# Utility Functions
# ---------------------------------------------------
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

def format_large_number(num):
    if num >= 1e9:
        return f"${num/1e9:.2f}B"
    elif num >= 1e6:
        return f"${num/1e6:.2f}M"
    elif num >= 1e3:
        return f"${num/1e3:.2f}K"
    return f"${num:.2f}"

def create_metric_card(title, value, subtitle="", emoji="", color="#4CAF50"):
    return f"""
    <div style='background: linear-gradient(135deg, #1a1a2e 0%, #16213e 100%);
                padding: 8px 10px;
                border-radius: 8px;
                border-left: 3px solid {color};
                box-shadow: 0 1px 3px rgba(0,0,0,0.2);
                margin-bottom: 5px;'>
        <div style='font-size: 18px; margin-bottom: 3px;'>{emoji}</div>
        <div style='font-size: 11px; color: #aaa; text-transform: uppercase; letter-spacing: 0.4px;'>{title}</div>
        <div style='font-size: 14px; font-weight: 500; color: {color}; margin: 3px 0;'>{value}</div>
        <div style='font-size: 11px; color: #888;'>{subtitle}</div>
    </div>
    """

# ---------------------------------------------------
# TABS
# ---------------------------------------------------
tab1, tab2, tab3, tab4, tab5 = st.tabs([
    "📈 Price & Bias",
    "💰 Capital Flow", 
    "🎯 Win Rates",
    "⚖️ Long/Short",
    "🚨 Risk Metrics"
])

# Get latest row for KPIs
latest = df.iloc[-1]

# ===================================================
# TAB 1: PRICE & BIAS
# ===================================================
with tab1:
    st.subheader(f"{asset_choice.upper()} Price Action with Cohort Bias")
    
    # KPI Cards for Bias
    kpi_cols = st.columns(7)
    
    for i, seg in enumerate(cohort_columns):
        bias_value = float(latest[f"{seg}_bias"])
        label, color = classify_bias(bias_value)
        
        with kpi_cols[i]:
            st.markdown(
                create_metric_card(
                    cohort_names[seg],
                    label,
                    f"{bias_value:.3f}",
                    cohort_emojis[seg],
                    color
                ),
                unsafe_allow_html=True
            )
    
    # Candlestick Chart
    df['time'] = df['timestamp'].astype('int64') // 10**9
    
    candlestick_data = []
    for _, row in df.iterrows():
        candlestick_data.append({
            'time': int(row['time']),
            'open': float(row[f'{asset_choice}_open']),
            'high': float(row[f'{asset_choice}_high']),
            'low': float(row[f'{asset_choice}_low']),
            'close': float(row[f'{asset_choice}_close'])
        })
    
    # Cohort lines
    available_cohorts = []
    for seg in cohort_columns:
        if f"{seg}_bias" in df.columns:
            available_cohorts.append(seg)
    
    default_cohorts = [c for c in ["whale", "leviathan"] if c in available_cohorts]
    
    selected_cohorts = st.multiselect(
        "Select Cohorts to Display",
        available_cohorts,
        default=default_cohorts if default_cohorts else available_cohorts[:2] if len(available_cohorts) >= 2 else available_cohorts,
        format_func=lambda x: cohort_names[x]
    )
    
    cohort_series = []
    for seg in selected_cohorts:
        line_data = []
        for _, row in df.iterrows():
            line_data.append({
                'time': int(row['time']),
                'value': float(row[f'{seg}_bias'])
            })
        
        cohort_series.append({
            'type': 'Line',
            'data': line_data,
            'options': {
                'color': cohort_colors[seg],
                'lineWidth': 2,
                'title': cohort_names[seg],
                'priceScaleId': 'left'
            }
        })
    
    chartOptions = {
        'layout': {'background': {'color': '#000000'}, 'textColor': '#d1d4dc'},
        'grid': {'vertLines': {'color': '#1e1e1e'}, 'horzLines': {'color': '#1e1e1e'}},
        'crosshair': {'mode': 0},
        'rightPriceScale': {'visible': True, 'borderColor': '#2B2B43'},
        'leftPriceScale': {'visible': True, 'borderColor': '#2B2B43'},
        'timeScale': {'borderColor': '#2B2B43', 'timeVisible': True, 'secondsVisible': False},
        'height': 600,
    }
    
    seriesCandlestickChart = [{
        'type': 'Candlestick',
        'data': candlestick_data,
        'options': {
            'upColor': '#00C087',
            'downColor': '#EF5350',
            'borderVisible': False,
            'wickUpColor': '#00C087',
            'wickDownColor': '#EF5350',
            'priceScaleId': 'right'
        }
    }]
    
    seriesCandlestickChart.extend(cohort_series)
    
    renderLightweightCharts([{"chart": chartOptions, "series": seriesCandlestickChart}], 'price_bias')

# ===================================================
# TAB 2: CAPITAL FLOW
# ===================================================
with tab2:
    st.subheader("💰 Capital Distribution & Flow Analysis")
    
    # Current Capital Distribution KPIs
    cap_cols = st.columns(4)
    
    total_equity = sum([latest[f"{seg}_total_perp_equity"] for seg in cohort_columns])
    total_active = sum([latest[f"{seg}_total_active_perp_equity"] for seg in cohort_columns])
    
    with cap_cols[0]:
        st.markdown(
            create_metric_card(
                "Total Equity",
                format_large_number(total_equity),
                "All Cohorts Combined",
                "💎",
                "#00C087"
            ),
            unsafe_allow_html=True
        )
    
    with cap_cols[1]:
        st.markdown(
            create_metric_card(
                "Active Equity",
                format_large_number(total_active),
                f"{(total_active/total_equity*100):.1f}% Deployed",
                "⚡",
                "#FFD700"
            ),
            unsafe_allow_html=True
        )
    
    whale_equity = latest["whale_total_perp_equity"] + latest["tidal_whale_total_perp_equity"] + latest["leviathan_total_perp_equity"]
    
    with cap_cols[2]:
        st.markdown(
            create_metric_card(
                "Whale Capital",
                format_large_number(whale_equity),
                f"{(whale_equity/total_equity*100):.1f}% of Total",
                "🐳",
                "#9467bd"
            ),
            unsafe_allow_html=True
        )
    
    with cap_cols[3]:
        avg_exposure = sum([latest[f"{seg}_exposure_ratio"] for seg in cohort_columns]) / len(cohort_columns)
        st.markdown(
            create_metric_card(
                "Avg Exposure",
                f"{avg_exposure:.2f}x",
                "Market Leverage",
                "📊",
                "#F57C00" if avg_exposure > 3 else "#4CAF50"
            ),
            unsafe_allow_html=True
        )
    
    # Equity over time chart
    st.markdown("### Capital Flow Timeline")
    
    fig_equity = go.Figure()
    
    for seg in cohort_columns:
        fig_equity.add_trace(go.Scatter(
            x=df['timestamp'],
            y=df[f'{seg}_total_perp_equity'],
            name=cohort_names[seg],
            mode='lines',
            stackgroup='one',
            line=dict(width=0.5, color=cohort_colors[seg]),
            fillcolor=cohort_colors[seg]
        ))
    
    fig_equity.update_layout(
        template='plotly_dark',
        height=500,
        hovermode='x unified',
        yaxis_title='Total Equity ($)',
        xaxis_title='Time',
        plot_bgcolor='#000000',
        paper_bgcolor='#000000'
    )
    
    st.plotly_chart(fig_equity, use_container_width=True)
    
    # Capital distribution pie chart
    col1, col2 = st.columns(2)
    
    with col1:
        st.markdown("### Current Distribution")
        equity_data = {cohort_names[seg]: latest[f"{seg}_total_perp_equity"] for seg in cohort_columns}
        
        fig_pie = go.Figure(data=[go.Pie(
            labels=list(equity_data.keys()),
            values=list(equity_data.values()),
            marker=dict(colors=[cohort_colors[seg] for seg in cohort_columns]),
            hole=0.4
        )])
        
        fig_pie.update_layout(
            template='plotly_dark',
            height=400,
            plot_bgcolor='#000000',
            paper_bgcolor='#000000'
        )
        
        st.plotly_chart(fig_pie, use_container_width=True)
    
    with col2:
        st.markdown("### Active vs Total Equity")
        
        active_ratios = []
        for seg in cohort_columns:
            total = latest[f"{seg}_total_perp_equity"]
            active = latest[f"{seg}_total_active_perp_equity"]
            active_ratios.append((active/total*100) if total > 0 else 0)
        
        fig_bar = go.Figure(data=[
            go.Bar(
                x=[cohort_names[seg] for seg in cohort_columns],
                y=active_ratios,
                marker_color=[cohort_colors[seg] for seg in cohort_columns]
            )
        ])
        
        fig_bar.update_layout(
            template='plotly_dark',
            height=400,
            yaxis_title='Active Capital (%)',
            plot_bgcolor='#000000',
            paper_bgcolor='#000000'
        )
        
        st.plotly_chart(fig_bar, use_container_width=True)

# ===================================================
# TAB 3: WIN RATES
# ===================================================
with tab3:
    st.subheader("🎯 Trader Performance & Win Rates")
    
    # Win Rate KPIs
    win_cols = st.columns(7)
    
    for i, seg in enumerate(cohort_columns):
        in_position = latest[f"{seg}_count_traders_in_position"]
        in_profit = latest[f"{seg}_count_traders_in_profit"]
        win_rate = (in_profit / in_position * 100) if in_position > 0 else 0
        
        color = "#2ECC71" if win_rate >= 50 else "#D32F2F"
        
        with win_cols[i]:
            st.markdown(
                create_metric_card(
                    cohort_names[seg],
                    f"{win_rate:.1f}%",
                    f"{in_profit}/{in_position} traders",
                    cohort_emojis[seg],
                    color
                ),
                unsafe_allow_html=True
            )
    
    # Win rate over time
    st.markdown("### Win Rate Timeline")
    
    fig_winrate = go.Figure()
    
    for seg in cohort_columns:
        win_rates = []
        for _, row in df.iterrows():
            in_pos = row[f"{seg}_count_traders_in_position"]
            in_prof = row[f"{seg}_count_traders_in_profit"]
            wr = (in_prof / in_pos * 100) if in_pos > 0 else 0
            win_rates.append(wr)
        
        fig_winrate.add_trace(go.Scatter(
            x=df['timestamp'],
            y=win_rates,
            name=cohort_names[seg],
            mode='lines',
            line=dict(color=cohort_colors[seg], width=2)
        ))
    
    fig_winrate.add_hline(y=50, line_dash="dash", line_color="white", opacity=0.3)
    
    fig_winrate.update_layout(
        template='plotly_dark',
        height=500,
        hovermode='x unified',
        yaxis_title='Win Rate (%)',
        xaxis_title='Time',
        plot_bgcolor='#000000',
        paper_bgcolor='#000000'
    )
    
    st.plotly_chart(fig_winrate, use_container_width=True)
    
    # Smart Money vs Dumb Money comparison
    col1, col2 = st.columns(2)
    
    with col1:
        st.markdown("### 🐟 Fish vs 🐉 Leviathan")
        
        fish_wr = (latest["fish_count_traders_in_profit"] / latest["fish_count_traders_in_position"] * 100)
        lev_wr = (latest["leviathan_count_traders_in_profit"] / latest["leviathan_count_traders_in_position"] * 100)
        
        fig_compare = go.Figure(data=[
            go.Bar(
                x=['Fish', 'Leviathan'],
                y=[fish_wr, lev_wr],
                marker_color=['#1f77b4', '#e377c2']
            )
        ])
        
        fig_compare.add_hline(y=50, line_dash="dash", line_color="white", opacity=0.3)
        
        fig_compare.update_layout(
            template='plotly_dark',
            height=350,
            yaxis_title='Win Rate (%)',
            plot_bgcolor='#000000',
            paper_bgcolor='#000000'
        )
        
        st.plotly_chart(fig_compare, use_container_width=True)
    
    with col2:
        st.markdown("### PnL Distribution")
        
        pnl_data = {cohort_names[seg]: latest[f"{seg}_perp_pnl"] for seg in cohort_columns}
        
        colors_pnl = [('#2ECC71' if v >= 0 else '#D32F2F') for v in pnl_data.values()]
        
        fig_pnl = go.Figure(data=[
            go.Bar(
                x=list(pnl_data.keys()),
                y=list(pnl_data.values()),
                marker_color=colors_pnl
            )
        ])
        
        fig_pnl.update_layout(
            template='plotly_dark',
            height=350,
            yaxis_title='PnL ($)',
            plot_bgcolor='#000000',
            paper_bgcolor='#000000'
        )
        
        st.plotly_chart(fig_pnl, use_container_width=True)

# ===================================================
# TAB 4: LONG/SHORT
# ===================================================
with tab4:
    st.subheader("⚖️ Long vs Short Positioning")
    
    # Long/Short Balance KPIs
    ls_cols = st.columns(4)
    
    total_long_value = sum([latest[f"{seg}_long_total_value"] for seg in cohort_columns])
    total_short_value = sum([latest[f"{seg}_short_total_value"] for seg in cohort_columns])
    long_ratio = total_long_value / (total_long_value + total_short_value) * 100
    
    with ls_cols[0]:
        st.markdown(
            create_metric_card(
                "Total Long",
                format_large_number(total_long_value),
                f"{long_ratio:.1f}% of positions",
                "📈",
                "#00C087"
            ),
            unsafe_allow_html=True
        )
    
    with ls_cols[1]:
        st.markdown(
            create_metric_card(
                "Total Short",
                format_large_number(total_short_value),
                f"{100-long_ratio:.1f}% of positions",
                "📉",
                "#EF5350"
            ),
            unsafe_allow_html=True
        )
    
    total_long_count = sum([latest[f"{seg}_long_count_open_positions"] for seg in cohort_columns])
    total_short_count = sum([latest[f"{seg}_short_count_open_positions"] for seg in cohort_columns])
    
    with ls_cols[2]:
        st.markdown(
            create_metric_card(
                "Long Positions",
                f"{total_long_count:,}",
                "Open contracts",
                "🟢",
                "#00C087"
            ),
            unsafe_allow_html=True
        )
    
    with ls_cols[3]:
        st.markdown(
            create_metric_card(
                "Short Positions",
                f"{total_short_count:,}",
                "Open contracts",
                "🔴",
                "#EF5350"
            ),
            unsafe_allow_html=True
        )
    
    # Long/Short by cohort
    st.markdown("### Position Distribution by Cohort")
    
    fig_ls = go.Figure()
    
    long_values = [latest[f"{seg}_long_total_value"] for seg in cohort_columns]
    short_values = [-latest[f"{seg}_short_total_value"] for seg in cohort_columns]
    
    fig_ls.add_trace(go.Bar(
        y=[cohort_names[seg] for seg in cohort_columns],
        x=long_values,
        name='Long',
        orientation='h',
        marker_color='#00C087'
    ))
    
    fig_ls.add_trace(go.Bar(
        y=[cohort_names[seg] for seg in cohort_columns],
        x=short_values,
        name='Short',
        orientation='h',
        marker_color='#EF5350'
    ))
    
    fig_ls.update_layout(
        template='plotly_dark',
        height=500,
        barmode='relative',
        xaxis_title='Position Value ($)',
        plot_bgcolor='#000000',
        paper_bgcolor='#000000'
    )
    
    st.plotly_chart(fig_ls, use_container_width=True)
    
    # Long/Short ratio over time
    st.markdown("### Long/Short Ratio Timeline")
    
    fig_ratio = go.Figure()
    
    for seg in cohort_columns:
        ratios = []
        for _, row in df.iterrows():
            long_val = row[f"{seg}_long_total_value"]
            short_val = row[f"{seg}_short_total_value"]
            ratio = (long_val / (long_val + short_val) * 100) if (long_val + short_val) > 0 else 50
            ratios.append(ratio)
        
        fig_ratio.add_trace(go.Scatter(
            x=df['timestamp'],
            y=ratios,
            name=cohort_names[seg],
            mode='lines',
            line=dict(color=cohort_colors[seg], width=2)
        ))
    
    fig_ratio.add_hline(y=50, line_dash="dash", line_color="white", opacity=0.3, annotation_text="Balanced")
    
    fig_ratio.update_layout(
        template='plotly_dark',
        height=500,
        hovermode='x unified',
        yaxis_title='Long Ratio (%)',
        xaxis_title='Time',
        plot_bgcolor='#000000',
        paper_bgcolor='#000000'
    )
    
    st.plotly_chart(fig_ratio, use_container_width=True)

# ===================================================
# TAB 5: RISK METRICS
# ===================================================
with tab5:
    st.subheader("🚨 Risk & Exposure Analysis")
    
    # Risk KPIs
    risk_cols = st.columns(4)
    
    max_exposure = max([latest[f"{seg}_exposure_ratio"] for seg in cohort_columns])
    max_exposure_cohort = cohort_names[[seg for seg in cohort_columns if latest[f"{seg}_exposure_ratio"] == max_exposure][0]]
    
    with risk_cols[0]:
        color = "#D32F2F" if max_exposure > 3.5 else "#F57C00" if max_exposure > 3 else "#4CAF50"
        st.markdown(
            create_metric_card(
                "Max Exposure",
                f"{max_exposure:.2f}x",
                f"By {max_exposure_cohort}",
                "⚠️",
                color
            ),
            unsafe_allow_html=True
        )
    
    total_positions = sum([latest[f"{seg}_count_open_positions"] for seg in cohort_columns])
    
    with risk_cols[1]:
        st.markdown(
            create_metric_card(
                "Open Positions",
                f"{total_positions:,}",
                "Market-wide",
                "📊",
                "#00C087"
            ),
            unsafe_allow_html=True
        )
    
    total_size = sum([latest[f"{seg}_total_size"] for seg in cohort_columns])
    
    with risk_cols[2]:
        st.markdown(
            create_metric_card(
                "Total Size",
                format_large_number(total_size),
                "Aggregate exposure",
                "💼",
                "#FFD700"
            ),
            unsafe_allow_html=True
        )
    
    total_pnl = sum([latest[f"{seg}_perp_pnl"] for seg in cohort_columns])
    pnl_color = "#2ECC71" if total_pnl >= 0 else "#D32F2F"
    
    with risk_cols[3]:
        st.markdown(
            create_metric_card(
                "Market PnL",
                format_large_number(total_pnl),
                "Net profit/loss",
                "💰",
                pnl_color
            ),
            unsafe_allow_html=True
        )
    
    # Exposure ratio over time
    st.markdown("### Leverage Timeline")
    
    fig_exposure = go.Figure()
    
    for seg in cohort_columns:
        fig_exposure.add_trace(go.Scatter(
            x=df['timestamp'],
            y=df[f'{seg}_exposure_ratio'],
            name=cohort_names[seg],
            mode='lines',
            line=dict(color=cohort_colors[seg], width=2)
        ))
    
    fig_exposure.add_hline(y=3.0, line_dash="dash", line_color="yellow", opacity=0.5, annotation_text="High Risk")
    fig_exposure.add_hline(y=3.5, line_dash="dash", line_color="red", opacity=0.5, annotation_text="Extreme Risk")
    
    fig_exposure.update_layout(
        template='plotly_dark',
        height=500,
        hovermode='x unified',
        yaxis_title='Exposure Ratio',
        xaxis_title='Time',
        plot_bgcolor='#000000',
        paper_bgcolor='#000000'
    )
    
    st.plotly_chart(fig_exposure, use_container_width=True)
    
    # Risk heatmap
    col1, col2 = st.columns(2)
    
    with col1:
        st.markdown("### Current Exposure by Cohort")
        
        exposures = [latest[f"{seg}_exposure_ratio"] for seg in cohort_columns]
        colors_exp = []
        for exp in exposures:
            if exp > 3.5:
                colors_exp.append('#D32F2F')
            elif exp > 3:
                colors_exp.append('#F57C00')
            else:
                colors_exp.append('#4CAF50')
        
        fig_exp_bar = go.Figure(data=[
            go.Bar(
                x=[cohort_names[seg] for seg in cohort_columns],
                y=exposures,
                marker_color=colors_exp
            )
        ])
        
        fig_exp_bar.add_hline(y=3.0, line_dash="dash", line_color="yellow", opacity=0.5)
        fig_exp_bar.add_hline(y=3.5, line_dash="dash", line_color="red", opacity=0.5)
        
        fig_exp_bar.update_layout(
            template='plotly_dark',
            height=400,
            yaxis_title='Exposure Ratio',
            plot_bgcolor='#000000',
            paper_bgcolor='#000000'
        )
        
        st.plotly_chart(fig_exp_bar, use_container_width=True)
    
    with col2:
        st.markdown("### Total Size by Cohort")
        
        sizes = [latest[f"{seg}_total_size"] for seg in cohort_columns]
        
        fig_size = go.Figure(data=[
            go.Bar(
                x=[cohort_names[seg] for seg in cohort_columns],
                y=sizes,
                marker_color=[cohort_colors[seg] for seg in cohort_columns]
            )
        ])
        
        fig_size.update_layout(
            template='plotly_dark',
            height=400,
            yaxis_title='Total Size ($)',
            plot_bgcolor='#000000',
            paper_bgcolor='#000000'
        )
        
        st.plotly_chart(fig_size, use_container_width=True)

# ---------------------------------------------------
# Footer
# ---------------------------------------------------
st.markdown("---")
col1, col2, col3 = st.columns(3)

with col1:
    st.markdown(f"**Last Updated:** {latest['timestamp'].strftime('%Y-%m-%d %H:%M:%S EST')}")

with col2:
    st.markdown(f"**Data Points:** {len(df):,} candles")

with col3:
    total_traders = sum([latest[f"{seg}_count_traders_in_position"] for seg in cohort_columns])
    st.markdown(f"**Active Traders:** {total_traders:,}")