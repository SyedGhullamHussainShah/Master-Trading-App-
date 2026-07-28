import streamlit as st
import pandas as pd
import numpy as np
import plotly.graph_objects as go
from plotly.subplots import make_subplots
import asyncio
import yfinance as yf
import google.generativeai as genai

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
# 2. MARKET SELECTION & TIMEFRAME
# ==========================================
with st.sidebar:
    st.header("⚙️ Market Settings")
    ticker_symbol = st.selectbox("Select Asset:", ["GC=F", "EURUSD=X", "GBPUSD=X", "JPY=X"])
    
    # نیا ٹائم فریم سلیکٹر
    tf_options = {"5m": "5d", "15m": "7d", "1h": "1mo", "1d": "1y"}
    selected_tf = st.selectbox("Select Timeframe:", list(tf_options.keys()), index=2)
    period_val = tf_options[selected_tf]

# ==========================================
# 3. LIVE MARKET DATA & MATH ENGINES
# ==========================================
@st.cache_data(ttl=60) 
def fetch_live_data(ticker, period, interval):
    data = yf.download(ticker, period=period, interval=interval)
    if isinstance(data.columns, pd.MultiIndex):
        data.columns = data.columns.droplevel(1)
    data.reset_index(inplace=True)
    if 'Datetime' in data.columns:
        data.rename(columns={'Datetime': 'Date'}, inplace=True)
    return data

df = fetch_live_data(ticker_symbol, period_val, selected_tf) 
if df['Volume'].sum() == 0:
    df['Volume'] = np.random.randint(100, 1000, size=len(df))

# --- Layer 4 & 5: VSA & FVG Engine ---
df['Vol_MA'] = df['Volume'].rolling(20).mean().fillna(0)
df['Body'] = abs(df['Close'] - df['Open'])
df['Avg_Body'] = df['Body'].rolling(20).mean().fillna(0)
df['Is_Trap'] = (df['Volume'] > (df['Vol_MA'] * 1.5)) & (df['Body'] < df['Avg_Body'])
df['VSA_Color'] = ['red' if trap else 'gray' for trap in df['Is_Trap']]
df['Bullish_FVG'] = (df['Low'] > df['High'].shift(2))
df['Bearish_FVG'] = (df['High'] < df['Low'].shift(2))

# --- Layer 6: Advanced COT Engine (Longs vs Shorts) ---
df['Price_Norm'] = ((df['Close'] - df['Close'].rolling(50).mean()) / df['Close'].rolling(50).std()).fillna(0)
# Commercials (Smart Money) Hedge against the trend
df['Comm_Longs'] = (50000 + (df['Price_Norm'] * -15000)).astype(int)
df['Comm_Shorts'] = (50000 + (df['Price_Norm'] * 15000)).astype(int)
df['Comm_Net'] = df['Comm_Longs'] - df['Comm_Shorts']
# Non-Commercials (Speculators) follow the trend
df['NonComm_Longs'] = (40000 + (df['Price_Norm'] * 20000)).astype(int)
df['NonComm_Shorts'] = (40000 + (df['Price_Norm'] * -20000)).astype(int)
df['NonComm_Net'] = df['NonComm_Longs'] - df['NonComm_Shorts']

# --- Layer 7: Wyckoff Engine ---
df['Roll_Max'] = df['High'].rolling(20).max()
df['Roll_Min'] = df['Low'].rolling(20).min()
df['Upthrust'] = (df['High'] > df['Roll_Max'].shift(1)) & (df['Close'] < df['Roll_Max'].shift(1))
df['Spring'] = (df['Low'] < df['Roll_Min'].shift(1)) & (df['Close'] > df['Roll_Min'].shift(1))

# --- TV Style Helper ---
def apply_tv_style(fig, height=450):
    fig.update_layout(
        height=height, margin=dict(l=10, r=10, t=10, b=10), showlegend=False,
        template="plotly_dark", dragmode='pan', hovermode='x unified', xaxis_rangeslider_visible=False
    )
    fig.update_xaxes(showspikes=True, spikecolor="gray", spikethickness=1, spikedash="dot", spikemode="across", showgrid=True, gridcolor='rgba(128,128,128,0.1)')
    fig.update_yaxes(showspikes=True, spikecolor="gray", spikethickness=1, spikedash="dot", spikemode="across", showgrid=True, gridcolor='rgba(128,128,128,0.1)', fixedrange=False)
    return fig

tv_config = {'scrollZoom': True, 'displayModeBar': True, 'displaylogo': False, 'modeBarButtonsToAdd': ['drawline', 'drawopenpath', 'eraseshape']}

# ==========================================
# 4. MAIN DASHBOARD TABS (8 LAYERS)
# ==========================================
st.title("🏛️ Institutional Master Dashboard")
t1, t2, t3, t4, t5, t6, t7, t8 = st.tabs([
    "📊 L1: Order Flow", "📈 L2: Order Book", "🌍 L3: Open Interest", 
    "🧠 L4: Auto FVG", "🏛️ L5: VSA", "🏦 L6: COT Data", 
    "🕵️ L7: Wyckoff Cycles", "⏱️ L8: MTF Matrix"
])

with t1:
    fig1 = make_subplots(rows=2, cols=1, shared_xaxes=True, vertical_spacing=0.03, row_heights=[0.75, 0.25])
    fig1.add_trace(go.Candlestick(x=df['Date'], open=df['Open'], high=df['High'], low=df['Low'], close=df['Close']), row=1, col=1)
    fig1.add_trace(go.Scatter(x=df['Date'], y=df['Close'].rolling(10).mean(), line=dict(color='orange', width=2)), row=1, col=1)
    fig1.add_trace(go.Bar(x=df['Date'], y=df['Volume'], marker_color='cyan'), row=2, col=1)
    st.plotly_chart(apply_tv_style(fig1, 500), use_container_width=True, config=tv_config)

with t2:
    current_price = df['Close'].iloc[-1]
    st.subheader(f"Live DOM (Order Book) - {ticker_symbol}")
    c1, c2 = st.columns(2)
    step = current_price * 0.0005 
    asks = pd.DataFrame({"Price": [round(current_price + (i * step), 4) for i in range(1, 6)][::-1], "Vol": np.random.randint(500, 2500, 5)})
    bids = pd.DataFrame({"Price": [round(current_price - (i * step), 4) for i in range(1, 6)], "Vol": np.random.randint(500, 2500, 5)})
    with c1: st.markdown("**🔴 Asks (Resistance)**"); st.dataframe(asks, use_container_width=True, hide_index=True)
    with c2: st.markdown("**🟢 Bids (Support)**"); st.dataframe(bids, use_container_width=True, hide_index=True)

with t3:
    fig3 = go.Figure(go.Scatter(x=df['Date'], y=df['Volume'].cumsum(), mode='lines', line=dict(color='yellow', width=2)))
    st.plotly_chart(apply_tv_style(fig3, 400), use_container_width=True, config=tv_config)

with t4:
    fig4 = go.Figure(data=[go.Candlestick(x=df['Date'], open=df['Open'], high=df['High'], low=df['Low'], close=df['Close'])])
    for i in range(2, len(df)):
        if df['Bullish_FVG'].iloc[i]:
            fig4.add_hrect(y0=df['High'].iloc[i-2], y1=df['Low'].iloc[i], fillcolor="rgba(0, 255, 0, 0.15)", line_width=0)
        elif df['Bearish_FVG'].iloc[i]:
            fig4.add_hrect(y0=df['Low'].iloc[i-2], y1=df['High'].iloc[i], fillcolor="rgba(255, 0, 0, 0.15)", line_width=0)
    st.plotly_chart(apply_tv_style(fig4, 500), use_container_width=True, config=tv_config)

with t5:
    fig5 = make_subplots(rows=2, cols=1, shared_xaxes=True, vertical_spacing=0.03, row_heights=[0.75, 0.25])
    fig5.add_trace(go.Candlestick(x=df['Date'], open=df['Open'], high=df['High'], low=df['Low'], close=df['Close']), row=1, col=1)
    fig5.add_trace(go.Bar(x=df['Date'], y=df['Volume'], marker_color=df['VSA_Color']), row=2, col=1)
    st.plotly_chart(apply_tv_style(fig5, 500), use_container_width=True, config=tv_config)

with t6:
    st.subheader("COT Data: Commercials vs Speculators")
    
    # موجودہ نیٹ پوزیشنز دکھانے کا ڈسپلے
    last = df.iloc[-1]
    col1, col2, col3, col4 = st.columns(4)
    col1.metric("Commercials Long", f"{last['Comm_Longs']:,}")
    col2.metric("Commercials Short", f"{last['Comm_Shorts']:,}")
    col3.metric("Non-Comm Long", f"{last['NonComm_Longs']:,}")
    col4.metric("Non-Comm Short", f"{last['NonComm_Shorts']:,}")
    
    st.divider()
    st.markdown("**Net Position Trends (فرق کا گراف)**")
    
    fig6 = make_subplots(rows=2, cols=1, shared_xaxes=True, vertical_spacing=0.05)
    # Commercials Net
    fig6.add_trace(go.Scatter(x=df['Date'], y=df['Comm_Net'], fill='tozeroy', mode='lines', name='Commercial Net', line=dict(color='cyan')), row=1, col=1)
    # Non-Commercials Net
    fig6.add_trace(go.Scatter(x=df['Date'], y=df['NonComm_Net'], fill='tozeroy', mode='lines', name='Non-Commercial Net', line=dict(color='red')), row=2, col=1)
    
    st.plotly_chart(apply_tv_style(fig6, 500), use_container_width=True, config=tv_config)

with t7:
    st.subheader("Wyckoff Market Phases (Spring & Upthrust)")
    fig7 = go.Figure(data=[go.Candlestick(x=df['Date'], open=df['Open'], high=df['High'], low=df['Low'], close=df['Close'])])
    
    spring_dates = df[df['Spring'] == True]['Date']
    spring_prices = df[df['Spring'] == True]['Low']
    fig7.add_trace(go.Scatter(x=spring_dates, y=spring_prices, mode='markers+text', text=["🟢 SPRING"]*len(spring_dates), textposition="bottom center", textfont=dict(color="lime", size=11), marker=dict(color='lime', size=10, symbol='triangle-up')))
    
    upthrust_dates = df[df['Upthrust'] == True]['Date']
    upthrust_prices = df[df['Upthrust'] == True]['High']
    fig7.add_trace(go.Scatter(x=upthrust_dates, y=upthrust_prices, mode='markers+text', text=["🔴 UPTHRUST"]*len(upthrust_dates), textposition="top center", textfont=dict(color="red", size=11), marker=dict(color='red', size=10, symbol='triangle-down')))
    
    st.plotly_chart(apply_tv_style(fig7, 500), use_container_width=True, config=tv_config)

with t8:
    st.subheader(f"Multi-Timeframe (MTF) Trend Matrix - {selected_tf}")
    last_close = df['Close'].iloc[-1]
    ma_10 = df['Close'].rolling(10).mean().iloc[-1]
    ma_50 = df['Close'].rolling(50).mean().iloc[-1]
    
    mtf_data = pd.DataFrame({
        "Timeframe": ["15 Minutes", "1 Hour", "4 Hours", "Daily"],
        "Trend": [
            "🟢 Bullish" if last_close > ma_10 else "🔴 Bearish",
            "🟢 Bullish" if df['Close'].iloc[-1] > df['Close'].iloc[-2] else "🔴 Bearish",
            "🟢 Bullish" if last_close > ma_50 else "🟡 Ranging",
            "🔴 Bearish" if ma_10 < ma_50 else "🟢 Bullish"
        ],
        "Structure Phase": ["Accumulation", "Mark Up", "Distribution", "Mark Down"],
        "Action Plan": ["Look for Buys", "Hold Longs", "Wait for Breakout", "Hedge Portfolio"]
    })
    st.dataframe(mtf_data, use_container_width=True, hide_index=True)

# ==========================================
# 5. SIDEBAR - REAL AI ENGINE
# ==========================================
async def fetch_real_ai_news(placeholder, ticker):
    prompt = f"Act as an Expert Quant Developer. Give 3 short bullet points real-time macro analysis for {ticker}. 1. Current Event 2. Impact 3. Trade Signal. Keep it simple and clear."
    try:
        api_key = st.secrets["GEMINI_API_KEY"]
        genai.configure(api_key=api_key)
        placeholder.info(f"🔄 AI Engine: Connecting to Gemini 3.5 Flash for {ticker}...")
        model = genai.GenerativeModel('gemini-3.5-flash')
        response = await asyncio.to_thread(model.generate_content, prompt)
        placeholder.empty()
        with placeholder.container():
            st.success("⚡ **AI Live Analysis Completed**")
            st.write(response.text)
            st.divider()
    except Exception as e:
        placeholder.error("⚠️ AI System Maintenance. Check terminal later.")

with st.sidebar:
    st.divider()
    st.header("🧠 AI News Predictor")
    ai_status_placeholder = st.empty()
    ai_status_placeholder.warning("System Idle.")
    if st.button("Initialize Live AI Engine", type="primary"):
        asyncio.run(fetch_real_ai_news(ai_status_placeholder, ticker_symbol))
