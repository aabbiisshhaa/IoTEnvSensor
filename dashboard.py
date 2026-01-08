import streamlit as st
import pandas as pd
import plotly.express as px
import plotly.graph_objects as go
import os
import time
import platform
from datetime import datetime

# --- IMPORT UTILS ---
from utils.styles import apply_styles, therm_icon, hum_icon, batt_icon, sig_icon, time_icon, motion_icon
from utils.data import load_data_from_s3, load_data_from_csv
from utils.ml import run_ml_prediction, check_api_health

if platform.system() == "Windows":
    # dot.exe path
    os.environ["PATH"] += os.pathsep + r'C:\Program Files\Graphviz\bin'

import shutil
print(shutil.which("dot")) 
# This should print the path to dot.exe. If it prints 'None', it's still not on the path.

import warnings
warnings.filterwarnings("ignore", category=UserWarning)
warnings.filterwarnings("ignore", category=FutureWarning)

# --- SETTINGS & STYLING ---
st.set_page_config(page_title="Group C: Environment Sensor Dashboard", page_icon="🌡️", layout="wide", initial_sidebar_state="expanded")

apply_styles()

    
# --- MAIN DASHBOARD LOGIC ---
def main():
    
    st.markdown("<h1 style='color:#2e7d32;'>🌱 IoT Environmental Monitoring Dashboard</h1>", unsafe_allow_html=True) 
    st.markdown("Real-time telemetry with AI-powered insights.")
    
    # Automatically refresh the dashboard every 10 minutes (600 seconds)
    st.empty() 
    if "last_refresh" not in st.session_state:
        st.session_state.last_refresh = time.time()
    
    # This keeps the app updated without a full page reload
    st.cache_data.clear() # Optional: clears cache to ensure fresh S3 data

    # 1. First, try to get data from AWS S3
    df = load_data_from_s3()

    # 2. If S3 is empty, try to load the local file as a backup
    if df.empty:
        st.info("No cloud data found. Loading local CSV backup...")
        df = load_data_from_csv("sensor_ml_data.csv")
        
    # 3. If BOTH are still empty, stop and show the error
    if df.empty:
        st.error("⚠️ No telemetry data available from S3 or local CSV.")
        return    
    
    # If your CSV columns are already 'temperature_celsius', just ensure 'timestamp' exists
    if 'timestamp' not in df.columns:
        st.error("Timestamp column missing from S3 data")
        
    # 4. If we found data, show the latest reading
    latest = df.iloc[-1] 
    
    
# --- COMFORT ZONE LOGIC ---
    temp_now = latest['temperature_celsius']
    hum_now = latest['humidity_percent']

    if 20 <= temp_now <= 26 and 30 <= hum_now <= 60:
        st.success("✅ **Status: Optimal.** The environment is within the healthy comfort zone.")
    elif temp_now > 26:
        st.warning("⚠️ **Status: High Temperature.** Cooling may be required.")
    elif temp_now < 20:
        st.info("❄️ **Status: Low Temperature.** Heating may be required.")
    else:
        st.warning("💧 **Status: Humidity Alert.** Air may be too dry or too damp.")
        
    st.caption(f"Last sync: {latest['timestamp'].strftime('%Y-%m-%d %H:%M:%S')} (Uganda Time)")
    
    
# --- TOP ROW: CUSTOM CARDS ---    
    # Display latest metrics
    
    m1, m2, m3, m4, m5, m6 = st.columns(6)
    
    m1.markdown(f'<div class="card card-time">{time_icon}<span class="metric-label">Last Update</span><div class="metric-value">{latest["timestamp"].strftime("%H:%M:%S")}</div></div>', unsafe_allow_html=True)
    m2.markdown(f'<div class="card card-temp">{therm_icon}<span class="metric-label">Temp</span><div class="metric-value">{latest["temperature_celsius"]:.1f}°C</div></div>', unsafe_allow_html=True)
    m3.markdown(f'<div class="card card-hum">{hum_icon}<span class="metric-label">Humidity</span><div class="metric-value">{latest["humidity_percent"]:.1f}%</div></div>', unsafe_allow_html=True)
    m4.markdown(f'<div class="card card-battery">{batt_icon}<span class="metric-label">Battery</span><div class="metric-value">{latest.get("battery_voltage",0):.2f}V</div></div>', unsafe_allow_html=True)
    m5.markdown(f'<div class="card card-motion">{motion_icon}<span class="metric-label">Motion</span><div class="metric-value">{latest.get("motion_counts",0)} counts</div></div>', unsafe_allow_html=True)
    m6.markdown(f'<div class="card card-signal">{sig_icon}<span class="metric-label">RSSI</span><div class="metric-value">{latest.get("rssi",-100)} dBm</div></div>', unsafe_allow_html=True)

    st.divider()
    
    
# --- VISUAL ANALYTICS ROW ---
    col_gauge, col_trend = st.columns([1, 1])

    with col_gauge:
        # --- TEMPERATURE GAUGE ---
        fig_gauge = go.Figure(go.Indicator(
            mode = "gauge+number",
            value = latest['temperature_celsius'],
            title = {'text': "Current Temperature (°C)"},
            gauge = {
                'axis': {'range': [None, 50]},
                'bar': {'color': "#2e7d32"},
                'steps': [
                    {'range': [0, 20], 'color': "#a5d6a7"},
                    {'range': [20, 30], 'color': "#fff59d"},
                    {'range': [30, 50], 'color': "#ef9a9a"}
                ],
                'threshold': {
                    'line': {'color': "red", 'width': 4},
                    'thickness': 0.75,
                    'value': 35
                }
            }
        ))
        fig_gauge.update_layout(height=350, margin=dict(l=20, r=20, t=50, b=20))
        st.plotly_chart(fig_gauge, width="stretch", key="temp_gauge")

    with col_trend:
        # --- LINE CHART ---
        st.markdown("### 📈 Temperature Trend")
        # Setting height to match the gauge
        st.line_chart(df.set_index('timestamp')['temperature_celsius'], height=350)  
        
    st.divider()


# --MIDDLE ROW: AI PREDICTION ---
    st.markdown("🔮 AI Temperature Forecast")
    st.info("The AI service analyzes rolling averages and temporal lags to forecast trends.")
    
    if st.button("🎯 Run AI Prediction", type="primary"):
        with st.spinner("Waking up prediction service..."):
            time.sleep(2) # Simulating API call
            result = run_ml_prediction(df)
            
            if result and result.get('success'):
                pred = result['prediction']['temperature_celsius']
                current = latest['temperature_celsius']
                diff = pred - current
                
                pc1, pc2, pc3 = st.columns(3)
                pc1.metric("Predicted Temp", f"{pred:.2f} °C", f"{diff:+.2f} °C")
                pc2.metric("Confidence (MAE)", result['prediction'].get('confidence', 'N/A'))
                pc3.write("📝 **Analysis:**" + (" Rising trend" if diff > 0.1 else " Falling trend" if diff < -0.1 else " Stable"))
            else:
                st.error("Prediction service timed out. Please try again in 15 seconds.")                    


# ---TRENDS ---
    st.markdown("## 📊 Trends")
    tab_motion, tab_signal, tab_battery, tab_corr = st.tabs(["🏃 Motion", "📶 Signal", "🔋 Battery", "🔍 Insights & Correlations"])
    with tab_motion:
        fig_motion = px.line(
            df,
            x="timestamp",
            y="motion_counts",
            title="Motion Activity Over Time"
        )
        st.plotly_chart(fig_motion, width="stretch", key="motion_trend")

    with tab_signal:
        fig_signal = px.line(
            df,
            x="timestamp",
            y="rssi",
            title="Signal Strength Over Time"
        )
        st.plotly_chart(fig_signal, width="stretch", key="signal_trend")

    with tab_battery:
        fig_battery = px.line(
            df,
            x="timestamp",
            y="battery_voltage",
            title="Battery Voltage Over Time"
        )
        st.plotly_chart(fig_battery, width="stretch", key="battery_trend")
        
    with tab_corr:

        fig_hist = px.histogram(df, x="temperature_celsius", title="Temperature Distribution")
        st.plotly_chart(fig_hist, width="stretch", key="temp_histogram")

        corr_cols = [
            "temperature_celsius",
            "humidity_percent",
            "battery_voltage",
            "motion_counts",
            "rssi"
        ]

        corr = df[corr_cols].corr()

        fig_corr = go.Figure(
            data=go.Heatmap(
                z=corr.values,
                x=corr.columns,
                y=corr.columns,
                colorscale="RdBu",
                zmid=0
            )
        )

        fig_corr.update_layout(title="Telemetry Correlation Matrix")

        st.plotly_chart(fig_corr, width="stretch", key="corr_heatmap")

        st.caption(f"Last sync: {datetime.now().strftime('%H:%M:%S')} | Total records: {len(df)}")
  
    
# --- BOTTOM TABS FOR STATISTICS ---
    st.divider()
    tab1, tab2, tab3, tab4 = st.tabs(["📈 Analysis", "🤖 AI Forecast", "📂 Raw Data", "🧩 System Architecture"])
    
    with tab1:
        col_lett, col_right = st.columns(2)
        with col_lett:
            fig_temp = px.line(df, x="timestamp", y="temperature_celsius", title="Temperature Over Time", markers=True)
            st.plotly_chart(fig_temp, width="stretch", key="temp_trend")
        with col_right:
            fig_hum = px.area(df, x="timestamp", y="humidity_percent", title="Humidity Levels Over Time", color_discrete_sequence=['#00CC96'])
            st.plotly_chart(fig_hum, width="stretch", key="hum_trend")
            
        fig_combined = px.line(df, x="timestamp", y=["temperature_celsius", "humidity_percent"], title="Temperature & Humidity Combined")

        st.plotly_chart(fig_combined, width="stretch", key="temp_humidity_chart")

    with tab2:
        st.subheader("🤖 Machine Learning Inference")
        pred_val = run_ml_prediction(df)
        if pred_val:
            c1, c2 = st.columns(2)
            c1.metric("Ridge Predicted Next Temp", f"{pred_val}°C")
            c2.write("The model utilizes **Ridge Regression** to analyze temporal patterns.")
            
            # Use the correct column name 'temperature_celsius' for the plot
            df_plot = df.sort_values("timestamp").tail(20) 
            st.line_chart(df_plot.set_index('timestamp')['temperature_celsius'])
        else:
            st.warning("Collecting more telemetry data for model training (Need at least 5 records)...")        

    with tab3:
        st.subheader("📂 Historical Data Archive")
        st.dataframe(df, width="stretch")
        # Data Export (Group I Feature)
        csv = df.to_csv(index=False).encode('utf-8')
        st.download_button("📥 Export CSV Data", data=csv, file_name="environmental_logs.csv", mime="text/csv")
        st.dataframe(df, width="stretch")
               
    with tab4:
        st.subheader("🧩 High-Level Data Flow")
        st.markdown("""
        1. **End Device:** LHT65N reads Temp/Hum.
        2. **Gateway:** LG308N forwards to TTN.
        3. **Cloud Bridge:** TTN Storage API stores JSON packets.
        4. **Analytics:** Streamlit applies Ridge Regression for prediction.
        """)   

        # System Architecture Diagram

        st.graphviz_chart('''
        digraph G {
            rankdir=LR;
            node [shape=box, style=filled, color=lightblue, fontname="Helvetica"];
            
            subgraph cluster_0 {
                label = "Edge Sensing Layer";
                color=lightgrey;
                style=filled;
                LHT65N [label="LHT65N Sensor"];
                LG308N [label="LG308N Gateway"];
            }

            subgraph cluster_1 {
                label = "Cloud Orchestration";
                color=lightyellow;
                style=filled;
                TTN [label="The Things Network", shape=cloud];
                Lambda [label="AWS Lambda (Ingestion)"];
                EventBridge [label="AWS EventBridge", shape=circle];
            }

            subgraph cluster_2 {
                label = "Data Lake & Storage";
                color=lightgreen;
                style=filled;
                S3 [label="Amazon S3 (Data Lake)", shape=folder];
                ThingSpeak [label="ThingSpeak", shape=database];
            }

            subgraph cluster_3 {
                label = "Application & Analytics";
                color=lavender;
                style=filled;
                Streamlit [label="Streamlit Dashboard", shape=window];
                ML_Model [label="Ridge Regression (ML)"];
            }

            # Data flow connections
            LHT65N -> LG308N [label="LoRaWAN"];
            LG308N -> TTN [label="HTTPS"];
            EventBridge -> Lambda [label="Trigger (12h)"];
            TTN -> Lambda [label="API Fetch"];
            Lambda -> S3 [label="Store JSON"];
            Lambda -> ThingSpeak [label="Update Fields"];
            S3 -> Streamlit [label="Fetch History"];
            ThingSpeak -> Streamlit [label="Live Feed"];
            S3 -> ML_Model;
            ML_Model -> Streamlit [label="Predictions"];
        }
        ''')
        
        st.caption("System architecture illustrating data flow from sensing to analytics.")
    
# --- SIDEBAR ---
    with st.sidebar:
        
        # ... Refresh button via the sidebar
        if st.button("🔄 Refresh"):
            st.cache_data.clear()
            st.rerun()
            
        st.header("🏗️ System Architecture")
        st.info("**Layer 1:** Dragino LHT65N (LoRaWAN)\n\n**Layer 2:** TTN Community Network\n\n**Layer 3:** Streamlit Data Engine\n\n**Layer 4:** Ridge Regression ML")
        st.divider()
        st.markdown("### 📊 Project Metrics")
        st.write(f"Total Records: {len(df)}")
        st.write(f"Operational Cost: ~$0.00/mo")
        
        days_back = st.slider("Data Window (Days)", 1, 30, 7)
        time_range = st.selectbox("Chart Filter", ["Last 6 Hours", "Last 24 Hours", "Last 7 Days", "All Data"], index=1)
            
        st.markdown("---")
        st.markdown("### 🤖 ML Status")
        health = check_api_health()
            
        if health:
            st.success("API Online")
            st.caption(f"Model: {health.get('model_type', 'Ridge Regression')} | Uptime: {health.get('uptime', 'N/A')}s")
        else:
            st.warning("API Sleeping")

            if st.button("💤 Wake Up API"):
                check_api_health()
                st.rerun()

if __name__ == "__main__":
    main()  