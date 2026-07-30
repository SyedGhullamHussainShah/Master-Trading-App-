import streamlit as st
import requests
import pandas as pd
import numpy as np
import yfinance as yf
import plotly.graph_objects as go
from plotly.subplots import make_subplots

# -----------------------------------------------------------------------------
# 1. Page & Layout Setup
# -----------------------------------------------------------------------------
st.set_page_config(
    page_title="Master Institutional Analysis Terminal",
    layout="wide",
    initial_sidebar_state="expanded"
)

st.title("🏛️ Master Institutional Market & Order Flow Engine")
st.caption("Real-Time Order Book, Open Interest, VSA & Multi-Exchange Analytics")

# -----------------------------------------------------------------------------
# 2. Sidebar & Multi-Source Configuration
# -----------------------------------------------------------------------------
st.sidebar.header("⚙️ Data Feeds & Configuration")

market_type = st.sidebar.radio("Select Market Type:", ["Crypto Futures (Binance Data)", "Gold & Forex (Yahoo / OANDA)"])

if market_type == "Crypto Futures (Binance Data)":
    symbol = st.sidebar.selectbox("Select Asset:", ["BTCUSDT", "ETHUSDT", "SOLUSDT"], index=0)
else:
    symbol = st.sidebar.selectbox("Select Asset:", ["GC=F", "EURUSD=X", "GBPUSD=X"], index=0)
    oanda_api_key = st.sidebar.text_input("OANDA API Key (Optional for Gold/Forex):", type="password")
    oanda_account_id = st.sidebar.text_input("OANDA Account ID (Optional):")

timeframe = st.sidebar.selectbox("Chart Timeframe:", ["1d", "1h", "15m", "5m"], index=1)
period_map = {"1d": "6m", "1h": "1m", "15m": "7d", "5m": "60d"}

# -----------------------------------------------------------------------------
# 3. Robust Data Engines (Cached & Error-Free)
# -----------------------------------------------------------------------------

# A. Binance Futures API Engine (No Key Required)
@st.cache_data(ttl=5)
def fetch_binance_data(sym):
    try:
        # Depth / Order Book
        depth_url = f"https://fapi.binance.com/fapi/v1/depth?symbol={sym}&limit=20"
        depth_res = requests.get(depth_url, timeout=5).json()
        bids = pd.DataFrame(depth_res['bids'], columns=['Price', 'Quantity']).astype(float)
        asks = pd.DataFrame(depth_res['asks'], columns=['Price', 'Quantity']).astype(float)
        
        # Open Interest
        oi_url = f"https://fapi.binance.com/fapi/v1/openInterest?symbol={sym}"
        oi_res = requests.get(oi_url, timeout=5).json()
        oi = float(oi_res['openInterest'])
        
        # Global Long/Short Ratio
        ls_url = f"https://fapi.binance.com/fapi/v1/globalLongShortAccountRatio?symbol={sym}&period=5m&limit=1"
        ls_res = requests.get(ls_url, timeout=5).json()
        long_ratio = float(ls_res[0]['longAccount']) * 100
        short_ratio = float(ls_res[0]['shortAccount']) * 100

        return bids, asks, oi, long_ratio, short_ratio
    except Exception as e:
        return pd.DataFrame(), pd.DataFrame(), 0.0, 50.0, 50.0

# B. Yahoo Finance Engine for VSA & Candlesticks
@st.cache_data(ttl=15)
def fetch_yf_candles(sym, tf, period):
    try:
        data = yf.download(sym, period=period, interval=tf, progress=False)
        if isinstance(data.columns, pd.MultiIndex):
            data.columns = data.columns.get_level_values(0)
        data.dropna(inplace=True)
        return data
    except Exception:
        return pd.DataFrame()

# C. OANDA API Engine (Optional Integration)
@st.cache_data(ttl=30)
def fetch_oanda_positions(api_key, acc_id, instrument="XAU_USD"):
    if not api_key or not acc_id:
        return None
    try:
        headers = {"Authorization": f"Bearer {api_key}"}
        url = f"https://api-fxpractice.oanda.com/v3/instruments/{instrument}/positionBook"
        res = requests.get(url, headers=headers, timeout=5).json()
        return res
    except Exception:
        return None

# -----------------------------------------------------------------------------
# 4. Main Execution & Display Logic
# -----------------------------------------------------------------------------

if market_type == "Crypto Futures (Binance Data)":
    bids, asks, oi, long_pct, short_pct = fetch_binance_data(symbol)
    
    if not bids.empty and not asks.empty:
        total_bids = bids['Quantity'].sum()
        total_asks = asks['Quantity'].sum()
        imbalance = (total_bids / (total_bids + total_asks)) * 100

        # Top Metric Cards
        st.subheader("📊 Live Order Flow & Open Interest Metrics")
        m1, m2, m3, m4 = st.columns(4)
        m1.metric("Live Market Price", f"${bids['Price'].iloc[0]:,.2f}")
        m2.metric("Open Interest (OI)", f"{oi:,.2f}")
        m3.metric("Institutional Longs Ratio", f"{long_pct:.1f}%")
        m4.metric("Institutional Shorts Ratio", f"{short_pct:.1f}%")

        # Order Book Pressure Banner
        if imbalance > 55:
            st.success(f"🟢 **Institutional Buying Wall Detected:** Buyers dominate ({imbalance:.1f}%)")
        elif imbalance < 45:
            st.error(f"🔴 **Institutional Selling Wall Detected:** Sellers dominate ({100 - imbalance:.1f}%)")
        else:
            st.info(f"⚪ **Order Book Neutral:** Balanced Market ({imbalance:.1f}%)")

        # Visual Order Book Depth Chart
        st.subheader("📈 Real-Time Order Book Depth (Bids vs Asks)")
        fig_depth = go.Figure()
        fig_depth.add_trace(go.Scatter(x=bids['Price'], y=bids['Quantity'].cumsum(), fill='tozeroy', name='Bids (Buyers)', line_color='#26a69a'))
        fig_depth.add_trace(go.Scatter(x=asks['Price'], y=asks['Quantity'].cumsum(), fill='tozeroy', name='Asks (Sellers)', line_color='#ef5350'))
        fig_depth.update_layout(height=350, template="plotly_dark", margin=dict(l=10, r=10, t=20, b=20))
        st.plotly_chart(fig_depth, use_container_width=True)

# -----------------------------------------------------------------------------
# 5. VSA & Wyckoff Analysis Section (Applicable for all Assets)
# -----------------------------------------------------------------------------
st.markdown("---")
st.subheader("🏛️ Institutional VSA & Candlestick Analysis")

yf_symbol = symbol if market_type != "Crypto Futures (Binance Data)" else symbol
df_candles = fetch_yf_candles(yf_symbol, timeframe, period_map[timeframe])

if not df_candles.empty:
    # VSA Calculations
    df_candles['Spread'] = df_candles['High'] - df_candles['Low']
    df_candles['Vol_MA'] = df_candles['Volume'].rolling(20).mean()
    df_candles['Spread_MA'] = df_candles['Spread'].rolling(20).mean()
    df_candles['Close_Pos'] = (df_candles['Close'] - df_candles['Low']) / (df_candles['Spread'] + 1e-9)

    # VSA Signal Logic
    signals = []
    for i in range(len(df_candles)):
        if i < 20:
            signals.append("Neutral")
            continue
        v = df_candles['Volume'].iloc[i]
        v_ma = df_candles['Vol_MA'].iloc[i]
        s = df_candles['Spread'].iloc[i]
        s_ma = df_candles['Spread_MA'].iloc[i]
        cp = df_candles['Close_Pos'].iloc[i]

        if v > v_ma * 1.5 and s > s_ma * 1.3 and cp > 0.7:
            signals.append("Accumulation / Stopping Volume (Bullish)")
        elif v > v_ma * 1.5 and s > s_ma * 1.3 and cp < 0.3:
            signals.append("Distribution / Selling Climax (Bearish)")
        elif v < v_ma * 0.6 and s < s_ma * 0.8:
            signals.append("No Supply / Demand Test")
        else:
            signals.append("Neutral")

    df_candles['VSA_Signal'] = signals

    # Plot Candlestick + Volume Chart
    fig_vsa = make_subplots(rows=2, cols=1, shared_xaxes=True, vertical_spacing=0.03, row_width=[0.3, 0.7])
    fig_vsa.add_trace(go.Candlestick(x=df_candles.index, open=df_candles['Open'], high=df_candles['High'], low=df_candles['Low'], close=df_candles['Close'], name="Price"), row=1, col=1)
    
    vol_colors = ['#26a69a' if c >= o else '#ef5350' for c, o in zip(df_candles['Close'], df_candles['Open'])]
    fig_vsa.add_trace(go.Bar(x=df_candles.index, y=df_candles['Volume'], marker_color=vol_colors, name="Volume"), row=2, col=1)
    fig_vsa.add_trace(go.Scatter(x=df_candles.index, y=df_candles['Vol_MA'], line=dict(color='orange', width=1.5), name="Vol MA"), row=2, col=1)
    
    fig_vsa.update_layout(height=550, template="plotly_dark", xaxis_rangeslider_visible=False, margin=dict(l=10, r=10, t=20, b=20))
    st.plotly_chart(fig_vsa, use_container_width=True)

    # Recent Signal Display
    latest = df_candles.iloc[-1]
    st.info(f"📍 **Latest Bar VSA Signal ({yf_symbol}):** {latest['VSA_Signal']}")

else:
    st.warning("⚠️ Live Candlestick data fetch limit reached or symbol formatting issue.")
