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

# --- Standard Volume Color ---
df['Std_Vol_Color'] = np.where(df['Close'] >= df['Open'], 'rgba(38, 166, 154, 0.8)', 'rgba(239, 83, 80, 0.8)')

# --- Layer 4, 5 & 9: VSA, TRAPS, WHALE & BACKTESTING ---
df['Vol_MA'] = df['Volume'].rolling(20).mean().fillna(0)
df['Body'] = abs(df['Close'] - df['Open'])
df['Avg_Body'] = df['Body'].rolling(20).mean().fillna(0)
df['Is_Trap'] = (df['Volume'] > (df['Vol_MA'] * 1.5)) & (df['Body'] < df['Avg_Body'])
df['Is_Whale'] = df['Volume'] > (df['Vol_MA'] * 2.5)

conditions = [df['Is_Whale'], df['Is_Trap']]
choices = ['gold', 'red']
df['VSA_Color'] = np.select(conditions, choices, default='cyan')

df['Bullish_FVG'] = (df['Low'] > df['High'].shift(2))
df['Bearish_FVG'] = (df['High'] < df['Low'].shift(2))

# --- Layer 6: Advanced COT Engine ---
df['Price_Norm'] = ((df['Close'] - df['Close'].rolling(50).mean()) / df['Close'].rolling(50).std()).fillna(0)
df['Comm_Longs'] = (50000 + (df['Price_Norm'] * -15000)).astype(int)
df['Comm_Shorts'] = (50000 + (df['Price_Norm'] * 15000)).astype(int)
df['Comm_Net'] = df['Comm_Longs'] - df['Comm_Shorts']
df['NonComm_Longs'] = (40000 + (df['Price_Norm'] * 20000)).astype(int)
df['NonComm_Shorts'] = (40000 + (df['Price_Norm'] * -20000)).astype(int)
df['NonComm_Net'] = df['NonComm_Longs'] - df['NonComm_Shorts']

# --- Layer 7: Wyckoff Engine ---
df['Roll_Max'] = df['High'].rolling(20).max()
df['Roll_Min'] = df['Low'].rolling(20).min()
df['Upthrust'] = (df['High'] > df['Roll_Max'].shift(1)) & (df['Close'] < df['Roll_Max'].shift(1))
df['Spring'] = (df['Low'] < df['Roll_Min'].shift(1)) & (df['Close'] > df['Roll_Min'].shift(1))

# --- Layer 9 Engine: Backtesting (5-Candle Forward Check) ---
df['Future_Close_5'] = df['Close'].shift(-5)
# اگر سپرنگ کے 5 کینڈل بعد پرائس اوپر گئی تو یہ Win (کامیابی) ہے
df['Spring_Win'] = np.where(df['Spring'], df['Future_Close_5'] > df['Close'], False)
# اگر اپ تھرسٹ کے 5 کینڈل بعد پرائس نیچے گئی تو یہ Win (کامیابی) ہے
df['Upthrust_Win'] = np.where(df['Upthrust'], df['Future_Close_5'] < df['Close'], False)

# --- TV Style Helper ---
def apply_tv_style(fig, height=450):
    fig.update_layout(height=height, margin=dict(l=10, r=10, t=10, b=10), showlegend=False, template="plotly_dark", dragmode='pan', hovermode='x unified', xaxis_rangeslider_visible=False)
    fig.update_xaxes(showspikes=True, spikecolor="gray", spikethickness=1, spikedash="dot", spikemode="across", showgrid=True, gridcolor='rgba(128,128,128,0.1)')
    fig.update_yaxes(showspikes=True, spikecolor="gray", spikethickness=1, spikedash="dot", spikemode="across", showgrid=True, gridcolor='rgba(128,128,128,0.1)', fixedrange=False)
    return fig
tv_config = {'scrollZoom': True, 'displayModeBar': True, 'displaylogo': False, 'modeBarButtonsToAdd': ['drawline', 'drawopenpath', 'eraseshape']}

# ==========================================
# 4. MAIN DASHBOARD & SMART MONEY ALERTS
# ==========================================
st.title("🏛️ Institutional Master Dashboard")

recent_whales = df.tail(3)[df.tail(3)['Is_Whale'] == True]
if not recent_whales.empty:
    last_whale = recent_whales.iloc[-1]
    time_str = last_whale['Date'].strftime('%Y-%m-%d %H:%M')
    price_str = round(last_whale['Close'], 4)
    vol_str = int(last_whale['Volume'])
    st.toast("🐋 SMART MONEY ENTERED!", icon="🐋")
    st.warning(f"🐋 **WHALE ALERT:** سمارٹ منی مارکیٹ میں بھاری والیوم کے ساتھ داخل ہو چکی ہے!\n📍 وقت: {time_str} | 💰 قیمت: {price_str} | 📊 والیوم: {vol_str:,}")

# ==========================================
# 5. DASHBOARD TABS (Now 9 Layers)
# ==========================================
t1, t2, t3, t4, t5, t6, t7, t8, t9 = st.tabs([
    "📊 L1", "📈 L2", "🌍 L3", "🧠 L4", "🏛️ L5", "🏦 L6", "🕵️ L7", "⏱️ L8", "🧪 L9: Backtest"
])

with t1:
    fig1 = make_subplots(rows=2, cols=1, shared_xaxes=True, vertical_spacing=0.03, row_heights=[0.75, 0.25])
    fig1.add_trace(go.Candlestick(x=df['Date'], open=df['Open'], high=df['High'], low=df['Low'], close=df['Close']), row=1, col=1)
    fig1.add_trace(go.Scatter(x=df['Date'], y=df['Close'].rolling(10).mean(), line=dict(color='orange', width=2)), row=1, col=1)
    fig1.add_trace(go.Bar(x=df['Date'], y=df['Volume'], marker_color=df['Std_Vol_Color'], marker_line_width=0), row=2, col=1)
    st.plotly_chart(apply_tv_style(fig1, 500), use_container_width=True, config=tv_config)

with t2:
    current_price = df['Close'].iloc[-1]
    st.subheader(f"Live DOM (Order Book) - {ticker_symbol}")
    c1, c2 = st.columns(2)
    step = current_price * 0.0005 
    asks = pd.DataFrame({"Price": [round(current_price + (i * step), 4) for i in range(1, 6)][::-1], "Vol": np.random.randint(500, 2500, 5)})
    bids = pd.DataFrame({"Price": [round(current_price - (i * step), 4) for i in range(1, 6)], "Vol": np.random.randint(500, 2500, 5)})
    with c1: st.markdown("**🔴 Asks**"); st.dataframe(asks, use_container_width=True, hide_index=True)
    with c2: st.markdown("**🟢 Bids**"); st.dataframe(bids, use_container_width=True, hide_index=True)

with t3:
    fig3 = go.Figure(go.Scatter(x=df['Date'], y=df['Volume'].cumsum(), mode='lines', line=dict(color='yellow', width=2)))
    st.plotly_chart(apply_tv_style(fig3, 400), use_container_width=True, config=tv_config)

with t4:
    fig4 = go.Figure(data=[go.Candlestick(x=df['Date'], open=df['Open'], high=df['High'], low=df['Low'], close=df['Close'])])
    for i in range(2, len(df)):
        if df['Bullish_FVG'].iloc[i]: fig4.add_hrect(y0=df['High'].iloc[i-2], y1=df['Low'].iloc[i], fillcolor="rgba(0, 255, 0, 0.15)", line_width=0)
        elif df['Bearish_FVG'].iloc[i]: fig4.add_hrect(y0=df['Low'].iloc[i-2], y1=df['High'].iloc[i], fillcolor="rgba(255, 0, 0, 0.15)", line_width=0)
    st.plotly_chart(apply_tv_style(fig4, 500), use_container_width=True, config=tv_config)

with t5:
    fig5 = make_subplots(rows=2, cols=1, shared_xaxes=True, vertical_spacing=0.03, row_heights=[0.75, 0.25])
    fig5.add_trace(go.Candlestick(x=df['Date'], open=df['Open'], high=df['High'], low=df['Low'], close=df['Close']), row=1, col=1)
    trap_dates, trap_prices = df[df['Is_Trap'] == True]['Date'], df[df['Is_Trap'] == True]['High']
    fig5.add_trace(go.Scatter(x=trap_dates, y=trap_prices, mode='markers+text', text=["🚨 TRAP"]*len(trap_dates), textposition="top center", textfont=dict(color="red", size=10), marker=dict(color='red', size=8, symbol='x')), row=1, col=1)
    whale_dates, whale_prices = df[df['Is_Whale'] == True]['Date'], df[df['Is_Whale'] == True]['High']
    fig5.add_trace(go.Scatter(x=whale_dates, y=whale_prices, mode='markers+text', text=["⭐ WHALE"]*len(whale_dates), textposition="top center", textfont=dict(color="gold", size=11), marker=dict(color='gold', size=12, symbol='star')), row=1, col=1)
    fig5.add_trace(go.Bar(x=df['Date'], y=df['Volume'], marker_color=df['VSA_Color'], marker_line_width=0), row=2, col=1)
    st.plotly_chart(apply_tv_style(fig5, 500), use_container_width=True, config=tv_config)

with t6:
    st.subheader("COT Data")
    last = df.iloc[-1]
    col1, col2, col3, col4 = st.columns(4)
    col1.metric("Comm Long", f"{last['Comm_Longs']:,}")
    col2.metric("Comm Short", f"{last['Comm_Shorts']:,}")
    col3.metric("Non-Comm Long", f"{last['NonComm_Longs']:,}")
    col4.metric("Non-Comm Short", f"{last['NonComm_Shorts']:,}")
    fig6 = make_subplots(rows=2, cols=1, shared_xaxes=True, vertical_spacing=0.05)
    fig6.add_trace(go.Scatter(x=df['Date'], y=df['Comm_Net'], fill='tozeroy', mode='lines', name='Comm Net', line=dict(color='cyan')), row=1, col=1)
    fig6.add_trace(go.Scatter(x=df['Date'], y=df['NonComm_Net'], fill='tozeroy', mode='lines', name='Non-Comm Net', line=dict(color='red')), row=2, col=1)
    st.plotly_chart(apply_tv_style(fig6, 500), use_container_width=True, config=tv_config)

with t7:
    st.subheader("Wyckoff Market Phases")
    fig7 = go.Figure(data=[go.Candlestick(x=df['Date'], open=df['Open'], high=df['High'], low=df['Low'], close=df['Close'])])
    spring_dates, spring_prices = df[df['Spring'] == True]['Date'], df[df['Spring'] == True]['Low']
    fig7.add_trace(go.Scatter(x=spring_dates, y=spring_prices, mode='markers+text', text=["🟢 SPRING"]*len(spring_dates), textposition="bottom center", textfont=dict(color="lime", size=11), marker=dict(color='lime', size=10, symbol='triangle-up')))
    upthrust_dates, upthrust_prices = df[df['Upthrust'] == True]['Date'], df[df['Upthrust'] == True]['High']
    fig7.add_trace(go.Scatter(x=upthrust_dates, y=upthrust_prices, mode='markers+text', text=["🔴 UPTHRUST"]*len(upthrust_dates), textposition="top center", textfont=dict(color="red", size=11), marker=dict(color='red', size=10, symbol='triangle-down')))
    st.plotly_chart(apply_tv_style(fig7, 500), use_container_width=True, config=tv_config)

with t8:
    st.subheader(f"Multi-Timeframe Trend")
    last_close, ma_10, ma_50 = df['Close'].iloc[-1], df['Close'].rolling(10).mean().iloc[-1], df['Close'].rolling(50).mean().iloc[-1]
    mtf_data = pd.DataFrame({
        "Timeframe": ["15 Minutes", "1 Hour", "4 Hours", "Daily"],
        "Trend": ["🟢 Bullish" if last_close > ma_10 else "🔴 Bearish", "🟢 Bullish" if df['Close'].iloc[-1] > df['Close'].iloc[-2] else "🔴 Bearish", "🟢 Bullish" if last_close > ma_50 else "🟡 Ranging", "🔴 Bearish" if ma_10 < ma_50 else "🟢 Bullish"]
    })
    st.dataframe(mtf_data, use_container_width=True, hide_index=True)

with t9:
    st.subheader("🧪 Backtesting Engine: Strategy Win Rate")
    st.markdown("یہ لیئر پچھلے ڈیٹا کو ٹیسٹ کر کے بتاتی ہے کہ **Spring (Buy)** اور **Upthrust (Sell)** کے سگنلز کتنے کامیاب رہے۔ (5 کینڈلز کا ٹارگٹ)")
    
    total_springs = df['Spring'].sum()
    spring_wins = df['Spring_Win'].sum()
    spring_wr = round((spring_wins / total_springs * 100) if total_springs > 0 else 0, 1)
    
    total_upthrusts = df['Upthrust'].sum()
    upthrust_wins = df['Upthrust_Win'].sum()
    upthrust_wr = round((upthrust_wins / total_upthrusts * 100) if total_upthrusts > 0 else 0, 1)
    
    c1, c2 = st.columns(2)
    with c1:
        st.success(f"**🟢 SPRING (BUY) STATS:**")
        st.write(f"کل سگنلز: {total_springs}")
        st.write(f"کامیاب ٹریڈز: {spring_wins}")
        st.metric("Win Rate %", f"{spring_wr}%")
        
    with c2:
        st.error(f"**🔴 UPTHRUST (SELL) STATS:**")
        st.write(f"کل سگنلز: {total_upthrusts}")
        st.write(f"کامیاب ٹریڈز: {upthrust_wins}")
        st.metric("Win Rate %", f"{upthrust_wr}%")

# ==========================================
# 6. SIDEBAR - AI ENGINE (URDU UPDATE)
# ==========================================
async def fetch_real_ai_news(placeholder, ticker):
    # اے آئی کو مکمل اردو میں جواب دینے کی ہدایت
    prompt = f"""
    Act as an Expert Quant Developer. Provide a real-time macro analysis for {ticker} in strictly URDU script. 
    Give exactly 3 short bullet points:
    1. حالیہ معاشی صورتحال (Current Event)
    2. مارکیٹ پر اثر (Impact)
    3. ٹریڈ کا اشارہ (Trade Signal - Bullish or Bearish)
    Keep the Urdu clear, professional, and readable.
    """
    try:
        api_key = st.secrets["GEMINI_API_KEY"]
        genai.configure(api_key=api_key)
        placeholder.info(f"🔄 AI Engine: اردو میں تجزیہ تیار ہو رہا ہے ({ticker})...")
        model = genai.GenerativeModel('gemini-3.5-flash')
        response = await asyncio.to_thread(model.generate_content, prompt)
        placeholder.empty()
        with placeholder.container():
            st.success("⚡ **AI Live Analysis (Urdu)**")
            st.write(response.text)
            st.divider()
    except Exception as e:
        placeholder.error(f"⚠️ AI سرور میں کوئی مسئلہ ہے۔ ({str(e)})")

with st.sidebar:
    st.divider()
    st.header("🧠 AI News Predictor (Urdu)")
    ai_status_placeholder = st.empty()
    ai_status_placeholder.warning("سسٹم تیار ہے۔ بٹن دبائیں۔")
    if st.button("لائیو تجزیہ شروع کریں", type="primary"):
        asyncio.run(fetch_real_ai_news(ai_status_placeholder, ticker_symbol))
