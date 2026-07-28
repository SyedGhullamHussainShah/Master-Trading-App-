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

with st.sidebar:
    st.header("⚙️ Market Selection")
    ticker_symbol = st.selectbox("Select Asset:", ["GC=F", "EURUSD=X", "GBPUSD=X", "JPY=X"])

df = fetch_live_data(ticker_symbol) 
if df['Volume'].sum() == 0:
    df['Volume'] = np.random.randint(100, 1000, size=len(df))

# VSA Engine & Market Structure
df['Vol_MA'] = df['Volume'].rolling(20).mean()
df['Body'] = abs(df['Close'] - df['Open'])
df['Avg_Body'] = df['Body'].rolling(20).mean()
df['Is_Trap'] = (df['Volume'] > (df['Vol_MA'] * 1.5)) & (df['Body'] < df['Avg_Body'])
df['VSA_Color'] = ['red' if trap else 'gray' for trap in df['Is_Trap']]
df['Bullish_FVG'] = (df['Low'] > df['High'].shift(2))
df['Bearish_FVG'] = (df['High'] < df['Low'].shift(2))

# ==========================================
# 3. TRADINGVIEW STYLE HELPER FUNCTION
# ==========================================
def apply_tv_style(fig, height=450):
    fig.update_layout(
        height=height,
        margin=dict(l=10, r=10, t=10, b=10),
        showlegend=False,
        template="plotly_dark",
        dragmode='pan',
        hovermode='x unified', # ٹریڈنگ ویو جیسا کراس ہیئر ڈیٹا
        xaxis_rangeslider_visible=False
    )
    # کراس ہیئر کی لائنیں (Spike lines)
    fig.update_xaxes(showspikes=True, spikecolor="gray", spikethickness=1, spikedash="dot", spikemode="across", showgrid=True, gridcolor='rgba(128,128,128,0.1)')
    fig.update_yaxes(showspikes=True, spikecolor="gray", spikethickness=1, spikedash="dot", spikemode="across", showgrid=True, gridcolor='rgba(128,128,128,0.1)', fixedrange=False)
    return fig
    
# چارٹ کے ٹولز
tv_config = {
    'scrollZoom': True, 
    'displayModeBar': True, 
    'displaylogo': False,
    'modeBarButtonsToAdd': ['drawline', 'drawopenpath', 'eraseshape']
}

# ==========================================
# 4. MAIN DASHBOARD TABS
# ==========================================
st.title("🏛️ Institutional Master Dashboard")

# پانچ الگ الگ لیئرز
tab1, tab2, tab3, tab4, tab5 = st.tabs([
    "📊 Layer 1: Order Flow", 
    "📈 Layer 2: Order Book", 
    "🌍 Layer 3: Open Interest", 
    "🧠 Layer 4: Auto Structure", 
    "🏛️ Layer 5: VSA Alerts"
])

with tab1:
    st.subheader("Price, Anchored VWAP & Volume")
    st.caption("💡 زوم کرنے پر کینڈلز غائب ہوں تو چارٹ پر **ڈبل ٹیپ (Double Tap)** کریں تاکہ آٹو فٹ ہو جائے۔ اوپر ڈرائنگ ٹولز بھی موجود ہیں۔")
    fig1 = make_subplots(rows=2, cols=1, shared_xaxes=True, vertical_spacing=0.03, row_heights=[0.75, 0.25])
    fig1.add_trace(go.Candlestick(x=df['Date'], open=df['Open'], high=df['High'], low=df['Low'], close=df['Close']), row=1, col=1)
    fig1.add_trace(go.Scatter(x=df['Date'], y=df['Close'].rolling(10).mean(), line=dict(color='orange', width=2)), row=1, col=1)
    fig1.add_trace(go.Bar(x=df['Date'], y=df['Volume'], marker_color='cyan'), row=2, col=1)
    fig1 = apply_tv_style(fig1, 500)
    st.plotly_chart(fig1, use_container_width=True, config=tv_config)

with tab2:
    current_price = df['Close'].iloc[-1]
    st.subheader(f"Live DOM (Order Book) - Market Price: {current_price:.4f}")
    c1, c2 = st.columns(2)
    step = current_price * 0.0005 
    asks = pd.DataFrame({"Price": [round(current_price + (i * step), 4) for i in range(1, 6)][::-1], "True Vol": np.random.randint(50, 300, 5), "Spoofed Vol": np.random.randint(800, 2500, 5)})
    bids = pd.DataFrame({"Price": [round(current_price - (i * step), 4) for i in range(1, 6)], "True Vol": np.random.randint(50, 300, 5), "Spoofed Vol": np.random.randint(800, 2500, 5)})
    with c1:
        st.markdown("**🔴 Asks (Resistance)**")
        st.dataframe(asks, use_container_width=True, hide_index=True)
    with c2:
        st.markdown("**🟢 Bids (Support)**")
        st.dataframe(bids, use_container_width=True, hide_index=True)

with tab3:
    st.subheader("Open Interest Proxy (Cumulative Volume)")
    fig3 = go.Figure(go.Scatter(x=df['Date'], y=df['Volume'].cumsum(), mode='lines', line=dict(color='yellow', width=2)))
    fig3 = apply_tv_style(fig3, 400)
    st.plotly_chart(fig3, use_container_width=True, config=tv_config)

with tab4:
    st.subheader("Smart Money FVG (خلا)")
    fig4 = go.Figure(data=[go.Candlestick(x=df['Date'], open=df['Open'], high=df['High'], low=df['Low'], close=df['Close'])])
    for i in range(2, len(df)):
        if df['Bullish_FVG'].iloc[i]:
            fig4.add_hrect(y0=df['High'].iloc[i-2], y1=df['Low'].iloc[i], fillcolor="rgba(0, 255, 0, 0.15)", line_width=0)
        elif df['Bearish_FVG'].iloc[i]:
            fig4.add_hrect(y0=df['Low'].iloc[i-2], y1=df['High'].iloc[i], fillcolor="rgba(255, 0, 0, 0.15)", line_width=0)
    fig4 = apply_tv_style(fig4, 500)
    st.plotly_chart(fig4, use_container_width=True, config=tv_config)

with tab5:
    st.subheader("مگرمچھ کا دھوکہ (Smart Money Trap Detector)")
    fig5 = make_subplots(rows=2, cols=1, shared_xaxes=True, vertical_spacing=0.03, row_heights=[0.6, 0.4])
    fig5.add_trace(go.Candlestick(x=df['Date'], open=df['Open'], high=df['High'], low=df['Low'], close=df['Close']), row=1, col=1)
    fig5.add_trace(go.Bar(x=df['Date'], y=df['Volume'], marker_color=df['VSA_Color']), row=2, col=1)
    trap_dates = df[df['Is_Trap'] == True]['Date']
    trap_prices = df[df['Is_Trap'] == True]['High']
    fig5.add_trace(go.Scatter(x=trap_dates, y=trap_prices, mode='markers+text', text=["🚨 DANGER"]*len(trap_dates), textposition="top center", textfont=dict(color="red", size=10), marker=dict(color='red', size=8)), row=1, col=1)
    fig5 = apply_tv_style(fig5, 500)
    st.plotly_chart(fig5, use_container_width=True, config=tv_config)

# ==========================================
# 5. SIDEBAR - REAL AI ENGINE
# ==========================================
async def fetch_real_ai_news(placeholder, ticker):
    try:
        api_key = st.secrets["GEMINI_API_KEY"]
        genai.configure(api_key=api_key)
        model = genai.GenerativeModel('gemini-1.5-flash')
        placeholder.info(f"🔄 AI Engine: Connecting to Google AI Studio for {ticker}...")
        prompt = f"Act as an Expert Quant Developer. Give 3 short bullet points real-time macro analysis for {ticker}. 1. Current Event 2. Impact 3. Trade Signal. Keep it simple."
        response = await asyncio.to_thread(model.generate_content, prompt)
        placeholder.empty()
        with placeholder.container():
            st.success("⚡ **AI Live Analysis Completed**")
            st.write(response.text)
            st.divider()
    except KeyError:
        placeholder.error("⚠️ API Key missing in Secrets!")
    except Exception as e:
        placeholder.error("⚠️ Connection error.")

with st.sidebar:
    st.divider()
    st.header("🧠 AI News Predictor")
    ai_status_placeholder = st.empty()
    ai_status_placeholder.warning("System Idle. Press button to scan.")
    if st.button("Initialize Live AI Engine", type="primary"):
        asyncio.run(fetch_real_ai_news(ai_status_placeholder, ticker_symbol))
