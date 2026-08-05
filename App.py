import streamlit as st
import streamlit.components.v1 as components
import yfinance as yf
import plotly.graph_objects as go
import pandas as pd
import numpy as np

# ==========================================
# 1. PAGE CONFIGURATION
# ==========================================
st.set_page_config(page_title="Institutional Master Dashboard", page_icon="🏦", layout="wide", initial_sidebar_state="collapsed")

st.markdown("""
<style>
    .block-container { padding-top: 1rem; padding-bottom: 0rem; }
    .streamlit-expanderHeader { color: #D4AF37; font-weight: bold; font-size: 16px; }
</style>
""", unsafe_allow_html=True)

st.title("🏦 Institutional Master Dashboard")
st.markdown("**Focus:** XAU/USD & Gold Futures | **Engine:** TradingView + Custom Python Algorithms")

# ==========================================
# 2. MAIN DASHBOARD LAYERS (TABS)
# ==========================================
tab1, tab2, tab3, tab4 = st.tabs([
    "🕯️ SMC & VSA", 
    "📊 Order Flow & Vol Profile", 
    "📈 OI & COT Data", 
    "💧 Retail Sentiment"
])

# ------------------------------------------
# LAYER 1: SMC & VSA
# ------------------------------------------
with tab1:
    st.subheader("Price Action & Institutional Footprints (XAU/USD)")
    
    with st.expander("📈 Live Interactive Chart (SMC)", expanded=True):
        tv_xauusd = """
        <div class="tradingview-widget-container" style="height:450px;width:100%">
          <div id="tv_xauusd" style="height:100%;width:100%"></div>
          <script type="text/javascript" src="https://s3.tradingview.com/tv.js"></script>
          <script type="text/javascript">
          new TradingView.widget({
          "autosize": true, "symbol": "OANDA:XAUUSD", "interval": "15", "timezone": "Etc/UTC", "theme": "dark",
          "style": "1", "locale": "en", "enable_publishing": false, "backgroundColor": "#000000",
          "withdateranges": true, "hide_top_toolbar": false, "hide_side_toolbar": false, "allow_symbol_change": true,
          "container_id": "tv_xauusd"
          });
          </script>
        </div>
        """
        components.html(tv_xauusd, height=450)

    # UPDATED: VSA Institutional Volume Scanner with Exact Color Rules
    with st.expander("🚨 VSA Institutional Volume Scanner", expanded=True):
        try:
            gold_vsa = yf.download("GC=F", period="5d", interval="15m", progress=False)
            if not gold_vsa.empty:
                gold_vsa['Vol_SMA'] = gold_vsa['Volume'].rolling(window=20).mean()
                
                # Custom Color Logic
                colors = []
                for index, row in gold_vsa.iterrows():
                    # Smart Money Anomaly (> 2x SMA) -> Extra Bright Red
                    if row['Volume'] > (row['Vol_SMA'] * 2):
                        colors.append('#FF0000') 
                    # Normal Bullish Candle -> Normal Green
                    elif row['Close'] >= row['Open']:
                        colors.append('#228B22') 
                    # Normal Bearish Candle -> Normal Dark Red
                    else:
                        colors.append('#8B0000') 
                
                fig = go.Figure()
                fig.add_trace(go.Bar(x=gold_vsa.index, y=gold_vsa['Volume'], marker_color=colors, name='Volume'))
                fig.add_trace(go.Scatter(x=gold_vsa.index, y=gold_vsa['Vol_SMA'], mode='lines', line=dict(color='#D4AF37', width=2), name='Average'))
                fig.update_layout(height=200, margin=dict(l=0, r=0, t=10, b=0), template="plotly_dark", xaxis_rangeslider_visible=False)
                st.plotly_chart(fig, use_container_width=True)
        except:
            st.error("Volume Data Error")

# ------------------------------------------
# LAYER 2: ORDER FLOW & VOLUME PROFILE
# ------------------------------------------
with tab2:
    st.subheader("Institutional Volume & POC Tracking")
    with st.expander("📊 Volume Profile (POC, VAH, VAL)", expanded=True):
        tv_vol = """
        <div class="tradingview-widget-container" style="height:500px;width:100%">
          <div id="tv_vol" style="height:100%;width:100%"></div>
          <script type="text/javascript" src="https://s3.tradingview.com/tv.js"></script>
          <script type="text/javascript">
          new TradingView.widget({
          "autosize": true, "symbol": "COMEX:GC1!", "interval": "60", "timezone": "Etc/UTC", "theme": "dark",
          "style": "1", "locale": "en", "enable_publishing": false, "backgroundColor": "#000000",
          "hide_top_toolbar": false, "hide_side_toolbar": false,
          "container_id": "tv_vol"
          });
          </script>
        </div>
        """
        components.html(tv_vol, height=500)

# ------------------------------------------
# LAYER 3: OPEN INTEREST (OI) & COT DATA
# ------------------------------------------
with tab3:
    st.subheader("Macro Fundamentals (Custom Python Engine)")
    
    # UPDATED: Daily Open Interest Tracker (Now a Line Graph)
    with st.expander("📈 Daily Open Interest (OI) Tracker", expanded=True):
        st.markdown("**اوپن انٹرسٹ ٹرینڈ لائن:** لائن اوپر جانے کا مطلب نیا انسٹیٹیوشنل کیش مارکیٹ میں آ رہا ہے۔")
        
        # Structural data array to show how the real CME API will look
        dates_oi = pd.date_range(end=pd.Timestamp.today(), periods=30, freq='D')
        
        # Simulating a trending OI logic
        base_oi = 450000
        oi_values = [base_oi]
        for _ in range(1, 30):
            step = np.random.randint(-5000, 5500) # Slightly upward bias
            oi_values.append(oi_values[-1] + step)
            
        fig_oi = go.Figure()
        # Changed to Scatter with mode='lines+markers'
        fig_oi.add_trace(go.Scatter(x=dates_oi, y=oi_values, mode='lines+markers', line=dict(color='#00FFFF', width=3), name="Open Interest"))
        
        fig_oi.update_layout(height=280, template="plotly_dark", margin=dict(l=0, r=0, t=10, b=0), xaxis_title="Daily Update", yaxis_title="Total Contracts")
        st.plotly_chart(fig_oi, use_container_width=True)
        st.caption("API Slot: Awaiting Live CME Futures Data Feed.")

    # 2. Weekly COT Report Graph
    with st.expander("🏦 Weekly COT Report (Commercials vs Non-Commercials)", expanded=True):
        st.markdown("ہر جمعہ کو اپڈیٹ ہوتا ہے۔ ہم یہاں **کمرشلز (ریڈ لائن)** اور **ہیج فنڈز (گرین لائن)** کی پوزیشنز کا ٹکراؤ دیکھ رہے ہیں۔")
        
        dates_cot = pd.date_range(end=pd.Timestamp.today(), periods=12, freq='W-FRI')
        commercials = np.random.randint(-250000, -150000, size=12) 
        non_commercials = np.random.randint(150000, 250000, size=12) 
        
        fig_cot = go.Figure()
        fig_cot.add_trace(go.Scatter(x=dates_cot, y=commercials, mode='lines+markers', name='Commercials (Smart Money)', line=dict(color='#FF3333', width=3)))
        fig_cot.add_trace(go.Scatter(x=dates_cot, y=non_commercials, mode='lines+markers', name='Non-Commercials (Funds)', line=dict(color='#33FF33', width=3)))
        
        fig_cot.update_layout(height=300, template="plotly_dark", margin=dict(l=0, r=0, t=10, b=0), xaxis_title="Weekly Update (Fridays)", yaxis_title="Net Positions")
        st.plotly_chart(fig_cot, use_container_width=True)
        st.caption("API Slot: Awaiting Live CFTC Data Integration.")

# ------------------------------------------
# LAYER 4: RETAIL SENTIMENT & ORDER BOOK
# ------------------------------------------
with tab4:
    st.subheader("Position Book & Stop Losses")
    with st.expander("💧 Order Book (Pending API)", expanded=True):
        st.warning("انتظار فرمائیں: ریٹیلرز کے سٹاپ لاسز ہنٹ کرنے کا لائیو ڈیٹا API (FXSSI/OANDA) ملنے پر یہاں ظاہر ہوگا۔")
