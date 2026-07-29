import streamlit as st
import pandas as pd
import numpy as np
import plotly.graph_objects as go
from plotly.subplots import make_subplots
import asyncio
import yfinance as yf
import google.generativeai as genai

# ==========================================
# 1. PAGE CONFIGURATION & CUSTOM CSS 
# ==========================================
st.set_page_config(
    page_title="Institutional Master Dashboard",
    page_icon="🏛️",
    layout="wide",
    initial_sidebar_state="expanded"
)

st.markdown("""
    <style>
    .block-container { padding-top: 1rem !important; padding-bottom: 1rem !important; }
    header {visibility: hidden;}
    footer {visibility: hidden;}
    [data-testid="stSidebar"] { min-width: 250px !important; max-width: 250px !important; width: 250px !important; }
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
# 3. LIVE MARKET DATA (100% REAL FETCH)
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

@st.cache_data(ttl=3600)
def fetch_macro_correlation(ticker):
    try:
        macro_df = yf.download([ticker, "DX-Y.NYB", "^TNX"], period="3mo", interval="1d")
        if isinstance(macro_df.columns, pd.MultiIndex):
            closes = macro_df['Close'].dropna()
        else:
            return None, None
        if len(closes) > 10:
            corr_dxy = closes[ticker].corr(closes['DX-Y.NYB'])
            corr_tnx = closes[ticker].corr(closes['^TNX'])
            return corr_dxy, corr_tnx
        return None, None
    except:
        return None, None

df = fetch_live_data(ticker_symbol, period_val, selected_tf) 

# (No fake volume fallback used here. 100% real tick volume from Yahoo Finance)

# ==========================================
# 4. MATH ENGINES (BASED ON REAL PRICE ACTION)
# ==========================================
# --- CVD (Cumulative Volume Delta) - The Real Order Flow Tool ---
df['Tick_Dir'] = np.where(df['Close'] >= df['Close'].shift(1), 1, -1)
df['Buy_Vol'] = np.where(df['Tick_Dir'] > 0, df['Volume'], 0)
df['Sell_Vol'] = np.where(df['Tick_Dir'] < 0, df['Volume'], 0)
df['CVD'] = (df['Buy_Vol'] - df['Sell_Vol']).cumsum()

# --- VSA (Whales & Traps) ---
df['Vol_MA'] = df['Volume'].rolling(20).mean().fillna(0)
df['Body'] = abs(df['Close'] - df['Open'])
df['Avg_Body'] = df['Body'].rolling(20).mean().fillna(0)
df['Is_Trap'] = (df['Volume'] > (df['Vol_MA'] * 1.5)) & (df['Body'] < df['Avg_Body'])
df['Is_Whale'] = df['Volume'] > (df['Vol_MA'] * 2.5)

# --- SMC & Liquidity Sweeps ---
df['Bullish_FVG'] = (df['Low'] > df['High'].shift(2))
df['Bearish_FVG'] = (df['High'] < df['Low'].shift(2))
df['Swing_High'] = df['High'].rolling(10).max().shift(1)
df['Swing_Low'] = df['Low'].rolling(10).min().shift(1)
df['Sweep_High'] = (df['High'] > df['Swing_High']) & (df['Close'] < df['Swing_High'])
df['Sweep_Low'] = (df['Low'] < df['Swing_Low']) & (df['Close'] > df['Swing_Low'])
df['Bullish_BOS'] = (df['Close'] > df['Swing_High']) & (df['Close'].shift(1) <= df['Swing_High'].shift(1))
df['Bearish_BOS'] = (df['Close'] < df['Swing_Low']) & (df['Close'].shift(1) >= df['Swing_Low'].shift(1))

# --- Wyckoff Engine ---
df['Roll_Max'] = df['High'].rolling(20).max()
df['Roll_Min'] = df['Low'].rolling(20).min()
df['Upthrust'] = (df['High'] > df['Roll_Max'].shift(1)) & (df['Close'] < df['Roll_Max'].shift(1))
df['Spring'] = (df['Low'] < df['Roll_Min'].shift(1)) & (df['Close'] > df['Roll_Min'].shift(1))

# --- Backtesting Engine ---
df['Future_Close_5'] = df['Close'].shift(-5)
df['Spring_Win'] = np.where(df['Spring'], df['Future_Close_5'] > df['Close'], False)
df['Upthrust_Win'] = np.where(df['Upthrust'], df['Future_Close_5'] < df['Close'], False)

# --- Volume Profile (Real POC, VAH, VAL) ---
if df['Volume'].sum() > 0:
    min_price, max_price = df['Low'].min(), df['High'].max()
    bins = np.linspace(min_price, max_price, 50)
    df['Price_Bin'] = pd.cut(df['Close'], bins)
    vol_profile = df.groupby('Price_Bin', observed=True)['Volume'].sum().reset_index()
    vol_profile['Mid_Price'] = vol_profile['Price_Bin'].apply(lambda x: x.mid).astype(float)
    vol_profile_sorted = vol_profile.sort_values(by='Volume', ascending=False)
    poc_price = vol_profile_sorted.iloc[0]['Mid_Price']
    
    total_vol = vol_profile_sorted['Volume'].sum()
    vol_profile_sorted['Cum_Vol'] = vol_profile_sorted['Volume'].cumsum()
    value_area = vol_profile_sorted[vol_profile_sorted['Cum_Vol'] <= total_vol * 0.70]
    vah = value_area['Mid_Price'].max()
    val = value_area['Mid_Price'].min()
else:
    poc_price, vah, val, vol_profile = df['Close'].iloc[-1], df['Close'].iloc[-1], df['Close'].iloc[-1], pd.DataFrame()

# ==========================================
# TV STYLE HELPER
# ==========================================
def apply_tv_style(fig, height=500):
    fig.update_layout(height=height, margin=dict(l=10, r=10, t=10, b=10), showlegend=False, template="plotly_dark", dragmode='pan', hovermode='x unified', xaxis_rangeslider_visible=False)
    fig.update_xaxes(showspikes=True, spikecolor="gray", spikethickness=1, spikedash="dot", spikemode="across", showgrid=True, gridcolor='rgba(128,128,128,0.1)')
    fig.update_yaxes(showspikes=True, spikecolor="gray", spikethickness=1, spikedash="dot", spikemode="across", showgrid=True, gridcolor='rgba(128,128,128,0.1)', fixedrange=False)
    return fig
tv_config = {'scrollZoom': True, 'displayModeBar': True, 'displaylogo': False, 'modeBarButtonsToAdd': ['drawline', 'drawopenpath', 'eraseshape']}

# ==========================================
# 5. PROFESSIONAL DASHBOARD TABS
# ==========================================
st.title("🏛️ Professional Quant Terminal (100% Real Data)")

# TABS (Clean and Focused)
tabs = st.tabs(["📊 L1: Price & CVD", "🏛️ L2: Premium SMC & Profile", "💧 L3: Liquidity & BOS", "🐋 L4: VSA (Whales/Traps)", "🕵️ L5: Wyckoff", "🌍 L6: Macro Matrix", "🧪 L7: Real Backtest"])
t1, t2, t3, t4, t5, t6, t7 = tabs

# --- T1: PRICE & CVD (Real Order Flow) ---
with t1:
    st.subheader("Price & Cumulative Volume Delta (CVD)")
    st.markdown("CVD بتاتا ہے کہ حقیقی والیوم بائرز (Buyers) کی طرف ہے یا سیلرز (Sellers) کی طرف۔ (یہ 100% ریل ڈیٹا پر مبنی ہے)")
    fig1 = make_subplots(rows=2, cols=1, shared_xaxes=True, vertical_spacing=0.05, row_heights=[0.7, 0.3])
    fig1.add_trace(go.Candlestick(x=df['Date'], open=df['Open'], high=df['High'], low=df['Low'], close=df['Close']), row=1, col=1)
    
    # Real CVD Plot
    fig1.add_trace(go.Scatter(x=df['Date'], y=df['CVD'], mode='lines', fill='tozeroy', name='CVD', line=dict(color='cyan', width=2)), row=2, col=1)
    st.plotly_chart(apply_tv_style(fig1, 600), use_container_width=True, config=tv_config)

# --- T2: PREMIUM SMC & VOLUME PROFILE ---
with t2:
    st.subheader("Volume Profile & Real Order Blocks")
    if not vol_profile.empty:
        fig2 = make_subplots(rows=1, cols=2, shared_yaxes=True, column_widths=[0.85, 0.15], horizontal_spacing=0)
        fig2.add_trace(go.Candlestick(x=df['Date'], open=df['Open'], high=df['High'], low=df['Low'], close=df['Close']), row=1, col=1)
        
        # Profile Lines
        fig2.add_hline(y=poc_price, line_width=2, line_color="rgba(255, 0, 0, 0.7)", annotation_text="POC", row=1, col=1)
        fig2.add_hline(y=vah, line_dash="dot", line_color="rgba(0, 255, 255, 0.5)", annotation_text="VAH", row=1, col=1)
        fig2.add_hline(y=val, line_dash="dot", line_color="rgba(0, 255, 255, 0.5)", annotation_text="VAL", row=1, col=1)
        
        # Order Blocks (FVG Based)
        if not df[df['Bullish_FVG']].empty and df[df['Bullish_FVG']].index[-1] >= 2:
            ob_high, ob_low = df.loc[df[df['Bullish_FVG']].index[-1]-2, 'High'], df.loc[df[df['Bullish_FVG']].index[-1]-2, 'Low']
            fig2.add_hrect(y0=ob_low, y1=ob_high, fillcolor="rgba(0, 255, 0, 0.15)", line_width=1, line_color="green", annotation_text="Bullish OB", row=1, col=1)
        if not df[df['Bearish_FVG']].empty and df[df['Bearish_FVG']].index[-1] >= 2:
            ob_high, ob_low = df.loc[df[df['Bearish_FVG']].index[-1]-2, 'High'], df.loc[df[df['Bearish_FVG']].index[-1]-2, 'Low']
            fig2.add_hrect(y0=ob_low, y1=ob_high, fillcolor="rgba(255, 0, 0, 0.15)", line_width=1, line_color="red", annotation_text="Bearish OB", row=1, col=1)
            
        fig2.add_trace(go.Bar(x=vol_profile['Volume'], y=vol_profile['Mid_Price'], orientation='h', marker_color='rgba(100, 150, 255, 0.4)', marker_line_width=0), row=1, col=2)
        st.plotly_chart(apply_tv_style(fig2, 600), use_container_width=True, config=tv_config)
    else:
        st.warning("Volume data is not available for this asset on Yahoo Finance to calculate Profile.")

# --- T3: LIQUIDITY SWEEPS & BOS ---
with t3:
    st.subheader("Liquidity Sweeps & Break of Structure")
    fig3 = go.Figure(data=[go.Candlestick(x=df['Date'], open=df['Open'], high=df['High'], low=df['Low'], close=df['Close'])])
    
    # BOS markers
    fig3.add_trace(go.Scatter(x=df[df['Bullish_BOS']]['Date'], y=df[df['Bullish_BOS']]['High'], mode='markers+text', text=["🟢 BOS"]*len(df[df['Bullish_BOS']]), textposition="top center", textfont=dict(color="lime", size=11), marker=dict(color='lime', size=8, symbol='triangle-up')))
    fig3.add_trace(go.Scatter(x=df[df['Bearish_BOS']]['Date'], y=df[df['Bearish_BOS']]['Low'], mode='markers+text', text=["🔴 BOS"]*len(df[df['Bearish_BOS']]), textposition="bottom center", textfont=dict(color="red", size=11), marker=dict(color='red', size=8, symbol='triangle-down')))
    
    # Sweeps markers
    fig3.add_trace(go.Scatter(x=df[df['Sweep_High']]['Date'], y=df[df['Sweep_High']]['High'], mode='markers+text', text=["💧 SWEEP"]*len(df[df['Sweep_High']]), textposition="top center", textfont=dict(color="cyan", size=11), marker=dict(color='cyan', size=10, symbol='triangle-down')))
    fig3.add_trace(go.Scatter(x=df[df['Sweep_Low']]['Date'], y=df[df['Sweep_Low']]['Low'], mode='markers+text', text=["💧 SWEEP"]*len(df[df['Sweep_Low']]), textposition="bottom center", textfont=dict(color="cyan", size=11), marker=dict(color='cyan', size=10, symbol='triangle-up')))
    
    st.plotly_chart(apply_tv_style(fig3, 500), use_container_width=True, config=tv_config)

# --- T4: VSA ---
with t4:
    st.subheader("VSA (Whales & Traps)")
    vsa_view = st.radio("Select View:", ["⭐ Whales", "🚨 Traps"], horizontal=True, label_visibility="collapsed")
    fig4 = make_subplots(rows=2, cols=1, shared_xaxes=True, vertical_spacing=0.03, row_heights=[0.75, 0.25])
    fig4.add_trace(go.Candlestick(x=df['Date'], open=df['Open'], high=df['High'], low=df['Low'], close=df['Close']), row=1, col=1)
    
    if vsa_view == "⭐ Whales":
        fig4.add_trace(go.Scatter(x=df[df['Is_Whale']]['Date'], y=df[df['Is_Whale']]['High'], mode='markers+text', text=["⭐ WHALE"]*len(df[df['Is_Whale']]), textposition="top center", textfont=dict(color="gold", size=11), marker=dict(color='gold', size=12, symbol='star')), row=1, col=1)
        fig4.add_trace(go.Bar(x=df['Date'], y=df['Volume'], marker_color=np.where(df['Is_Whale'], 'gold', 'cyan'), marker_line_width=0), row=2, col=1)
    else:
        fig4.add_trace(go.Scatter(x=df[df['Is_Trap']]['Date'], y=df[df['Is_Trap']]['High'], mode='markers+text', text=["🚨 TRAP"]*len(df[df['Is_Trap']]), textposition="top center", textfont=dict(color="red", size=10), marker=dict(color='red', size=8, symbol='x')), row=1, col=1)
        fig4.add_trace(go.Bar(x=df['Date'], y=df['Volume'], marker_color=np.where(df['Is_Trap'], 'red', 'cyan'), marker_line_width=0), row=2, col=1)
    st.plotly_chart(apply_tv_style(fig4, 500), use_container_width=True, config=tv_config)

# --- T5: WYCKOFF ---
with t5:
    st.subheader("Wyckoff Market Phases")
    fig5 = go.Figure(data=[go.Candlestick(x=df['Date'], open=df['Open'], high=df['High'], low=df['Low'], close=df['Close'])])
    fig5.add_trace(go.Scatter(x=df[df['Spring']]['Date'], y=df[df['Spring']]['Low'], mode='markers+text', text=["🟢 SPRING"]*len(df[df['Spring']]), textposition="bottom center", textfont=dict(color="lime", size=11), marker=dict(color='lime', size=10, symbol='triangle-up')))
    fig5.add_trace(go.Scatter(x=df[df['Upthrust']]['Date'], y=df[df['Upthrust']]['High'], mode='markers+text', text=["🔴 UPTHRUST"]*len(df[df['Upthrust']]), textposition="top center", textfont=dict(color="red", size=11), marker=dict(color='red', size=10, symbol='triangle-down')))
    st.plotly_chart(apply_tv_style(fig5, 500), use_container_width=True, config=tv_config)

# --- T6: MACRO ---
with t6:
    st.subheader("🌍 Real Macro Correlation Matrix")
    corr_dxy, corr_tnx = fetch_macro_correlation(ticker_symbol)
    if corr_dxy is not None:
        c1, c2 = st.columns(2)
        c1.metric("Correlation (US Dollar - DXY)", f"{round(corr_dxy * 100, 1)}%")
        c2.metric("Correlation (US 10Y Bonds)", f"{round(corr_tnx * 100, 1)}%")
    else:
        st.warning("Data fetch error or insufficient daily data for Correlation.")

# --- T7: BACKTEST ---
with t7:
    st.subheader("🧪 Real Backtesting Statistics (5-Candle Projection)")
    st.write(f"Spring (Buy) Win Rate: **{round((df['Spring_Win'].sum() / df['Spring'].sum() * 100) if df['Spring'].sum()>0 else 0, 1)}%**")
    st.write(f"Upthrust (Sell) Win Rate: **{round((df['Upthrust_Win'].sum() / df['Upthrust'].sum() * 100) if df['Upthrust'].sum()>0 else 0, 1)}%**")

# ==========================================
# 6. SIDEBAR - AI ENGINE (URDU)
# ==========================================
async def fetch_real_ai_news(placeholder, ticker):
    prompt = f"Act as an Expert Quant Developer. Provide a real-time macro analysis for {ticker} in strictly URDU script. Give exactly 3 short bullet points: 1. Current Event 2. Impact 3. Trade Signal."
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
        placeholder.error(f"⚠️ AI سرور میں مسئلہ ہے۔")

with st.sidebar:
    st.divider()
    st.header("🧠 AI News Predictor")
    ai_status_placeholder = st.empty()
    ai_status_placeholder.warning("سسٹم تیار ہے۔ بٹن دبائیں۔")
    if st.button("لائیو تجزیہ شروع کریں", type="primary"):
        asyncio.run(fetch_real_ai_news(ai_status_placeholder, ticker_symbol))
