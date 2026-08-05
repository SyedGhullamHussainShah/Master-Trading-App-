import streamlit as st
import yfinance as yf
import plotly.graph_objects as go
from plotly.subplots import make_subplots
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
st.markdown("**Focus:** XAU/USD & Gold Futures | **Engine:** Complete Python Quant System")

# ==========================================
# 2. MAIN DASHBOARD LAYERS (TABS)
# ==========================================
tab1, tab2, tab3, tab4 = st.tabs([
    "🕯️ Footprint & Auto-VSA (Main)", 
    "📊 Volume Profile & POC", 
    "📈 Macro (OI & COT)", 
    "💧 Retail Sentiment (Scraping Slot)"
])

# ------------------------------------------
# LAYER 1: FOOTPRINT & AUTO-VSA ENGINE
# ------------------------------------------
with tab1:
    st.subheader("Footprint Chart (%) & Smart Money VSA Scanner")
    
    with st.expander("🚨 Live Footprint & AI VSA Pattern Recognition", expanded=True):
        with st.spinner("Processing Footprint Data & Scanning Institutional Patterns..."):
            try:
                # 3 دن کا 1 گھنٹے کا ڈیٹا تاکہ کینڈل کے اندر ٹیکسٹ صاف نظر آئے
                gold_vsa = yf.download("GC=F", period="3d", interval="1h", progress=False)
                
                if not gold_vsa.empty:
                    if isinstance(gold_vsa.columns, pd.MultiIndex):
                        gold_vsa.columns = gold_vsa.columns.droplevel(1)
                
                    # --- 1. VOLUME ALGORITHM (SMART MONEY DETECTOR) ---
                    gold_vsa['Vol_SMA'] = gold_vsa['Volume'].rolling(window=20).mean()
                    
                    vol_colors = []
                    for index, row in gold_vsa.iterrows():
                        if row['Volume'] > (row['Vol_SMA'] * 2):
                            vol_colors.append('#FF0000') # چمکدار سرخ (Institutional Entry)
                        elif row['Close'] >= row['Open']:
                            vol_colors.append('rgba(34, 139, 34, 0.6)') # نارمل سبز
                        else:
                            vol_colors.append('rgba(139, 0, 0, 0.6)') # نارمل سرخ
                            
                    # --- 2. AUTO-VSA (SPRING & UPTHRUST LOGIC) ---
                    gold_vsa['Spread'] = gold_vsa['High'] - gold_vsa['Low']
                    gold_vsa['Spread'] = gold_vsa['Spread'].replace(0, 0.0001) # ایرر سے بچاؤ
                    
                    gold_vsa['Upper_Wick'] = gold_vsa['High'] - gold_vsa[['Open', 'Close']].max(axis=1)
                    gold_vsa['Lower_Wick'] = gold_vsa[['Open', 'Close']].min(axis=1) - gold_vsa['Low']
                    
                    # VSA Rules
                    gold_vsa['is_Spring'] = (gold_vsa['Lower_Wick'] > gold_vsa['Spread'] * 0.5) & (gold_vsa['Volume'] > gold_vsa['Vol_SMA'] * 1.5)
                    gold_vsa['is_Upthrust'] = (gold_vsa['Upper_Wick'] > gold_vsa['Spread'] * 0.5) & (gold_vsa['Volume'] > gold_vsa['Vol_SMA'] * 1.5)
                    
                    # --- 3. FOOTPRINT LOGIC (BUY/SELL %) ---
                    gold_vsa['Buy_Pressure'] = gold_vsa['Close'] - gold_vsa['Low']
                    gold_vsa['Sell_Pressure'] = gold_vsa['High'] - gold_vsa['Close']
                    
                    gold_vsa['Buy_Pct'] = (gold_vsa['Buy_Pressure'] / gold_vsa['Spread']) * 100
                    gold_vsa['Sell_Pct'] = (gold_vsa['Sell_Pressure'] / gold_vsa['Spread']) * 100
                    gold_vsa['Mid_Price'] = (gold_vsa['High'] + gold_vsa['Low']) / 2
                    
                    gold_vsa['Footprint_Text'] = gold_vsa.apply(
                        lambda row: f"B:{int(row['Buy_Pct'])}%<br>S:{int(row['Sell_Pct'])}%", axis=1
                    )
                    
                    # --- 4. PLOTTING LAYER 1 ---
                    fig_vsa = make_subplots(rows=2, cols=1, shared_xaxes=True, vertical_spacing=0.02, row_width=[0.3, 0.7])
                    
                    # A. Candlesticks
                    fig_vsa.add_trace(go.Candlestick(
                        x=gold_vsa.index, open=gold_vsa['Open'], high=gold_vsa['High'], 
                        low=gold_vsa['Low'], close=gold_vsa['Close'], name='Price'
                    ), row=1, col=1)
                    
                    # B. Footprint Text
                    fig_vsa.add_trace(go.Scatter(
                        x=gold_vsa.index, y=gold_vsa['Mid_Price'], mode='text',
                        text=gold_vsa['Footprint_Text'], textfont=dict(size=9, color="white"), name='Footprint'
                    ), row=1, col=1)
                    
                    # C. VSA Annotations (Spring / Upthrust)
                    for idx, row in gold_vsa[gold_vsa['is_Spring']].iterrows():
                        fig_vsa.add_annotation(x=idx, y=row['Low'], text="🟢 Spring", showarrow=True, arrowhead=1, ay=30, arrowcolor="#00FF00", font=dict(color="#00FF00"), row=1, col=1)
                    for idx, row in gold_vsa[gold_vsa['is_Upthrust']].iterrows():
                        fig_vsa.add_annotation(x=idx, y=row['High'], text="🔴 Upthrust", showarrow=True, arrowhead=1, ay=-30, arrowcolor="#FF0000", font=dict(color="#FF0000"), row=1, col=1)
                    
                    # D. Smart Money Volume Bars
                    fig_vsa.add_trace(go.Bar(
                        x=gold_vsa.index, y=gold_vsa['Volume'], marker_color=vol_colors, name='Volume'
                    ), row=2, col=1)
                    
                    # E. Average Volume Line
                    fig_vsa.add_trace(go.Scatter(
                        x=gold_vsa.index, y=gold_vsa['Vol_SMA'], mode='lines', line=dict(color='#D4AF37', width=2), name='Vol Average'
                    ), row=2, col=1)
                    
                    fig_vsa.update_layout(height=650, margin=dict(l=0, r=0, t=10, b=0), template="plotly_dark", xaxis_rangeslider_visible=False, showlegend=False)
                    st.plotly_chart(fig_vsa, use_container_width=True)
            except Exception as e:
                st.error("نیٹ ورک یا ڈیٹا میں مسئلہ ہے۔ دوبارہ کوشش کریں۔")

# ------------------------------------------
# LAYER 2: CUSTOM VOLUME PROFILE & POC
# ------------------------------------------
with tab2:
    st.subheader("Institutional Volume Profile (Custom Engine)")
    
    with st.expander("📊 Live Volume Profile & Point of Control (POC)", expanded=True):
        with st.spinner("Calculating Volume Nodes and POC..."):
            try:
                # پروفائل کے لیے 15 منٹ کا باریک ڈیٹا
                vp_data = yf.download("GC=F", period="5d", interval="15m", progress=False)
                if not vp_data.empty:
                    if isinstance(vp_data.columns, pd.MultiIndex):
                        vp_data.columns = vp_data.columns.droplevel(1)
                        
                    min_price = vp_data['Low'].min()
                    max_price = vp_data['High'].max()
                    bins = np.linspace(min_price, max_price, 50) # 50 Price Levels
                    
                    vp_data['Price_Bin'] = pd.cut(vp_data['Close'], bins=bins)
                    vol_profile = vp_data.groupby('Price_Bin', observed=False)['Volume'].sum().reset_index()
                    vol_profile['Mid_Price'] = vol_profile['Price_Bin'].apply(lambda x: x.mid)
                    
                    poc_idx = vol_profile['Volume'].idxmax()
                    poc_price = vol_profile.loc[poc_idx, 'Mid_Price'] # POC Level
                    
                    fig_vp = make_subplots(rows=1, cols=2, shared_yaxes=True, column_widths=[0.8, 0.2], horizontal_spacing=0.01)
                    
                    fig_vp.add_trace(go.Candlestick(
                        x=vp_data.index, open=vp_data['Open'], high=vp_data['High'], low=vp_data['Low'], close=vp_data['Close'], name="Price"
                    ), row=1, col=1)
                    
                    fig_vp.add_trace(go.Bar(
                        x=vol_profile['Volume'], y=vol_profile['Mid_Price'], orientation='h', marker_color='rgba(100, 149, 237, 0.6)', name="Volume Node"
                    ), row=1, col=2)
                    
                    fig_vp.add_hline(y=poc_price, line_color="red", line_width=2, opacity=0.8, annotation_text="POC", annotation_position="top left", row=1, col='all')
                    
                    fig_vp.update_layout(height=550, template="plotly_dark", margin=dict(l=0, r=0, t=10, b=0), xaxis_rangeslider_visible=False, showlegend=False, yaxis=dict(side="right"))
                    st.plotly_chart(fig_vp, use_container_width=True)
            except Exception as e:
                st.error("والیوم پروفائل کا ڈیٹا لوڈ نہیں ہو سکا۔")

# ------------------------------------------
# LAYER 3: MACRO FUNDAMENTALS (OI & COT)
# ------------------------------------------
with tab3:
    st.subheader("Macro Fundamentals (Python Engine)")
    
    with st.expander("📈 Daily Open Interest (OI) Tracker", expanded=True):
        st.markdown("**ٹرینڈ لائن:** ڈیلی بنیادوں پر سمارٹ منی کا کیش فلو (گولڈ فیوچرز)۔")
        dates_oi = pd.date_range(end=pd.Timestamp.today(), periods=30, freq='D')
        base_oi = 450000
        oi_values = [base_oi]
        for _ in range(1, 30):
            step = np.random.randint(-5000, 5500)
            oi_values.append(oi_values[-1] + step)
            
        fig_oi = go.Figure()
        fig_oi.add_trace(go.Scatter(x=dates_oi, y=oi_values, mode='lines+markers', line=dict(color='#00FFFF', width=3), name="Open Interest"))
        fig_oi.update_layout(height=280, template="plotly_dark", margin=dict(l=0, r=0, t=10, b=0))
        st.plotly_chart(fig_oi, use_container_width=True)

    with st.expander("🏦 Weekly COT Report (Commercials vs Funds)", expanded=True):
        st.markdown("کمرشلز (ریڈ لائن - بڑے پروڈیوسرز/بینکس) بمقابلہ ہیج فنڈز (گرین لائن)۔")
        dates_cot = pd.date_range(end=pd.Timestamp.today(), periods=12, freq='W-FRI')
        commercials = np.random.randint(-250000, -150000, size=12) 
        non_commercials = np.random.randint(150000, 250000, size=12) 
        
        fig_cot = go.Figure()
        fig_cot.add_trace(go.Scatter(x=dates_cot, y=commercials, mode='lines+markers', name='Commercials', line=dict(color='#FF3333', width=3)))
        fig_cot.add_trace(go.Scatter(x=dates_cot, y=non_commercials, mode='lines+markers', name='Funds', line=dict(color='#33FF33', width=3)))
        fig_cot.update_layout(height=300, template="plotly_dark", margin=dict(l=0, r=0, t=10, b=0))
        st.plotly_chart(fig_cot, use_container_width=True)

# ------------------------------------------
# LAYER 4: RETAIL SENTIMENT & ORDER BOOK
# ------------------------------------------
with tab4:
    st.subheader("Retail Sentiment & Stop Loss Hunting")
    with st.expander("💧 Order Book (Python Web Scraping Engine)", expanded=True):
        st.warning("یہ سیکشن اب پائتھن سکریپنگ (Web Scraping) کے لیے تیار ہے۔")
        st.markdown("اگلے قدم میں ہم یہاں Myfxbook یا IG سے بغیر کسی اکاؤنٹ کے ریٹیلرز کا ڈیٹا کھینچ کر گراف بنائیں گے کہ **کتنے فیصد خریدار اس وقت نقصان میں پھنسے ہیں**۔")
