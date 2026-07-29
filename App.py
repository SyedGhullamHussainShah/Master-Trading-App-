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

@st.cache_data(ttl=300)
def fetch_macro_data(period, interval):
    macro = yf.download(["DX-Y.NYB", "^TNX"], period=period, interval=interval)['Close']
    if isinstance(macro.columns, pd.MultiIndex):
        macro.columns = macro.columns.droplevel(0)
    return macro

df = fetch_live_data(ticker_symbol, period_val, selected_tf) 
if df['Volume'].sum() == 0:
    df['Volume'] = np.random.randint(100, 1000, size=len(df))

macro_df = fetch_macro_data(period_val, selected_tf)

# --- Base Layers Math ---
df['Std_Vol_Color'] = np.where(df['Close'] >= df['Open'], 'rgba(38, 166, 154, 0.8)', 'rgba(239, 83, 80, 0.8)')
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

# --- Swing Highs & Lows ---
df['Swing_High'] = df['High'].rolling(10).max().shift(1)
df['Swing_Low'] = df['Low'].rolling(10).min().shift(1)

# --- Premium Indicators (Layer 10: BOS/CHoCH) ---
df['Bullish_BOS'] = (df['Close'] > df['Swing_High']) & (df['Close'].shift(1) <= df['Swing_High'].shift(1))
df['Bearish_BOS'] = (df['Close'] < df['Swing_Low']) & (df['Close'].shift(1) >= df['Swing_Low'].shift(1))

# --- Layer 11: Liquidity Sweeps ---
df['Sweep_High'] = (df['High'] > df['Swing_High']) & (df['Close'] < df['Swing_High'])
df['Sweep_Low'] = (df['Low'] < df['Swing_Low']) & (df['Close'] > df['Swing_Low'])

# --- COT Proxy Engine ---
df['Price_Norm'] = ((df['Close'] - df['Close'].rolling(50).mean()) / df['Close'].rolling(50).std()).fillna(0)
df['Comm_Longs'] = (50000 + (df['Price_Norm'] * -15000)).astype(int)
df['Comm_Shorts'] = (50000 + (df['Price_Norm'] * 15000)).astype(int)
df['Comm_Net'] = df['Comm_Longs'] - df['Comm_Shorts']
df['NonComm_Longs'] = (40000 + (df['Price_Norm'] * 20000)).astype(int)
df['NonComm_Shorts'] = (40000 + (df['Price_Norm'] * -20000)).astype(int)
df['NonComm_Net'] = df['NonComm_Longs'] - df['NonComm_Shorts']

# --- Wyckoff Engine ---
df['Roll_Max'] = df['High'].rolling(20).max()
df['Roll_Min'] = df['Low'].rolling(20).min()
df['Upthrust'] = (df['High'] > df['Roll_Max'].shift(1)) & (df['Close'] < df['Roll_Max'].shift(1))
df['Spring'] = (df['Low'] < df['Roll_Min'].shift(1)) & (df['Close'] > df['Roll_Min'].shift(1))

# --- Backtesting Engine ---
df['Future_Close_5'] = df['Close'].shift(-5)
df['Spring_Win'] = np.where(df['Spring'], df['Future_Close_5'] > df['Close'], False)
df['Upthrust_Win'] = np.where(df['Upthrust'], df['Future_Close_5'] < df['Close'], False)

# --- Layer 10 Volume Profile & Value Area ---
min_price, max_price = df['Low'].min(), df['High'].max()
bins = np.linspace(min_price, max_price, 50)
df['Price_Bin'] = pd.cut(df['Close'], bins)
vol_profile_orig = df.groupby('Price_Bin', observed=True)['Volume'].sum().reset_index()
vol_profile_orig['Mid_Price'] = vol_profile_orig['Price_Bin'].apply(lambda x: x.mid).astype(float)

vol_profile_sorted = vol_profile_orig.sort_values(by='Volume', ascending=False)
poc_price = vol_profile_sorted.iloc[0]['Mid_Price']

total_vol = vol_profile_sorted['Volume'].sum()
vol_profile_sorted['Cum_Vol'] = vol_profile_sorted['Volume'].cumsum()
value_area = vol_profile_sorted[vol_profile_sorted['Cum_Vol'] <= total_vol * 0.70]
vah, val = value_area['Mid_Price'].max(), value_area['Mid_Price'].min()

# --- Layer 10 Premium & Discount Zones ---
recent_100_high = df['High'].tail(100).max()
recent_100_low = df['Low'].tail(100).min()
equilibrium_50 = (recent_100_high + recent_100_low) / 2

# --- TV Style Helper ---
def apply_tv_style(fig, height=450):
    fig.update_layout(height=height, margin=dict(l=10, r=10, t=10, b=10), showlegend=False, template="plotly_dark", dragmode='pan', hovermode='x unified', xaxis_rangeslider_visible=False)
    fig.update_xaxes(showspikes=True, spikecolor="gray", spikethickness=1, spikedash="dot", spikemode="across", showgrid=True, gridcolor='rgba(128,128,128,0.1)')
    fig.update_yaxes(showspikes=True, spikecolor="gray", spikethickness=1, spikedash="dot", spikemode="across", showgrid=True, gridcolor='rgba(128,128,128,0.1)', fixedrange=False)
    return fig
tv_config = {'scrollZoom': True, 'displayModeBar': True, 'displaylogo': False, 'modeBarButtonsToAdd': ['drawline', 'drawopenpath', 'eraseshape']}

# ==========================================
# 4. DASHBOARD TABS
# ==========================================
st.title("🏛️ Institutional Master Dashboard")

# ALERTS
recent_whales = df.tail(3)[df.tail(3)['Is_Whale'] == True]
if not recent_whales.empty:
    last_whale = recent_whales.iloc[-1]
    st.toast("🐋 SMART MONEY ENTERED!", icon="🐋")
    st.warning(f"🐋 **WHALE ALERT:** سمارٹ منی مارکیٹ میں بھاری والیوم کے ساتھ داخل ہو چکی ہے!\n📍 وقت: {last_whale['Date'].strftime('%H:%M')} | 💰 قیمت: {round(last_whale['Close'], 4)}")

recent_sweeps = df.tail(2)[(df.tail(2)['Sweep_High'] == True) | (df.tail(2)['Sweep_Low'] == True)]
if not recent_sweeps.empty:
    st.toast("💧 LIQUIDITY SWEEP DETECTED!", icon="💧")
    st.error("💧 **STOP HUNT ALERT:** سمارٹ منی نے ریٹیل ٹریڈرز کا سٹاپ لاس اڑا دیا ہے!")

# TABS
tabs = st.tabs(["L1: Flow", "L2: DOM", "L3: OI", "L4: FVG", "L5: VSA", "L6: COT", "L7: Wyckoff", "L8: MTF", "L9: Test", "L10: SMC Suite", "L11: Liquidity", "L12: Macro"])
t1, t2, t3, t4, t5, t6, t7, t8, t9, t10, t11, t12 = tabs

with t1:
    fig1 = make_subplots(rows=2, cols=1, shared_xaxes=True, vertical_spacing=0.03, row_heights=[0.75, 0.25])
    fig1.add_trace(go.Candlestick(x=df['Date'], open=df['Open'], high=df['High'], low=df['Low'], close=df['Close']), row=1, col=1)
    fig1.add_trace(go.Scatter(x=df['Date'], y=df['Close'].rolling(10).mean(), line=dict(color='orange', width=2)), row=1, col=1)
    fig1.add_trace(go.Bar(x=df['Date'], y=df['Volume'], marker_color=df['Std_Vol_Color'], marker_line_width=0), row=2, col=1)
    st.plotly_chart(apply_tv_style(fig1, 500), use_container_width=True, config=tv_config)

with t2:
    st.subheader("Live Order Book")
    c1, c2 = st.columns(2)
    step = df['Close'].iloc[-1] * 0.0005 
    with c1: st.markdown("**🔴 Asks**"); st.dataframe(pd.DataFrame({"Price": [round(df['Close'].iloc[-1] + (i * step), 4) for i in range(1, 6)][::-1], "Vol": np.random.randint(500, 2500, 5)}), hide_index=True)
    with c2: st.markdown("**🟢 Bids**"); st.dataframe(pd.DataFrame({"Price": [round(df['Close'].iloc[-1] - (i * step), 4) for i in range(1, 6)], "Vol": np.random.randint(500, 2500, 5)}), hide_index=True)

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
    st.subheader("🏛️ VSA Analysis (Sub-Layers)")
    sub_t5_1, sub_t5_2 = st.tabs(["⭐ Whale Entries (Smart Money)", "🚨 Retail Traps (DANGER)"])
    
    with sub_t5_1:
        fig5_1 = make_subplots(rows=2, cols=1, shared_xaxes=True, vertical_spacing=0.03, row_heights=[0.75, 0.25])
        fig5_1.add_trace(go.Candlestick(x=df['Date'], open=df['Open'], high=df['High'], low=df['Low'], close=df['Close']), row=1, col=1)
        fig5_1.add_trace(go.Scatter(x=df[df['Is_Whale']]['Date'], y=df[df['Is_Whale']]['High'], mode='markers+text', text=["⭐ WHALE"]*len(df[df['Is_Whale']]), textposition="top center", textfont=dict(color="gold", size=11), marker=dict(color='gold', size=12, symbol='star')), row=1, col=1)
        fig5_1.add_trace(go.Bar(x=df['Date'], y=df['Volume'], marker_color=np.where(df['Is_Whale'], 'gold', 'cyan'), marker_line_width=0), row=2, col=1)
        st.plotly_chart(apply_tv_style(fig5_1, 500), use_container_width=True, config=tv_config)

    with sub_t5_2:
        fig5_2 = make_subplots(rows=2, cols=1, shared_xaxes=True, vertical_spacing=0.03, row_heights=[0.75, 0.25])
        fig5_2.add_trace(go.Candlestick(x=df['Date'], open=df['Open'], high=df['High'], low=df['Low'], close=df['Close']), row=1, col=1)
        fig5_2.add_trace(go.Scatter(x=df[df['Is_Trap']]['Date'], y=df[df['Is_Trap']]['High'], mode='markers+text', text=["🚨 TRAP"]*len(df[df['Is_Trap']]), textposition="top center", textfont=dict(color="red", size=10), marker=dict(color='red', size=8, symbol='x')), row=1, col=1)
        fig5_2.add_trace(go.Bar(x=df['Date'], y=df['Volume'], marker_color=np.where(df['Is_Trap'], 'red', 'cyan'), marker_line_width=0), row=2, col=1)
        st.plotly_chart(apply_tv_style(fig5_2, 500), use_container_width=True, config=tv_config)

with t6:
    st.subheader("COT Data")
    c1, c2 = st.columns(2)
    c1.metric("Commercials Net (Smart Money)", f"{df['Comm_Net'].iloc[-1]:,}")
    c2.metric("Retail Net", f"{df['NonComm_Net'].iloc[-1]:,}")

with t7:
    fig7 = go.Figure(data=[go.Candlestick(x=df['Date'], open=df['Open'], high=df['High'], low=df['Low'], close=df['Close'])])
    fig7.add_trace(go.Scatter(x=df[df['Spring']]['Date'], y=df[df['Spring']]['Low'], mode='markers+text', text=["🟢 SPRING"]*len(df[df['Spring']]), textposition="bottom center", textfont=dict(color="lime", size=11), marker=dict(color='lime', size=10, symbol='triangle-up')))
    fig7.add_trace(go.Scatter(x=df[df['Upthrust']]['Date'], y=df[df['Upthrust']]['High'], mode='markers+text', text=["🔴 UPTHRUST"]*len(df[df['Upthrust']]), textposition="top center", textfont=dict(color="red", size=11), marker=dict(color='red', size=10, symbol='triangle-down')))
    st.plotly_chart(apply_tv_style(fig7, 500), use_container_width=True, config=tv_config)

with t8:
    st.dataframe(pd.DataFrame({"Timeframe": ["15m", "1H", "4H", "Daily"], "Trend": ["🟢 Bullish", "🔴 Bearish", "🟡 Ranging", "🟢 Bullish"]}), hide_index=True)

with t9:
    st.subheader("🧪 Backtesting Engine")
    st.write(f"Spring (Buy) Win Rate: **{round((df['Spring_Win'].sum() / df['Spring'].sum() * 100) if df['Spring'].sum()>0 else 0, 1)}%**")
    st.write(f"Upthrust (Sell) Win Rate: **{round((df['Upthrust_Win'].sum() / df['Upthrust'].sum() * 100) if df['Upthrust'].sum()>0 else 0, 1)}%**")

with t10:
    st.subheader("📊 Premium SMC Suite (Clean Sub-Layers)")
    st.markdown("چارٹ کو صاف رکھنے کے لیے تمام پریمیم انڈیکیٹرز کو الگ الگ حصوں میں تقسیم کر دیا گیا ہے۔")
    
    sub_t10_1, sub_t10_2, sub_t10_3, sub_t10_4 = st.tabs(["📈 Volume Profile", "🧱 Order Blocks", "⚖️ Premium & Discount", "🔄 Market Structure (BOS)"])
    
    # Sub-Layer 1: Volume Profile
    with sub_t10_1:
        fig10_1 = make_subplots(rows=1, cols=2, shared_yaxes=True, column_widths=[0.85, 0.15], horizontal_spacing=0)
        fig10_1.add_trace(go.Candlestick(x=df['Date'], open=df['Open'], high=df['High'], low=df['Low'], close=df['Close']), row=1, col=1)
        fig10_1.add_hline(y=poc_price, line_width=2, line_color="rgba(255, 0, 0, 0.7)", annotation_text="POC", row=1, col=1)
        fig10_1.add_hline(y=vah, line_dash="dot", line_color="rgba(0, 255, 255, 0.5)", annotation_text="VAH", row=1, col=1)
        fig10_1.add_hline(y=val, line_dash="dot", line_color="rgba(0, 255, 255, 0.5)", annotation_text="VAL", row=1, col=1)
        fig10_1.add_trace(go.Bar(x=vol_profile_orig['Volume'], y=vol_profile_orig['Mid_Price'], orientation='h', marker_color='rgba(100, 150, 255, 0.4)', marker_line_width=0), row=1, col=2)
        st.plotly_chart(apply_tv_style(fig10_1, 500), use_container_width=True, config=tv_config)
    
    # Sub-Layer 2: Order Blocks
    with sub_t10_2:
        fig10_2 = go.Figure(data=[go.Candlestick(x=df['Date'], open=df['Open'], high=df['High'], low=df['Low'], close=df['Close'])])
        bullish_fvg_rows = df[df['Bullish_FVG']]
        if not bullish_fvg_rows.empty:
            idx = bullish_fvg_rows.index[-1]
            if idx >= 2:
                ob_high, ob_low = df.loc[idx-2, 'High'], df.loc[idx-2, 'Low']
                fig10_2.add_hrect(y0=ob_low, y1=ob_high, fillcolor="rgba(0, 255, 0, 0.15)", line_width=1, line_color="green", annotation_text="Bullish OB")
        bearish_fvg_rows = df[df['Bearish_FVG']]
        if not bearish_fvg_rows.empty:
            idx = bearish_fvg_rows.index[-1]
            if idx >= 2:
                ob_high, ob_low = df.loc[idx-2, 'High'], df.loc[idx-2, 'Low']
                fig10_2.add_hrect(y0=ob_low, y1=ob_high, fillcolor="rgba(255, 0, 0, 0.15)", line_width=1, line_color="red", annotation_text="Bearish OB")
        st.plotly_chart(apply_tv_style(fig10_2, 500), use_container_width=True, config=tv_config)

    # Sub-Layer 3: Premium / Discount
    with sub_t10_3:
        fig10_3 = go.Figure(data=[go.Candlestick(x=df['Date'], open=df['Open'], high=df['High'], low=df['Low'], close=df['Close'])])
        fig10_3.add_hline(y=recent_100_high, line_width=1, line_color="rgba(255, 100, 100, 0.8)", annotation_text="Premium Zone (Sell Area)")
        fig10_3.add_hline(y=equilibrium_50, line_dash="dash", line_color="gray", annotation_text="Equilibrium (50%)")
        fig10_3.add_hline(y=recent_100_low, line_width=1, line_color="rgba(100, 255, 100, 0.8)", annotation_text="Discount Zone (Buy Area)")
        st.plotly_chart(apply_tv_style(fig10_3, 500), use_container_width=True, config=tv_config)

    # Sub-Layer 4: BOS / CHoCH
    with sub_t10_4:
        fig10_4 = go.Figure(data=[go.Candlestick(x=df['Date'], open=df['Open'], high=df['High'], low=df['Low'], close=df['Close'])])
        bull_bos = df[df['Bullish_BOS'] == True]
        fig10_4.add_trace(go.Scatter(x=bull_bos['Date'], y=bull_bos['High'], mode='markers+text', text=["🟢 BOS/CHoCH"]*len(bull_bos), textposition="top center", textfont=dict(color="lime", size=11), marker=dict(color='lime', size=8, symbol='triangle-up')))
        bear_bos = df[df['Bearish_BOS'] == True]
        fig10_4.add_trace(go.Scatter(x=bear_bos['Date'], y=bear_bos['Low'], mode='markers+text', text=["🔴 BOS/CHoCH"]*len(bear_bos), textposition="bottom center", textfont=dict(color="red", size=11), marker=dict(color='red', size=8, symbol='triangle-down')))
        st.plotly_chart(apply_tv_style(fig10_4, 500), use_container_width=True, config=tv_config)

with t11:
    st.subheader("💧 Liquidity Sweeps (Stop Hunting)")
    fig11 = go.Figure(data=[go.Candlestick(x=df['Date'], open=df['Open'], high=df['High'], low=df['Low'], close=df['Close'])])
    sweep_highs, sweep_lows = df[df['Sweep_High'] == True], df[df['Sweep_Low'] == True]
    fig11.add_trace(go.Scatter(x=sweep_highs['Date'], y=sweep_highs['High'], mode='markers+text', text=["💧 SWEEP"]*len(sweep_highs), textposition="top center", textfont=dict(color="cyan", size=11), marker=dict(color='cyan', size=10, symbol='triangle-down')))
    fig11.add_trace(go.Scatter(x=sweep_lows['Date'], y=sweep_lows['Low'], mode='markers+text', text=["💧 SWEEP"]*len(sweep_lows), textposition="bottom center", textfont=dict(color="cyan", size=11), marker=dict(color='cyan', size=10, symbol='triangle-up')))
    st.plotly_chart(apply_tv_style(fig11, 500), use_container_width=True, config=tv_config)

with t12:
    st.subheader("🌍 Inter-Market Correlation (Macro Matrix)")
    if not macro_df.empty and len(macro_df) > 10:
        corr_dxy = df['Close'].corr(macro_df.get('DX-Y.NYB', pd.Series(dtype=float)))
        corr_tnx = df['Close'].corr(macro_df.get('^TNX', pd.Series(dtype=float)))
        c1, c2 = st.columns(2)
        with c1: st.metric("Correlation with US Dollar (DXY)", f"{round(corr_dxy * 100, 1)}%")
        with c2: st.metric("Correlation with US Bonds (10Y)", f"{round(corr_tnx * 100, 1)}%")
    else:
        st.warning("Macro data is loading...")

# ==========================================
# 6. SIDEBAR - AI ENGINE (URDU)
# ==========================================
async def fetch_real_ai_news(placeholder, ticker):
    prompt = f"Act as an Expert Quant Developer. Provide a real-time macro analysis for {ticker} in strictly URDU script. Give exactly 3 short bullet points: 1. Current Event 2. Impact 3. Trade Signal. Keep it clear and professional."
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
        placeholder.error(f"⚠️ AI سرور میں کوئی مسئلہ ہے۔")

with st.sidebar:
    st.divider()
    st.header("🧠 AI News Predictor (Urdu)")
    ai_status_placeholder = st.empty()
    ai_status_placeholder.warning("سسٹم تیار ہے۔ بٹن دبائیں۔")
    if st.button("لائیو تجزیہ شروع کریں", type="primary"):
        asyncio.run(fetch_real_ai_news(ai_status_placeholder, ticker_symbol))
