import streamlit as st
import pandas as pd
import numpy as np
import plotly.graph_objects as go
from plotly.subplots import make_subplots
import asyncio
import yfinance as yf
import google.generativeai as genai
import requests

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
    [data-testid="stSidebar"] { min-width: 260px !important; max-width: 260px !important; width: 260px !important; }
    </style>
""", unsafe_allow_html=True)

# ==========================================
# 2. SIDEBAR - REAL API CONFIGURATION
# ==========================================
with st.sidebar:
    st.header("⚙️ Market Settings")
    ticker_symbol = st.selectbox("Select Asset:", ["GC=F", "EURUSD=X", "GBPUSD=X", "JPY=X"])
    tf_options = {"5m": "5d", "15m": "7d", "1h": "1mo", "1d": "1y"}
    selected_tf = st.selectbox("Select Timeframe:", list(tf_options.keys()), index=2)
    period_val = tf_options[selected_tf]
    
    st.divider()
    st.header("🔑 Real Data APIs")
    st.markdown("Oanda API required for real Order Book & Sentiment.")
    oanda_api_key = st.text_input("Oanda V20 API Key (Bearer):", type="password")
    oanda_env = st.selectbox("Oanda Environment:", ["practice", "live"])
    
def get_oanda_ticker(yf_ticker):
    mapper = {"EURUSD=X": "EUR_USD", "GBPUSD=X": "GBP_USD", "JPY=X": "USD_JPY", "GC=F": "XAU_USD"}
    return mapper.get(yf_ticker, None)

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

@st.cache_data(ttl=300)
def fetch_oanda_order_book(api_key, env, instrument):
    if not api_key or not instrument: return None, None
    base_url = f"https://api-fx{env}.oanda.com/v3/instruments/{instrument}"
    headers = {"Authorization": f"Bearer {api_key}"}
    try:
        ob_res = requests.get(f"{base_url}/orderBook", headers=headers).json()
        pb_res = requests.get(f"{base_url}/positionBook", headers=headers).json()
        return ob_res.get('orderBook', {}), pb_res.get('positionBook', {})
    except:
        return None, None

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

# --- REAL CFTC COT DATA FETCH ---
@st.cache_data(ttl=86400) 
def fetch_cftc_cot(ticker):
    cftc_map = {
        "GC=F": "GOLD - COMMODITY EXCHANGE INC.",
        "EURUSD=X": "EURO FX - CHICAGO MERCANTILE EXCHANGE",
        "GBPUSD=X": "BRITISH POUND - CHICAGO MERCANTILE EXCHANGE",
        "JPY=X": "JAPANESE YEN - CHICAGO MERCANTILE EXCHANGE"
    }
    market_name = cftc_map.get(ticker, "GOLD - COMMODITY EXCHANGE INC.")
    url = f"https://publicreporting.cftc.gov/resource/6dca-ht3v.json?market_and_exchange_names={market_name}&$limit=100&$order=report_date_as_yyyy_mm_dd DESC"
    try:
        res = requests.get(url)
        data = res.json()
        df_cot = pd.DataFrame(data)
        if not df_cot.empty:
            df_cot['report_date_as_yyyy_mm_dd'] = pd.to_datetime(df_cot['report_date_as_yyyy_mm_dd'])
            # Sort Ascending for correct graph drawing (left to right)
            df_cot = df_cot.sort_values('report_date_as_yyyy_mm_dd')
            
            cols_to_convert = [
                'comm_positions_long_all', 'comm_positions_short_all', 
                'noncomm_positions_long_all', 'noncomm_positions_short_all',
                'nonrept_positions_long_all', 'nonrept_positions_short_all', 'open_interest_all'
            ]
            for col in cols_to_convert:
                if col in df_cot.columns:
                    df_cot[col] = pd.to_numeric(df_cot[col], errors='coerce').fillna(0)
            
            df_cot['Comm_Net'] = df_cot['comm_positions_long_all'] - df_cot['comm_positions_short_all']
            df_cot['NonComm_Net'] = df_cot['noncomm_positions_long_all'] - df_cot['noncomm_positions_short_all']
            df_cot['SmallSpec_Net'] = df_cot['nonrept_positions_long_all'] - df_cot['nonrept_positions_short_all']
            
            return df_cot
    except Exception as e:
        pass
    return pd.DataFrame()

df = fetch_live_data(ticker_symbol, period_val, selected_tf) 
cot_df = fetch_cftc_cot(ticker_symbol)

# ==========================================
# 4. MATH ENGINES (REAL PRICE & VOLUME ONLY)
# ==========================================
df['Tick_Dir'] = np.where(df['Close'] >= df['Close'].shift(1), 1, -1)
df['Buy_Vol'] = np.where(df['Tick_Dir'] > 0, df['Volume'], 0)
df['Sell_Vol'] = np.where(df['Tick_Dir'] < 0, df['Volume'], 0)
df['CVD'] = (df['Buy_Vol'] - df['Sell_Vol']).cumsum()
df['Std_Vol_Color'] = np.where(df['Close'] >= df['Open'], 'rgba(38, 166, 154, 0.8)', 'rgba(239, 83, 80, 0.8)')

df['Bullish_FVG'] = (df['Low'] > df['High'].shift(2))
df['Bearish_FVG'] = (df['High'] < df['Low'].shift(2))
df['Swing_High'] = df['High'].rolling(10).max().shift(1)
df['Swing_Low'] = df['Low'].rolling(10).min().shift(1)
df['Sweep_High'] = (df['High'] > df['Swing_High']) & (df['Close'] < df['Swing_High'])
df['Sweep_Low'] = (df['Low'] < df['Swing_Low']) & (df['Close'] > df['Swing_Low'])
df['Bullish_BOS'] = (df['Close'] > df['Swing_High']) & (df['Close'].shift(1) <= df['Swing_High'].shift(1))
df['Bearish_BOS'] = (df['Close'] < df['Swing_Low']) & (df['Close'].shift(1) >= df['Swing_Low'].shift(1))

# TV STYLE HELPER
def apply_tv_style(fig, height=550):
    fig.update_layout(height=height, margin=dict(l=10, r=10, t=10, b=10), showlegend=False, template="plotly_dark", dragmode='pan', hovermode='x unified', xaxis_rangeslider_visible=False)
    fig.update_xaxes(showspikes=True, spikecolor="gray", spikethickness=1, spikedash="dot", spikemode="across", showgrid=True, gridcolor='rgba(128,128,128,0.1)')
    fig.update_yaxes(showspikes=True, spikecolor="gray", spikethickness=1, spikedash="dot", spikemode="across", showgrid=True, gridcolor='rgba(128,128,128,0.1)', fixedrange=False)
    return fig
tv_config = {'scrollZoom': True, 'displayModeBar': True, 'displaylogo': False}

# ==========================================
# 5. PROFESSIONAL DASHBOARD TABS
# ==========================================
st.title("🏛️ Institutional Quant Terminal (100% Real Data)")

tabs = st.tabs(["📊 L1: Price & CVD", "📉 L2: Oanda Book", "🏦 L3: COT Report", "📈 L4: Open Interest", "🏛️ L5: SMC & Macro"])
t1, t2, t3, t4, t5 = tabs

# --- T1: PRICE & CVD ---
with t1:
    fig1 = make_subplots(rows=2, cols=1, shared_xaxes=True, vertical_spacing=0.05, row_heights=[0.7, 0.3])
    fig1.add_trace(go.Candlestick(x=df['Date'], open=df['Open'], high=df['High'], low=df['Low'], close=df['Close']), row=1, col=1)
    fig1.add_trace(go.Scatter(x=df['Date'], y=df['CVD'], mode='lines', fill='tozeroy', name='CVD', line=dict(color='cyan', width=2)), row=2, col=1)
    st.plotly_chart(apply_tv_style(fig1, 600), use_container_width=True, config=tv_config)

# --- T2: OANDA 4-QUADRANT BOOK ---
with t2:
    oanda_ticker = get_oanda_ticker(ticker_symbol)
    ob_data, pb_data = fetch_oanda_order_book(oanda_api_key, oanda_env, oanda_ticker)
    if ob_data and pb_data:
        current_price = float(ob_data.get('price', 0))
        ob_buckets = ob_data.get('buckets', [])
        pb_buckets = pb_data.get('buckets', [])
        prices_ob = [float(b['price']) for b in ob_buckets]
        long_ob = [float(b['longCountPercent']) for b in ob_buckets]
        short_ob = [-float(b['shortCountPercent']) for b in ob_buckets]
        prices_pb = [float(b['price']) for b in pb_buckets]
        long_pb = [float(b['longCountPercent']) for b in pb_buckets]
        short_pb = [-float(b['shortCountPercent']) for b in pb_buckets]

        fig2 = make_subplots(rows=1, cols=2, shared_yaxes=True, horizontal_spacing=0, subplot_titles=("Open Orders", "Open Positions"))
        fig2.add_trace(go.Bar(y=prices_ob, x=short_ob, orientation='h', marker_color='rgba(239, 83, 80, 0.8)'), row=1, col=1)
        fig2.add_trace(go.Bar(y=prices_ob, x=long_ob, orientation='h', marker_color='rgba(38, 166, 154, 0.8)'), row=1, col=1)
        fig2.add_trace(go.Bar(y=prices_pb, x=short_pb, orientation='h', marker_color='rgba(239, 83, 80, 1.0)'), row=1, col=2)
        fig2.add_trace(go.Bar(y=prices_pb, x=long_pb, orientation='h', marker_color='rgba(38, 166, 154, 1.0)'), row=1, col=2)
        
        fig2.add_hline(y=current_price, line_dash="solid", line_color="white", row=1, col=1)
        fig2.add_hline(y=current_price, line_dash="solid", line_color="white", row=1, col=2)
        fig2.update_layout(barmode='relative', height=600, margin=dict(l=10, r=10, t=40, b=10), template="plotly_dark", showlegend=False)
        st.plotly_chart(fig2, use_container_width=True, config={'displayModeBar': False})
    else:
        st.error("⚠️ Oanda API Key is missing. Enter your API Key in the sidebar.")

# --- T3: COT REPORT (Advanced Net Position Graph) ---
with t3:
    st.subheader("🏦 L3: Real CFTC Commitment of Traders (COT)")
    
    if not cot_df.empty:
        last = cot_df.iloc[-1]
        prev = cot_df.iloc[-2]
        
        st.markdown(f"**Report Date:** {last['report_date_as_yyyy_mm_dd'].strftime('%Y-%m-%d')} | **Market:** {last['market_and_exchange_names']}")
        
        c1, c2, c3, c4 = st.columns(4)
        c1.metric("Large Specs (Non-Comm) Net", f"{int(last['NonComm_Net']):,}", f"{int(last['NonComm_Net'] - prev['NonComm_Net']):,}")
        c2.metric("Commercials (Hedgers) Net", f"{int(last['Comm_Net']):,}", f"{int(last['Comm_Net'] - prev['Comm_Net']):,}")
        c3.metric("Small Speculators Net", f"{int(last['SmallSpec_Net']):,}", f"{int(last['SmallSpec_Net'] - prev['SmallSpec_Net']):,}")
        c4.metric("Total Open Interest", f"{int(last['open_interest_all']):,}", f"{int(last['open_interest_all'] - prev['open_interest_all']):,}")
        
        # --- NEW: TRADINGSTER STYLE NET POSITION HISTOGRAM ---
        st.markdown("#### 📈 Non-Commercial Net Position Trend (Funds Direction)")
        st.markdown("اگر یہ گراف اوپر جا رہا ہے (سبز)، تو فنڈز بائنگ کر رہے ہیں۔ اگر نیچے گر رہا ہے (سرخ)، تو فنڈز سیلنگ کر رہے ہیں۔")
        
        fig3_1 = go.Figure()
        
        # Non-Commercials as a bold Histogram (Bar chart) centered at 0
        colors_noncomm = np.where(cot_df['NonComm_Net'] > 0, 'rgba(38, 166, 154, 0.8)', 'rgba(239, 83, 80, 0.8)')
        fig3_1.add_trace(go.Bar(
            x=cot_df['report_date_as_yyyy_mm_dd'], 
            y=cot_df['NonComm_Net'], 
            name='Large Specs (Funds) Net', 
            marker_color=colors_noncomm
        ))
        
        # Commercials as an Inverse Line
        fig3_1.add_trace(go.Scatter(
            x=cot_df['report_date_as_yyyy_mm_dd'], 
            y=cot_df['Comm_Net'], 
            mode='lines', 
            name='Commercials (Hedgers) Net', 
            line=dict(color='yellow', width=2)
        ))
        
        fig3_1.add_hline(y=0, line_width=2, line_color="white") # Zero Line
        fig3_1.update_layout(height=450, template="plotly_dark", margin=dict(l=10, r=10, t=30, b=10), legend=dict(orientation="h", yanchor="bottom", y=1.02, xanchor="right", x=1))
        st.plotly_chart(fig3_1, use_container_width=True, config=tv_config)
        
        # --- Bar Chart: Longs vs Shorts ---
        st.markdown("#### ⚖️ Current Positions (Long vs Short Breakdown)")
        fig3_2 = go.Figure(data=[
            go.Bar(name='Longs (Buy)', x=['Large Specs (Funds)', 'Commercials (Hedgers)', 'Small Specs'], y=[last['noncomm_positions_long_all'], last['comm_positions_long_all'], last['nonrept_positions_long_all']], marker_color='rgba(38, 166, 154, 0.8)'),
            go.Bar(name='Shorts (Sell)', x=['Large Specs (Funds)', 'Commercials (Hedgers)', 'Small Specs'], y=[last['noncomm_positions_short_all'], last['comm_positions_short_all'], last['nonrept_positions_short_all']], marker_color='rgba(239, 83, 80, 0.8)')
        ])
        fig3_2.update_layout(barmode='group', height=400, template="plotly_dark", margin=dict(l=10, r=10, t=30, b=10))
        st.plotly_chart(fig3_2, use_container_width=True, config=tv_config)
        
    else:
        st.warning("⚠️ Fetching CFTC data... (Updates Weekly)")

# --- T4: OPEN INTEREST & VOLUME ---
with t4:
    st.subheader("📈 L4: Daily Futures Volume")
    fig4 = make_subplots(rows=2, cols=1, shared_xaxes=True, vertical_spacing=0.03, row_heights=[0.7, 0.3])
    fig4.add_trace(go.Candlestick(x=df['Date'], open=df['Open'], high=df['High'], low=df['Low'], close=df['Close']), row=1, col=1)
    fig4.add_trace(go.Bar(x=df['Date'], y=df['Volume'], marker_color=df['Std_Vol_Color'], marker_line_width=0), row=2, col=1)
    st.plotly_chart(apply_tv_style(fig4, 600), use_container_width=True, config=tv_config)

# --- T5: SMC & MACRO ---
with t5:
    corr_dxy, corr_tnx = fetch_macro_correlation(ticker_symbol)
    if corr_dxy is not None:
        c1, c2 = st.columns(2)
        c1.metric("Correlation (US Dollar - DXY)", f"{round(corr_dxy * 100, 1)}%")
        c2.metric("Correlation (US 10Y Bonds)", f"{round(corr_tnx * 100, 1)}%")
        st.divider()

    fig5 = go.Figure(data=[go.Candlestick(x=df['Date'], open=df['Open'], high=df['High'], low=df['Low'], close=df['Close'])])
    
    if not df[df['Bullish_FVG']].empty and df[df['Bullish_FVG']].index[-1] >= 2:
        fig5.add_hrect(y0=df.loc[df[df['Bullish_FVG']].index[-1]-2, 'Low'], y1=df.loc[df[df['Bullish_FVG']].index[-1]-2, 'High'], fillcolor="rgba(0, 255, 0, 0.15)", line_width=1, line_color="green")
    if not df[df['Bearish_FVG']].empty and df[df['Bearish_FVG']].index[-1] >= 2:
        fig5.add_hrect(y0=df.loc[df[df['Bearish_FVG']].index[-1]-2, 'Low'], y1=df.loc[df[df['Bearish_FVG']].index[-1]-2, 'High'], fillcolor="rgba(255, 0, 0, 0.15)", line_width=1, line_color="red")

    fig5.add_trace(go.Scatter(x=df[df['Sweep_High']]['Date'], y=df[df['Sweep_High']]['High'], mode='markers+text', text=["💧 SWEEP"]*len(df[df['Sweep_High']]), textposition="top center", textfont=dict(color="cyan", size=11), marker=dict(color='cyan', size=10, symbol='triangle-down')))
    fig5.add_trace(go.Scatter(x=df[df['Sweep_Low']]['Date'], y=df[df['Sweep_Low']]['Low'], mode='markers+text', text=["💧 SWEEP"]*len(df[df['Sweep_Low']]), textposition="bottom center", textfont=dict(color="cyan", size=11), marker=dict(color='cyan', size=10, symbol='triangle-up')))
    st.plotly_chart(apply_tv_style(fig5, 600), use_container_width=True, config=tv_config)

# ==========================================
# 6. SIDEBAR - AI ENGINE
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
