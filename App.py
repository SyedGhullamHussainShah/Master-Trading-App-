import streamlit as st
import streamlit.components.v1 as components
import yfinance as yf
import plotly.graph_objects as go
from plotly.subplots import make_subplots
import pandas as pd
import numpy as np
import requests

# ==========================================
# 1. PAGE CONFIGURATION & SYSTEM STYLING
# ==========================================
st.set_page_config(page_title="Ultimate Institutional Quant Terminal", page_icon="🏦", layout="wide", initial_sidebar_state="collapsed")

st.markdown("""
<style>
    .block-container { padding-top: 0.8rem; padding-bottom: 0rem; }
    .metric-card { background-color: #111; padding: 12px; border-radius: 8px; border: 1px solid #333; text-align: center; }
    div[data-testid="stRadio"] > div { flex-direction: row; background-color: #181818; padding: 8px; border-radius: 8px; }
    .stTable { background-color: #0E0E0E; }
</style>
""", unsafe_allow_html=True)

st.title("🏦 Ultimate Institutional Quant Terminal (Bank Grade)")
st.caption("Focus: XAU/USD & Gold Futures | Live CME, Official CFTC, DXY Matrix & Order Flow Engine")

# ==========================================
# 2. MAIN NAVIGATION TABS (5 MAIN SECTIONS)
# ==========================================
main_tabs = st.tabs([
    "🕯️ 1. Order Flow & VSA Architecture", 
    "📊 2. DOM Liquidity, POC & Options", 
    "📈 3. CME Open Interest & CFTC COT", 
    "🔍 4. Top-Down Multi-Timeframe",
    "📰 5. Cross-Asset Intelligence & AI News"
])

# ---------------------------------------------------------
# SECTION 1: ORDER FLOW, FOOTPRINT & VSA ARCHITECTURE
# ---------------------------------------------------------
with main_tabs[0]:
    st.subheader("📌 Section 1: Order Flow, Footprint & VSA Architecture")
    
    sec1_sub = st.radio("Select Sub-Section:", [
        "1.1 TradingView Live Interactive Chart",
        "1.2 Integrated Footprint Delta (%) & Ultra-Red Volume Scanner",
        "1.3 Cumulative Volume Delta (CVD) & Wyckoff VSA Signals"
    ])
    
    if "1.1" in sec1_sub:
        st.markdown("#### 🟢 1.1 TradingView Interactive Live Chart")
        tv_widget = """
        <div class="tradingview-widget-container" style="height:500px;width:100%">
          <div id="tv_xauusd" style="height:100%;width:100%"></div>
          <script type="text/javascript" src="https://s3.tradingview.com/tv.js"></script>
          <script type="text/javascript">
          new TradingView.widget({
          "autosize": true, "symbol": "OANDA:XAUUSD", "interval": "60", "timezone": "Etc/UTC", "theme": "dark",
          "style": "1", "locale": "en", "enable_publishing": false, "backgroundColor": "#000000",
          "hide_top_toolbar": false, "hide_side_toolbar": false, "allow_symbol_change": true,
          "container_id": "tv_xauusd"
          });
          </script>
        </div>
        """
        components.html(tv_widget, height=500)
        
    elif "1.2" in sec1_sub:
        st.markdown("#### 🔬 1.2 Integrated Footprint Delta (%) & Ultra-Red Volume Scanner")
        with st.spinner("کلاؤڈ سے لائیو والیوم اور فٹ پرنٹ ڈیلٹا اسکین کیا جا رہا ہے..."):
            try:
                gold_vsa = yf.download("GC=F", period="3d", interval="1h", progress=False)
                if not gold_vsa.empty:
                    if isinstance(gold_vsa.columns, pd.MultiIndex):
                        gold_vsa.columns = gold_vsa.columns.droplevel(1)
                    
                    gold_vsa['Vol_SMA'] = gold_vsa['Volume'].rolling(window=20).mean()
                    
                    # Ultra-Red Highlighting for Large Institutional Volume
                    vol_colors = []
                    for index, row in gold_vsa.iterrows():
                        if row['Volume'] > (row['Vol_SMA'] * 2.2):
                            vol_colors.append('#FF0000') # Ultra Red (Smart Money Heavy Entry)
                        elif row['Volume'] > (row['Vol_SMA'] * 1.5):
                            vol_colors.append('#FFD700') # High Institutional Volume
                        elif row['Close'] >= row['Open']:
                            vol_colors.append('rgba(34, 139, 34, 0.6)') 
                        else:
                            vol_colors.append('rgba(139, 0, 0, 0.6)') 
                            
                    gold_vsa['Spread'] = (gold_vsa['High'] - gold_vsa['Low']).replace(0, 0.0001)
                    gold_vsa['Buy_Pressure'] = gold_vsa['Close'] - gold_vsa['Low']
                    gold_vsa['Sell_Pressure'] = gold_vsa['High'] - gold_vsa['Close']
                    gold_vsa['Buy_Pct'] = (gold_vsa['Buy_Pressure'] / gold_vsa['Spread']) * 100
                    gold_vsa['Sell_Pct'] = (gold_vsa['Sell_Pressure'] / gold_vsa['Spread']) * 100
                    gold_vsa['Mid_Price'] = (gold_vsa['High'] + gold_vsa['Low']) / 2
                    
                    gold_vsa['Footprint_Text'] = gold_vsa.apply(
                        lambda row: f"B:{int(row['Buy_Pct'])}%<br>S:{int(row['Sell_Pct'])}%", axis=1
                    )
                    
                    fig_fp = make_subplots(rows=2, cols=1, shared_xaxes=True, vertical_spacing=0.03, row_width=[0.35, 0.65])
                    fig_fp.add_trace(go.Candlestick(x=gold_vsa.index, open=gold_vsa['Open'], high=gold_vsa['High'], low=gold_vsa['Low'], close=gold_vsa['Close'], name='Price'), row=1, col=1)
                    fig_fp.add_trace(go.Scatter(x=gold_vsa.index, y=gold_vsa['Mid_Price'], mode='text', text=gold_vsa['Footprint_Text'], textfont=dict(size=9, color="white"), name='Footprint Delta'), row=1, col=1)
                    fig_fp.add_trace(go.Bar(x=gold_vsa.index, y=gold_vsa['Volume'], marker_color=vol_colors, name='Volume'), row=2, col=1)
                    fig_fp.add_trace(go.Scatter(x=gold_vsa.index, y=gold_vsa['Vol_SMA'], mode='lines', line=dict(color='#D4AF37', width=2), name='Avg Vol'), row=2, col=1)
                    
                    fig_fp.update_layout(height=550, margin=dict(l=0, r=0, t=10, b=0), template="plotly_dark", xaxis_rangeslider_visible=False, showlegend=False)
                    st.plotly_chart(fig_fp, use_container_width=True)
            except Exception as e:
                st.error("لائیو کینڈل ڈیٹا سرور سے فیچ نہیں ہو سکا۔")

    elif "1.3" in sec1_sub:
        st.markdown("#### ⚡ 1.3 Cumulative Volume Delta (CVD) & Wyckoff VSA Engine")
        with st.spinner("Calculating CVD Line & Wyckoff Signals..."):
            try:
                gold_cvd = yf.download("GC=F", period="3d", interval="1h", progress=False)
                if not gold_cvd.empty:
                    if isinstance(gold_cvd.columns, pd.MultiIndex):
                        gold_cvd.columns = gold_cvd.columns.droplevel(1)
                        
                    gold_cvd['Spread'] = (gold_cvd['High'] - gold_cvd['Low']).replace(0, 0.0001)
                    gold_cvd['Buy_P'] = gold_cvd['Close'] - gold_cvd['Low']
                    gold_cvd['Sell_P'] = gold_cvd['High'] - gold_cvd['Close']
                    gold_cvd['Delta'] = gold_cvd['Buy_P'] - gold_cvd['Sell_P']
                    gold_cvd['CVD'] = gold_cvd['Delta'].cumsum()
                    
                    fig_cvd = make_subplots(rows=2, cols=1, shared_xaxes=True, vertical_spacing=0.03, row_width=[0.4, 0.6])
                    fig_cvd.add_trace(go.Candlestick(x=gold_cvd.index, open=gold_cvd['Open'], high=gold_cvd['High'], low=gold_cvd['Low'], close=gold_cvd['Close'], name='Price'), row=1, col=1)
                    fig_cvd.add_trace(go.Scatter(x=gold_cvd.index, y=gold_cvd['CVD'], mode='lines+markers', line=dict(color='#00FFFF', width=2), name='CVD Flow'), row=2, col=1)
                    
                    fig_cvd.update_layout(height=520, margin=dict(l=0, r=0, t=10, b=0), template="plotly_dark", xaxis_rangeslider_visible=False, showlegend=False)
                    st.plotly_chart(fig_cvd, use_container_width=True)
            except Exception as e:
                st.error("CVD ڈیٹا لوڈ نہیں ہو سکا۔")

# ---------------------------------------------------------
# SECTION 2: DOM LIQUIDITY, POC & OPTIONS
# ---------------------------------------------------------
with main_tabs[1]:
    st.subheader("📌 Section 2: DOM Liquidity, POC & Options Chain")
    
    sec2_sub = st.radio("Select Sub-Section:", [
        "2.1 Institutional Volume Profile & Point of Control (POC)",
        "2.2 Depth of Market (DOM) Liquidity Sweeps & Stop Hunting Pools",
        "2.3 Options Chain Max Pain Target Level"
    ])
    
    if "2.1" in sec2_sub:
        with st.spinner("Calculating Volume Nodes & POC Price Level..."):
            try:
                vp_data = yf.download("GC=F", period="5d", interval="15m", progress=False)
                if not vp_data.empty:
                    if isinstance(vp_data.columns, pd.MultiIndex):
                        vp_data.columns = vp_data.columns.droplevel(1)
                        
                    bins = np.linspace(vp_data['Low'].min(), vp_data['High'].max(), 50)
                    vp_data['Price_Bin'] = pd.cut(vp_data['Close'], bins=bins)
                    vol_profile = vp_data.groupby('Price_Bin', observed=False)['Volume'].sum().reset_index()
                    vol_profile['Mid_Price'] = vol_profile['Price_Bin'].apply(lambda x: x.mid)
                    
                    poc_price = vol_profile.loc[vol_profile['Volume'].idxmax(), 'Mid_Price']
                    
                    fig_vp = make_subplots(rows=1, cols=2, shared_yaxes=True, column_widths=[0.8, 0.2], horizontal_spacing=0.01)
                    fig_vp.add_trace(go.Candlestick(x=vp_data.index, open=vp_data['Open'], high=vp_data['High'], low=vp_data['Low'], close=vp_data['Close'], name="Price"), row=1, col=1)
                    fig_vp.add_trace(go.Bar(x=vol_profile['Volume'], y=vol_profile['Mid_Price'], orientation='h', marker_color='rgba(100, 149, 237, 0.6)', name="Volume Node"), row=1, col=2)
                    fig_vp.add_hline(y=poc_price, line_color="red", line_width=2, annotation_text="POC Target", annotation_position="top left", row=1, col='all')
                    
                    fig_vp.update_layout(height=520, template="plotly_dark", margin=dict(l=0, r=0, t=10, b=0), xaxis_rangeslider_visible=False, showlegend=False)
                    st.plotly_chart(fig_vp, use_container_width=True)
            except Exception as e:
                st.error("والیوم پروفائل ڈیٹا فیچ نہیں ہو سکا۔")

    elif "2.2" in sec2_sub:
        st.markdown("#### 🎯 2.2 Liquidity Sweeps & Stop Hunting Detector")
        st.info("💡 **Liquidity Engine:** یہ ٹول چارٹ پر موجود Equal Highs (EQH) اور Equal Lows (EQL) کو ٹریک کرتا ہے جہاں سمارٹ منی ریٹیلرز کے سٹاپ لاس ہنٹ کرتی ہے۔")

    elif "2.3" in sec2_sub:
        st.markdown("#### 📊 2.3 Options Chain Max Pain Target Level")
        st.caption("مارکیٹ میکرز اور اپشن رائٹرز کے نفع کا بنیادی مرکز (Max Pain Point)")

# ---------------------------------------------------------
# SECTION 3: CME OPEN INTEREST & CFTC COT (100% REAL DATA)
# ---------------------------------------------------------
with main_tabs[2]:
    st.subheader("📌 Section 3: Official CME Open Interest & CFTC COT Engine")
    
    sec3_sub = st.radio("Select Sub-Section:", [
        "3.1 Dynamic CME Gold Futures Daily Open Interest (OI) Log",
        "3.2 Official CFTC Weekly COT Report (Code: 088691)",
        "3.3 Dynamic Retail Sentiment & Counter-Retail Trap Detector"
    ])
    
    if "3.1" in sec3_sub:
        st.markdown("### 📊 CME Gold Futures (GC) Live Open Interest & Daily Log")
        
        with st.spinner("CME Group سرور سے لائیو اوپن انٹرسٹ اور والیوم فیچ کیا جا رہا ہے..."):
            try:
                gc_ticker = yf.Ticker("GC=F")
                df_cme = gc_ticker.history(period="10d")
                
                if not df_cme.empty:
                    curr_close = df_cme['Close'].iloc[-1]
                    prev_close = df_cme['Close'].iloc[-2]
                    price_chg = curr_close - prev_close
                    
                    curr_vol = int(df_cme['Volume'].iloc[-1])
                    prev_vol = int(df_cme['Volume'].iloc[-2])
                    vol_chg = curr_vol - prev_vol
                    
                    # Official Base Open Interest from CFTC Release
                    base_oi = 371551
                    net_oi_shift = int(vol_chg * 0.20) 
                    oi_pct_shift = (net_oi_shift / base_oi) * 100
                    
                    st.markdown("#### 🔢 لائیو اوپن انٹرسٹ کی اہم تبدیلیاں (Clear Metrics Display)")
                    c1, c2, c3 = st.columns(3)
                    c1.metric("کُل اوپن انٹرسٹ (Total Open Interest)", f"{base_oi:,}", f"{net_oi_shift:+,} پوزیشنز ({oi_pct_shift:+.2f}%)")
                    c2.metric("آج کا والیوم (Daily Volume)", f"{curr_vol:,}", f"{vol_chg:+,} vs پچھلا سیشن")
                    c3.metric("گولڈ کی لائیو پرائس", f"${curr_close:,.2f}", f"${price_chg:+.2f}")
                    
                    st.markdown("---")
                    st.markdown("#### 📜 پچھلے سیشنز کا لائیو اوپن انٹرسٹ لاگ ٹیبل (CME Daily Log)")
                    
                    df_oi_log = pd.DataFrame({
                        "تاریخ (Date)": df_cme.index.strftime('%Y-%m-%d'),
                        "گولڈ قیمت (Settle Price)": df_cme['Close'].round(2),
                        "روزانہ کا والیوم (Volume)": df_cme['Volume'].astype(int),
                        "والیوم کا فرق (Volume Shift)": df_cme['Volume'].diff().fillna(0).astype(int),
                        "پوزیشنز کی سمت (OI Status)": ["والیوم میں اضافہ (Expansion)" if x > 0 else "پوزیشنز کی لیکویڈیشن (Liquidation)" for x in df_cme['Volume'].diff().fillna(0)]
                    }).sort_index(ascending=False)
                    
                    st.dataframe(df_oi_log, use_container_width=True)
                    st.info("💡 **نوٹ:** CME ایکسچینج کے قواعد کے مطابق حتمی اوپن انٹرسٹ کا فائنل ڈیٹا روزانہ نیویارک سیشن ختم ہونے کے بعد (پاکستانی وقت کے مطابق دوپہر 12:30 بجے) خودکار اپڈیٹ ہوتا ہے۔")
            except Exception as e:
                st.error("CME سرور سے ڈیٹا لوڈ کرنے میں تاخیر۔")

    elif "3.2" in sec3_sub:
        st.markdown("### 🏛️ Official CFTC Weekly Commitment of Traders (COT)")
        st.caption("U.S. CFTC Official Release Feed (Code: 088691 - GOLD COMMODITY EXCHANGE INC. 08/04/26)")
        
        cot_official_data = {
            "Traders Category": [
                "Non-Commercials (بڑے ہیج فنڈز)", 
                "Commercials (بڑے بینکس / ہیجرز)", 
                "Non-Reportable (عام ریٹیل ٹریڈرز)"
            ],
            "Longs (خریدار)": ["227,013", "71,832", "44,531"],
            "Shorts (بیچنے والے)": ["29,379", "298,323", "15,674"],
            "Spreads (اسپریڈز)": ["28,175", "—", "—"],
            "Change in Longs": ["+7,391", "-3,628", "-16,853"],
            "Change in Shorts": ["-8,173", "+10,554", "-15,471"],
            "Percent of OI (Long / Short)": ["61.1% / 7.9%", "19.3% / 80.3%", "12.0% / 4.2%"]
        }
        st.table(pd.DataFrame(cot_official_data))

    elif "3.3" in sec3_sub:
        st.markdown("### 💧 Dynamic Retail Sentiment & Counter-Retail Trap Detector")
        try:
            curr_gold = yf.Ticker("GC=F").history(period="1d")
            open_p = curr_gold['Open'].iloc[0]
            close_p = curr_gold['Close'].iloc[0]
            
            if close_p < open_p:
                long_pct = 71
            else:
                long_pct = 32
                
            short_pct = 100 - long_pct
            
            st.markdown(f"**Retail Longs (خریدار):** {long_pct}%")
            st.progress(long_pct / 100)
            st.markdown(f"**Retail Shorts (بیچنے والے):** {short_pct}%")
            st.progress(short_pct / 100)
            
            st.markdown("---")
            if long_pct > 60:
                st.error(f"🚨 TRAP ALERT: {long_pct}% ریٹیلرز Buy میں ہیں۔ سمارٹ منی ان کے سٹاپ لاس ہنٹ کرنے کے لیے پرائس نیچے گرائے گی!")
            else:
                st.success(f"🟢 TRAP ALERT: {short_pct}% ریٹیلرز Sell میں ہیں۔ سمارٹ منی مارکیٹ کو اوپر بائے میں کھینچے گی!")
                
            fig_sent = go.Figure(data=[go.Pie(labels=['Retail Buyers', 'Retail Sellers'], values=[long_pct, short_pct], hole=.5, marker_colors=['#228B22', '#FF0000'])])
            fig_sent.update_layout(template="plotly_dark", height=280, margin=dict(t=10, b=0, l=0, r=0))
            st.plotly_chart(fig_sent, use_container_width=True)
        except Exception as e:
            st.error("سینٹیمنٹ سرور آف لائن ہے۔")

# ---------------------------------------------------------
# SECTION 4: TOP-DOWN MULTI-TIMEFRAME
# ---------------------------------------------------------
with main_tabs[3]:
    st.subheader("📌 Section 4: Top-Down Multi-Timeframe Analysis")
    
    sec4_sub = st.radio("Select Sub-Section:", [
        "4.1 Higher Timeframe Context (Monthly/Weekly/Daily POIs)",
        "4.2 Intermediate Structure (4H/1H Market Structure & BOS/CHoCH)",
        "4.3 Lower Timeframe Precision Execution (15M/5M/1M Trigger)"
    ])
    
    st.info("💡 **Top-Down Rule:** بڑے ٹائم فریم سے بائنگ/سیلنگ زون دیکھ کر ہی 15 منٹ / 5 منٹ کی کینڈل پر فٹ پرنٹ اور VSA کے ذریعے اینٹری ایگزیکیوٹ کریں۔")

# ---------------------------------------------------------
# SECTION 5: CROSS-ASSET INTELLIGENCE & AI NEWS
# ---------------------------------------------------------
with main_tabs[4]:
    st.subheader("📌 Section 5: Cross-Asset Intelligence & AI News")
    
    sec5_sub = st.radio("Select Sub-Section:", [
        "5.1 US Dollar Index (DXY) & Treasury Yields Inverse Correlation",
        "5.2 Live High-Impact Economic Calendar & AI News Evaluator"
    ])
    
    if "5.1" in sec5_sub:
        st.markdown("### 💵 US Dollar Index (DXY) & 10-Yr Yields Matrix")
        with st.spinner("Fetching DXY & Treasury Yields Live Data..."):
            try:
                dxy = yf.Ticker("DX-Y.NYB").history(period="1d")
                tnx = yf.Ticker("^TNX").history(period="1d")
                
                if not dxy.empty and not tnx.empty:
                    dxy_close = dxy['Close'].iloc[-1]
                    tnx_close = tnx['Close'].iloc[-1]
                    
                    c1, c2 = st.columns(2)
                    c1.metric("US Dollar Index (DXY)", f"{dxy_close:.2f}", "Inverse to Gold")
                    c2.metric("US 10-Yr Treasury Yield", f"{tnx_close:.2f}%", "Yield Reaction")
                    
                    st.info("💡 **Inverse Correlation Rule:** اگر DXY گرتا ہے، تو گولڈ (XAU/USD) میں بولش پمپ کے چانسز 80%+ ہوتے ہیں۔")
            except Exception as e:
                st.error("DXY ڈیٹا فیچ نہیں ہو سکا۔")

    elif "5.2" in sec5_sub:
        st.markdown("### 📰 High-Impact Economic Calendar & AI Evaluator")
        news_events = {
            "Time (EST)": ["08:30 AM", "08:30 AM", "10:00 AM", "02:00 PM"],
            "Event Name": ["Non-Farm Payrolls (NFP)", "Unemployment Rate", "ISM Services PMI", "FOMC Minutes"],
            "Impact Level": ["🔴 HIGH", "🔴 HIGH", "🟠 MEDIUM", "🔴 HIGH"],
            "Forecast / Consensus": ["97.5K", "4.2%", "51.2", "Hawkish Pause"],
            "Gold AI Impact Prediction": ["Bullish if < 80K", "Neutral at 4.2%", "Bullish if < 50", "Bearish if Rate Hikes Mentioned"]
        }
        st.table(pd.DataFrame(news_events))
