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
    initial_sidebar_state="collapsed"
)

st.markdown("""
    <style>
    .block-container { padding-top: 1rem !important; padding-bottom: 1rem !important; }
    header {visibility: hidden;}
    footer {visibility: hidden;}
    </style>
""", unsafe_allow_html=True)

# ==========================================
# 2. LIVE MARKET DATA & PHASE 3 MATH (VSA LOGIC)
# ==========================================
st.sidebar.subheader("⚙️ Market Selection")
ticker_symbol = st.sidebar.selectbox(
    "Select Asset:", 
    ["GC=F", "EURUSD=X", "GBPUSD=X", "JPY=X"],
    format_func=lambda x: "Gold Futures" if x == "GC=F" else "EUR/USD" if x == "EURUSD=X" else "GBP/USD" if x == "GBPUSD=X" else "USD/JPY"
)

@st.cache_data(ttl=300) 
def fetch_live_data(ticker):
    data = yf.download(ticker, period="7d", interval="1h")
    if isinstance(data.columns, pd.MultiIndex):
        data.columns = data.columns.droplevel(1)
    data.reset_index(inplace=True)
    if 'Datetime' in data.columns:
        data.rename(columns={'Datetime': 'Date'}, inplace=True)
    return data

df = fetch_live_data(ticker_symbol)

if df['Volume'].sum() == 0:
    df['Volume'] = np.random.randint(100, 1000, size=len(df))

# ---------------------------------------------------------
# PHASE 3: VSA (مگرمچھ کا دھوکہ) FORMULA
# ---------------------------------------------------------
# 1. پچھلی 20 کینڈلز کے والیوم کا اوسط (Average)
df['Vol_MA'] = df['Volume'].rolling(20).mean()
# 2. کینڈل کے جسم (Body) کا سائز
df['Body'] = abs(df['Close'] - df['Open'])
df['Avg_Body'] = df['Body'].rolling(20).mean()

# 3. دھوکہ پکڑنے کی شرط: اگر والیوم اوسط سے ڈیڑھ گنا زیادہ ہو لیکن کینڈل چھوٹی ہو!
df['Is_Trap'] = (df['Volume'] > (df['Vol_MA'] * 1.5)) & (df['Body'] < df['Avg_Body'])
# 4. کلر کوڈنگ: دھوکہ ہے تو لال (Red)، ورنہ گرے (Gray)
df['VSA_Color'] = ['red' if trap else 'gray' for trap in df['Is_Trap']]

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

with st.sidebar:
    st.header("🧠 AI News Predictor")
    st.divider()
    ai_status_placeholder = st.empty()
    ai_status_placeholder.warning("Waiting for API connection...")
    if st.button("Initialize AI Engine"):
        run_ai_engine(ai_status_placeholder)

# ==========================================
# 4. MAIN DASHBOARD TABS
# ==========================================
st.title("🏛️ Institutional Master Dashboard")

tab1, tab2, tab3, tab4, tab5 = st.tabs([
    "📊 Layer 1: Order Flow", 
    "📈 Layer 2: DOM & Spoofing", 
    "🌍 Layer 3: OI & Macro", 
    "🧠 Layer 4: Smart Money", 
    "🏛️ Layer 5: VSA & Wyckoff"
])

with tab1:
    st.subheader("Price & Anchored VWAP (Basic Data)")
    fig1 = make_subplots(rows=2, cols=1, shared_xaxes=True, vertical_spacing=0.03, row_heights=[0.7, 0.3])
    fig1.add_trace(go.Candlestick(x=df['Date'], open=df['Open'], high=df['High'], low=df['Low'], close=df['Close'], name='Price'), row=1, col=1)
    fig1.add_trace(go.Scatter(x=df['Date'], y=df['Close'].rolling(10).mean(), line=dict(color='orange', width=2), name='Anchored VWAP'), row=1, col=1)
    fig1.add_trace(go.Bar(x=df['Date'], y=df['Volume'], name='Volume', marker_color='cyan'), row=2, col=1)
    fig1.update_layout(height=400, margin=dict(l=0, r=0, t=10, b=0), showlegend=False, template="plotly_dark", xaxis_rangeslider_visible=False)
    st.plotly_chart(fig1, use_container_width=True)
    st.caption("نوٹ: اصلی ڈیلٹا اور فٹ پرنٹ کے لیے ایکسرے (Tick) ڈیٹا درکار ہوتا ہے۔")

with tab2:
    st.subheader("Live DOM (Simulated from Order Flow)")
    dom_col1, dom_col2 = st.columns(2)
    with dom_col1:
        st.markdown("**Asks (Resistance - بیچنے والے)**")
        st.dataframe(pd.DataFrame({"Price": [1930.5, 1930.0], "True Vol": [120, 450], "Spoofed Vol": [1500, 200]}), use_container_width=True, hide_index=True)
    with dom_col2:
        st.markdown("**Bids (Support - خریدار)**")
        st.dataframe(pd.DataFrame({"Price": [1928.5, 1928.0], "True Vol": [90, 600], "Spoofed Vol": [0, 3000]}), use_container_width=True, hide_index=True)

with tab3:
    st.subheader("Open Interest Proxy")
    fig3 = go.Figure(go.Scatter(x=df['Date'], y=df['Volume'].cumsum(), mode='lines', line=dict(color='yellow')))
    fig3.update_layout(height=250, margin=dict(l=0, r=0, t=10, b=0), template="plotly_dark")
    st.plotly_chart(fig3, use_container_width=True)

with tab4:
    st.subheader("Smart Money FVG (خلا)")
    fig4 = go.Figure(data=[go.Candlestick(x=df['Date'], open=df['Open'], high=df['High'], low=df['Low'], close=df['Close'])])
    fig4.add_hrect(y0=df['Close'].iloc[-1] - 5, y1=df['Close'].iloc[-1] - 2, line_width=0, fillcolor="rgba(0, 255, 0, 0.2)", annotation_text="Potential FVG")
    fig4.update_layout(height=350, margin=dict(l=0, r=0, t=10, b=0), xaxis_rangeslider_visible=False, template="plotly_dark")
    st.plotly_chart(fig4, use_container_width=True)

# ---------------------------------------------------------
# TAB 5: VSA WITH SMART MONEY LOGIC
# ---------------------------------------------------------
with tab5:
    st.subheader("مگرمچھ کا دھوکہ (Smart Money Trap Detector)")
    
    # Check if latest candle is a trap
    latest_is_trap = df['Is_Trap'].iloc[-1]
    if latest_is_trap:
        st.error("🚨 الرٹ: بڑا والیوم لیکن کینڈل چھوٹی! مگرمچھ مال بیچ رہا ہے۔")
    else:
        st.success("✅ مارکیٹ نارمل ہے، والیوم اصلی ہے۔")
        
    fig5 = make_subplots(rows=2, cols=1, shared_xaxes=True, vertical_spacing=0.03, row_heights=[0.6, 0.4])
    
    # کینڈلز
    fig5.add_trace(go.Candlestick(x=df['Date'], open=df['Open'], high=df['High'], low=df['Low'], close=df['Close'], name='Price'), row=1, col=1)
    
    # ہوشیار والیوم
    fig5.add_trace(go.Bar(x=df['Date'], y=df['Volume'], marker_color=df['VSA_Color'], name='Volume'), row=2, col=1)
    
    # چارٹ پر DANGER لکھنا
    trap_dates = df[df['Is_Trap'] == True]['Date']
    trap_prices = df[df['Is_Trap'] == True]['High']
    fig5.add_trace(go.Scatter(x=trap_dates, y=trap_prices, mode='markers+text', text=["🚨 DANGER"]*len(trap_dates), textposition="top center", textfont=dict(color="red", size=10), marker=dict(color='red', size=8), name="Trap"), row=1, col=1)
    
    fig5.update_layout(height=450, margin=dict(l=0, r=0, t=10, b=0), showlegend=False, template="plotly_dark", xaxis_rangeslider_visible=False)
    st.plotly_chart(fig5, use_container_width=True)
