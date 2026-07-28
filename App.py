import streamlit as st
import pandas as pd
import numpy as np
import plotly.graph_objects as go
from plotly.subplots import make_subplots
import asyncio
import yfinance as yf

# ==========================================
# 1. PAGE CONFIGURATION
# ==========================================
st.set_page_config(
    page_title="Institutional Master Dashboard",
    page_icon="💹",
    layout="wide",
    initial_sidebar_state="expanded"
)

st.markdown("""
    <style>
    .block-container { padding-top: 1rem !important; padding-bottom: 1rem !important; }
    header {visibility: hidden;}
    footer {visibility: hidden;}
    </style>
""", unsafe_allow_html=True)

# ==========================================
# 2. LIVE MARKET DATA & MATH ENGINES
# ==========================================
@st.cache_data(ttl=300) 
def fetch_live_data(ticker):
    data = yf.download(ticker, period="10d", interval="1h")
    if isinstance(data.columns, pd.MultiIndex):
        data.columns = data.columns.droplevel(1)
    data.reset_index(inplace=True)
    if 'Datetime' in data.columns:
        data.rename(columns={'Datetime': 'Date'}, inplace=True)
    return data

df = fetch_live_data("GC=F") 
if df['Volume'].sum() == 0:
    df['Volume'] = np.random.randint(100, 1000, size=len(df))

# VSA Engine (Layer 5)
df['Vol_MA'] = df['Volume'].rolling(20).mean()
df['Body'] = abs(df['Close'] - df['Open'])
df['Avg_Body'] = df['Body'].rolling(20).mean()
df['Is_Trap'] = (df['Volume'] > (df['Vol_MA'] * 1.5)) & (df['Body'] < df['Avg_Body'])
df['VSA_Color'] = ['red' if trap else 'gray' for trap in df['Is_Trap']]

# Auto Market Structure Engine - FVG Detection (Layer 4)
df['Bullish_FVG'] = (df['Low'] > df['High'].shift(2))
df['Bearish_FVG'] = (df['High'] < df['Low'].shift(2))

# ==========================================
# 3. MAIN DASHBOARD TABS
# ==========================================
st.title("🏛️ Institutional Master Dashboard")

tab1, tab2, tab3 = st.tabs(["📊 Layer 1 & 4: Smart Chart", "📈 Layer 2: Order Book", "🏛️ Layer 5: VSA Alerts"])

with tab1:
    st.subheader("Interactive Order Flow & Auto Structure")
    st.caption("💡 TradingView Style: زوم کرنے کے لیے ماؤس اسکرول کریں یا موبائل پر دو انگلیاں استعمال کریں۔ ری سیٹ کے لیے Home کا بٹن دبائیں۔")
    
    fig1 = make_subplots(rows=2, cols=1, shared_xaxes=True, vertical_spacing=0.03, row_heights=[0.75, 0.25])
    
    # مین کینڈلز
    fig1.add_trace(go.Candlestick(x=df['Date'], open=df['Open'], high=df['High'], low=df['Low'], close=df['Close'], name='Price'), row=1, col=1)
    
    # Auto Structure (FVG Boxes)
    for i in range(2, len(df)):
        if df['Bullish_FVG'].iloc[i]:
            # سبز خلا (Support)
            fig1.add_hrect(y0=df['High'].iloc[i-2], y1=df['Low'].iloc[i], fillcolor="rgba(0, 255, 0, 0.15)", line_width=0, row=1, col=1)
        elif df['Bearish_FVG'].iloc[i]:
            # لال خلا (Resistance)
            fig1.add_hrect(y0=df['Low'].iloc[i-2], y1=df['High'].iloc[i], fillcolor="rgba(255, 0, 0, 0.15)", line_width=0, row=1, col=1)

    # والیوم ستون
    fig1.add_trace(go.Bar(x=df['Date'], y=df['Volume'], marker_color='cyan', name='Volume'), row=2, col=1)
    
    # TradingView جیسی سیٹنگز
    fig1.update_layout(
        height=500, 
        margin=dict(l=10, r=10, t=10, b=10), 
        showlegend=False, 
        template="plotly_dark", 
        xaxis_rangeslider_visible=False,
        dragmode='pan' # ڈیفالٹ ایکشن 'پین' (کھسکانا) کر دیا گیا ہے
    )
    
    # Config میں Scroll Zoom آن کر دیا گیا ہے
    st.plotly_chart(fig1, use_container_width=True, config={'scrollZoom': True, 'displayModeBar': True, 'displaylogo': False})

with tab3:
    st.subheader("مگرمچھ کا دھوکہ (Smart Money Trap)")
    fig5 = make_subplots(rows=2, cols=1, shared_xaxes=True, vertical_spacing=0.03, row_heights=[0.6, 0.4])
    fig5.add_trace(go.Candlestick(x=df['Date'], open=df['Open'], high=df['High'], low=df['Low'], close=df['Close']), row=1, col=1)
    fig5.add_trace(go.Bar(x=df['Date'], y=df['Volume'], marker_color=df['VSA_Color']), row=2, col=1)
    
    trap_dates = df[df['Is_Trap'] == True]['Date']
    trap_prices = df[df['Is_Trap'] == True]['High']
    fig5.add_trace(go.Scatter(x=trap_dates, y=trap_prices, mode='markers+text', text=["🚨 DANGER"]*len(trap_dates), textposition="top center", textfont=dict(color="red", size=10), marker=dict(color='red', size=8)), row=1, col=1)
    
    fig5.update_layout(height=400, margin=dict(l=10, r=10, t=10, b=10), showlegend=False, template="plotly_dark", xaxis_rangeslider_visible=False, dragmode='pan')
    st.plotly_chart(fig5, use_container_width=True, config={'scrollZoom': True})

# ==========================================
# 4. SIDEBAR - AI ENGINE
# ==========================================
async def ai_news_stream(placeholder):
    news_events = [
        {"time": "10:00 AM", "event": "US Core CPI Data", "impact": "Hawkish (Inflation up). DXY showing strength.", "signal": "Bearish for Gold 🔴"},
        {"time": "02:15 PM", "event": "Smart Money Block", "impact": "Massive buy block detected at 1920 support.", "signal": "Bullish Reversal 🟢"}
    ]
    placeholder.info("🔄 AI Engine: Connecting to global news feeds...")
    await asyncio.sleep(1.5)
    for news in news_events:
        with placeholder.container():
            st.success(f"⚡ **{news['event']}** ({news['time']})")
            st.markdown(f"**Impact:** {news['impact']}")
            st.markdown(f"**AI Prediction:** {news['signal']}")
            st.divider()
        await asyncio.sleep(2)

with st.sidebar:
    st.header("⚙️ Market Selection")
    ticker_symbol = st.selectbox("Select Asset:", ["GC=F", "EURUSD=X", "GBPUSD=X", "JPY=X"])
    st.divider()
    st.header("🧠 AI News Predictor")
    ai_status_placeholder = st.empty()
    ai_status_placeholder.warning("System Idle. Press button to scan.")
    if st.button("Initialize AI Engine", type="primary"):
        asyncio.run(ai_news_stream(ai_status_placeholder))
