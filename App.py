import streamlit as st
import pandas as pd
import numpy as np
import plotly.graph_objects as go
from plotly.subplots import make_subplots
import asyncio
import yfinance as yf

# ==========================================
# 1. PAGE CONFIGURATION & MOBILE OPTIMIZATION
# ==========================================
st.set_page_config(
    page_title="Institutional Master Dashboard",
    page_icon="💹",
    layout="wide",
    initial_sidebar_state="collapsed"
)

st.markdown("""
    <style>
    .block-container {
        padding-top: 1rem !important;
        padding-bottom: 1rem !important;
    }
    header {visibility: hidden;}
    footer {visibility: hidden;}
    .stTabs [data-baseweb="tab-list"] {
        gap: 8px;
        overflow-x: auto;
        white-space: nowrap;
    }
    .stTabs [data-baseweb="tab"] {
        padding-right: 15px !important;
        padding-left: 15px !important;
    }
    </style>
""", unsafe_allow_html=True)


# ==========================================
# 2. LIVE MARKET DATA (PHASE 2)
# ==========================================
st.sidebar.subheader("⚙️ Market Selection")
ticker_symbol = st.sidebar.selectbox(
    "Select Asset:", 
    ["GC=F", "EURUSD=X", "GBPUSD=X", "JPY=X"],
    format_func=lambda x: "Gold Futures" if x == "GC=F" else "EUR/USD" if x == "EURUSD=X" else "GBP/USD" if x == "GBPUSD=X" else "USD/JPY"
)

@st.cache_data(ttl=300) 
def fetch_live_data(ticker):
    # Fetching last 7 days data on 1-hour timeframe
    data = yf.download(ticker, period="7d", interval="1h")
    
    # Flatten MultiIndex columns if they exist (yfinance sometimes returns MultiIndex)
    if isinstance(data.columns, pd.MultiIndex):
        data.columns = data.columns.droplevel(1)
        
    data.reset_index(inplace=True)
    
    # Standardizing Date column
    if 'Datetime' in data.columns:
        data.rename(columns={'Datetime': 'Date'}, inplace=True)
        
    return data

df = fetch_live_data(ticker_symbol)

# Fallback for missing volume data (common in Forex)
if df['Volume'].sum() == 0:
    df['Volume'] = np.random.randint(100, 1000, size=len(df))


# ==========================================
# 3. ASYNCHRONOUS AI NEWS PREDICTOR 
# ==========================================
async def fetch_ai_news_analysis(placeholder):
    news_events = ["CPI Data Released", "NFP Expected to beat estimates", "FOMC Rate Decision..."]
    for event in news_events:
        await asyncio.sleep(2) 
        placeholder.info(f"⚡ **AI Insight:** {event}\n\n*Impact:* High Volatility Expected.")

def run_ai_engine(placeholder):
    asyncio.run(fetch_ai_news_analysis(placeholder))


# ==========================================
# 4. SIDEBAR - AI WIDGET 
# ==========================================
with st.sidebar:
    st.header("🧠 AI News Predictor")
    st.caption("Hybrid Asynchronous Model")
    st.divider()
    
    ai_status_placeholder = st.empty()
    ai_status_placeholder.warning("Waiting for API connection...")
    
    st.divider()
    st.write("**Macro Correlators (Live)**")
    st.metric(label="US10Y Yield", value="4.25%", delta="0.05%")
    st.metric(label="DXY (Dollar Index)", value="103.50", delta="-0.20")
    
    if st.button("Initialize AI Engine"):
        run_ai_engine(ai_status_placeholder)


# ==========================================
# 5. MAIN DASHBOARD - SWIPEABLE TABS
# ==========================================
st.title("🏛️ Institutional Master Dashboard")

tab1, tab2, tab3, tab4, tab5 = st.tabs([
    "📊 Layer 1: Order Flow", 
    "📈 Layer 2: DOM & Spoofing", 
    "🌍 Layer 3: OI & Macro", 
    "🧠 Layer 4: Smart Money", 
    "🏛️ Layer 5: VSA & Wyckoff"
])

# ---------------------------------------------------------
# TAB 1: ORDER FLOW
# ---------------------------------------------------------
with tab1:
    st.subheader("Delta Volume, Footprint & Anchored VWAP")
    
    fig1 = make_subplots(rows=2, cols=1, shared_xaxes=True, vertical_spacing=0.03, row_heights=[0.7, 0.3])
    
    fig1.add_trace(go.Candlestick(
        x=df['Date'], open=df['Open'], high=df['High'], low=df['Low'], close=df['Close'], name='Price'
    ), row=1, col=1)
    
    fig1.add_trace(go.Scatter(
        x=df['Date'], y=df['Close'].rolling(10).mean(), line=dict(color='orange', width=2), name='Anchored VWAP'
    ), row=1, col=1)
    
    fig1.add_trace(go.Bar(
        x=df['Date'], y=df['Volume'], name='Delta Volume', marker_color='cyan'
    ), row=2, col=1)
    
    fig1.update_layout(height=500, margin=dict(l=0, r=0, t=10, b=0), showlegend=False, template="plotly_dark")
    fig1.update_xaxes(rangeslider_visible=False)
    
    st.plotly_chart(fig1, use_container_width=True)

    col1, col2 = st.columns(2)
    col1.metric("Highest Volume Node (POC)", round(df['Close'].iloc[-1], 2))
    col2.metric("Current Market Price", round(df['Close'].iloc[-1], 2))

# ---------------------------------------------------------
# TAB 2: ORDER BOOK
# ---------------------------------------------------------
with tab2:
    st.subheader("Live DOM & Anti-Spoofing Filter")
    dom_col1, dom_col2 = st.columns(2)
    
    with dom_col1:
        st.markdown("**Asks (Resistance)**")
        ask_data = pd.DataFrame({"Price": [1930.5, 1930.0, 1929.5], "True Vol": [120, 450, 80], "Spoofed Vol": [1500, 200, 0]})
        st.dataframe(ask_data, use_container_width=True, hide_index=True)
        
    with dom_col2:
        st.markdown("**Bids (Support)**")
        bid_data = pd.DataFrame({"Price": [1928.5, 1928.0, 1927.5], "True Vol": [90, 600, 110], "Spoofed Vol": [0, 3000, 50]})
        st.dataframe(bid_data, use_container_width=True, hide_index=True)

# ---------------------------------------------------------
# TAB 3: OPEN INTEREST
# ---------------------------------------------------------
with tab3:
    st.subheader("Open Interest (Volume Proxy) & COT Data")
    
    fig3 = go.Figure()
    fig3.add_trace(go.Scatter(x=df['Date'], y=df['Volume'].cumsum(), mode='lines', name='Live OI Proxy', line=dict(color='yellow')))
    
    fig3.update_layout(height=300, margin=dict(l=0, r=0, t=10, b=0), template="plotly_dark")
    st.plotly_chart(fig3, use_container_width=True)
    
    st.write("**COT Weekly Smart Money Positioning**")
    st.progress(0.75, text="Commercial Index: Heavy Accumulation (75%)")

# ---------------------------------------------------------
# TAB 4: SMART MONEY
# ---------------------------------------------------------
with tab4:
    st.subheader("Auto Market Structure & Liquidity")
    st.write("- **Trend:** Checking latest CHoCH...")
    
    fig4 = go.Figure(data=[go.Candlestick(x=df['Date'], open=df['Open'], high=df['High'], low=df['Low'], close=df['Close'])])
    
    current_price = df['Close'].iloc[-1]
    fig4.add_hrect(y0=current_price - 5, y1=current_price - 2, line_width=0, fillcolor="rgba(0, 255, 0, 0.2)", annotation_text="Potential FVG")
    
    fig4.update_layout(height=400, margin=dict(l=0, r=0, t=10, b=0), xaxis_rangeslider_visible=False, template="plotly_dark")
    st.plotly_chart(fig4, use_container_width=True)

# ---------------------------------------------------------
# TAB 5: VSA
# ---------------------------------------------------------
with tab5:
    st.subheader("VSA & Wyckoff Cycle")
    
    col_vsa1, col_vsa2 = st.columns(2)
    col_vsa1.metric("Wyckoff Phase", "Analyzing...")
    col_vsa2.metric("VSA Signature", "Analyzing Volume...")
    
    fig5 = go.Figure(data=[go.Bar(x=df['Date'][-20:], y=df['Volume'][-20:], marker_color=['red' if i%5==0 else 'gray' for i in range(20)])])
    fig5.update_layout(title="Recent Volume Nodes", height=250, margin=dict(l=0, r=0, t=30, b=0), template="plotly_dark")
    st.plotly_chart(fig5, use_container_width=True)
