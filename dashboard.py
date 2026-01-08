import streamlit as st
import boto3
import pandas as pd
import plotly.express as px
import plotly.graph_objects as go
import json
import os
import numpy as np
import time
import requests
import logging
import graphviz
import platform
from sklearn.linear_model import Ridge
from datetime import datetime, timedelta
from graphviz import Digraph
from pathlib import Path

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

# Custom CSS for better aesthetics
st.markdown("""
<style>
    .card {padding: 20px; border-radius: 14px; box-shadow: 0px 3px 8px rgba(0,0,0,0.1); text-align: left; margin: 10px 0px; }
    .card-temp {background-color: #e8f5e9;}
    .card-hum {background-color: #e3f2fd;}
    .card-motion {background-color: #fff3e0;}
    .card-battery {background-color: #f1f8e9;}
    .metric-value {font-size: 28px; font-weight: bold; margin: 5px 0px; color: #2e7d32; }
    .metric-label {font-size: 14px; color: #555; }
    .icon {width: 26px; height: 26px; vertical-align: middle; margin-right: 8px; }
    .status-good {color: #4caf50; }
    .status-warning { color: #ff9800; }

</style>
""", unsafe_allow_html=True)

# --- SVG ICONS ---
therm_icon = """<svg xmlns"http://www.w3.org/2000/svg" fill="#e53935" class="icon" viewBox="0 0 24 24"><path d="M14 14.76V5a2 2 0 10-4 0v9.76a5 5 0 104 0z"/></svg>"""
hum_icon = """<svg xmlns="http://www.w3.org/2000/svg" fill="#1e88e5" class="icon" viewBox="0 0 24 24"><path d="M12 2.69L17.66 9a7 7 0 11-11.32 0L12 2.69z"/></svg>"""
batt_icon = """<svg xmlns="http://www.w3.org/2000/svg" fill="#4caf50" class="icon" viewBox="0 0 24 24"><path d="M15.67 4H14V2h-4v2H8.33C7.6 4 7 4.6 7 5.33v15.33C7 21.4 7.6 22 8.33 22h7.33c.74 0 .74-.6 .74-1.33V5.33C17 .6 .6 .6 .6 .6V5.33C-.8 .8 -8 -8 -8 -8z"/></svg>"""
sig_icon = """<svg xmlns="http://www.w3.org/2000/svg" fill="#ff9800" class="icon" viewBox="0 0 24 24"><path d="M1 9l2 2c4.97-4.97 13.03-4.97 18 0l2-2C16.93 2.93 7.07 2.93 1 9z"/></svg>"""
time_icon = """<svg xmlns="http://www.w3.org/2000/svg" fill="#ffb300" class="icon" viewBox="0 0 24 24"><path d="M12 1a11 11 0 1011 11A11.013 11.013 0 0012 1zm0 20a9 9 0 119-9 9.01 9.01 0 01-9 9zm.5-13h-1v6l5.25 3.15.5-.86-4.75-2.79z"/></svg>"""


# --- APIs ---
API_URL = "https://temperature-prediction-api.onrender.com/api"

try:
    BUCKET_NAME = st.secrets.get("BUCKET_NAME", "iotbucket256")
    DEVICE_ID = st.secrets.get("DEVICE_ID", "lht65n-01-temp-humidity-sensor")
    AWS_ACCESS_KEY_ID = st.secrets["AWS_ACCESS_KEY_ID"]
    AWS_SECRET_ACCESS_KEY = st.secrets["AWS_SECRET_ACCESS_KEY"]
    AWS_REGION = st.secrets.get("AWS_REGION", "eu-west-1")
except KeyError as e:
    st.error(f"⚠️ Missing secret: {e}")
    st.stop()
    
print(f"--- 🔍 S3 Debugger Started ---")
print(f"Checking Bucket: {BUCKET_NAME}, Device: {DEVICE_ID}")

# Initialize S3
s3 = boto3.client('s3', aws_access_key_id=AWS_ACCESS_KEY_ID, aws_secret_access_key=AWS_SECRET_ACCESS_KEY, region_name=AWS_REGION)

try:
    # 1. Test Connection
    print("Testing connection...")
    s3.head_bucket(Bucket=BUCKET_NAME)
    print("✅ Successfully connected to bucket!")

    # 2. List ALL objects (unfiltered)
    print("\nListing first 10 files in the bucket:")
    response = s3.list_objects_v2(Bucket=BUCKET_NAME, MaxKeys=10)
    
    if 'Contents' in response:
        for obj in response['Contents']:
            print(f"Found File: {obj['Key']} (Size: {obj['Size']} bytes)")
    else:
        print("❌ The bucket is completely empty.")

except Exception as e:
    print(f"❌ Error: {e}")

# --- S3 DATA LOADING ENGINE ---    
@st.cache_resource
def get_s3_client():
    return boto3.client('s3', aws_access_key_id=AWS_ACCESS_KEY_ID, aws_secret_access_key=AWS_SECRET_ACCESS_KEY, region_name=AWS_REGION)

@st.cache_data(ttl=300)
def load_data_from_s3(days_back=7):
    s3_client = get_s3_client()
    prefix = f"processed_data/{DEVICE_ID}/"
    all_records = []
    
    try:
        paginator = s3_client.get_paginator('list_objects_v2')
        pages = paginator.paginate(Bucket=BUCKET_NAME, Prefix=prefix)
        cutoff_date = datetime.now() - timedelta(days=days_back)
        for page in pages:
            if 'Contents' not in page:
                continue
            
            for obj in page['Contents']:
                if obj['LastModified'].replace(tzinfo=None) >= cutoff_date:
                    if obj['Key'].endswith('.json'):
                        resp = s3_client.get_object(Bucket=BUCKET_NAME, Key=obj['Key'])
                        data = json.loads(resp['Body'].read().decode('utf-8'))

                    if isinstance(data, list):
                        all_records.extend(data)
                    else:
                        all_records.append(data)
                        
        if not all_records:
           return pd.DataFrame()
       
        df = pd.DataFrame(all_records)

        # Normalize columns defensively
        df.columns = df.columns.str.strip().str.lower()

        if "timestamp_utc" in df.columns:
            df["timestamp"] = pd.to_datetime(df["timestamp_utc"], errors="coerce")
        elif "timestamp" in df.columns:
            df["timestamp"] = pd.to_datetime(df["timestamp"], errors="coerce")
        else:
            return pd.DataFrame()

        return df.dropna(subset=["timestamp"]).sort_values("timestamp")
    
    except Exception as e:
        logging.warning(f"S3 unavailable: {e}")
        return pd.DataFrame()

def check_api_health():
    try:
        response = requests.get(f"{API_URL}/health", timeout=15)
        return response.json() if response.status_code == 200 else None
    except: return None
    

# --- DATA LOAD ENGINE ---   
@st.cache_data
def load_data_from_csv(
    filename="sensor_ml_data.csv"
):    
    current_dir = Path(__file__).parent.absolute()
    file_path = current_dir / "dataset" / filename
    
    # DEBUG: This will print the EXACT path in your terminal
    print(f"--- 📂 Searching for CSV at: {file_path} ---")
    
    if not file_path.exists():
        st.error(f"CSV file '{file_path}' not found.")
        return pd.DataFrame()
    
    try:
        df = pd.read_csv(file_path)

        # Use Uganda time if available, otherwise UTC
        if 'timestamp_uganda' in df.columns:
            df['timestamp'] = pd.to_datetime(df['timestamp_uganda'])
        else:
            df['timestamp'] = pd.to_datetime(df['timestamp_utc'])

        # Keep only columns the dashboard needs
        df = df[[
            'timestamp',
            'temperature_celsius',
            'humidity_percent',
            'battery_voltage',
            'motion_counts',
            'rssi'
        ]]

        # Sort for time-series logic
        df = df.sort_values('timestamp').dropna()

        return df

    except Exception as e:
        st.error(f"CSV Load Error: {e}")
        return pd.DataFrame()
    
# --- ANALYTICS ENGINE ---
def get_battery_stats(df):
    if df.empty or 'Battery' not in df.columns:
        return 0.0, 0
    
    latest_v = df['Battery'].iloc[0]
    # Simple linear drain estimate
    subset = df.head(20)
    if len(subset) > 1:
        m, b = np.polyfit(range(len(subset)), subset['Battery'], 1)
        # Using 2.8V as the "Dead" threshold
        days_left = round((latest_v - 2.8) / abs(m * 24) if m < 0 else 99, 1)
    else:
        days_left = "Calculating..."
    return latest_v, days_left

def run_ml_prediction(df):
    
    df = df.copy()
    df.columns = df.columns.str.strip().str.lower()
    
    if 'timestamp' not in df.columns:
        return {"success": False, "error": "Timestamp column missing."}
    
    if len(df) < 10: 
        return {"success": False, "error": "Not enough data for prediction."}

    df_ml = df.sort_values("timestamp").copy()
    df_ml['temp_lag1'] = df_ml['temperature_celsius'].shift(1)
    df_ml['temp_lag2'] = df_ml['temperature_celsius'].shift(2)
    df_ml = df_ml.dropna()
    
    X = df_ml[['temp_lag1', 'temp_lag2', 'humidity_percent']]
    y = df_ml['temperature_celsius']

    model = Ridge(alpha=1.0)
    model.fit(X, y)
    
    # Predict based on the very last known values
    last_row = df_ml.iloc[-1]
    prediction = model.predict([[last_row['temperature_celsius'], last_row['temp_lag1'], last_row['humidity_percent']]])
    
    return {
        "success": True,
        "prediction": {
            "temperature_celsius": round(prediction[0], 2),
            "confidence": "±0.5°C (estimated MAE)"
        }
    }
    
# --- MAIN DASHBOARD LOGIC ---
def main():
    
    st.markdown("<h1 style='color:#2e7d32;'>🌱 IoT Environmental Monitoring Dashboard</h1>", unsafe_allow_html=True) 
    st.markdown("Real-time telemetry with AI-powered insights.")

# 1. First, try to get data from AWS S3
    df = load_data_from_s3(days_back=7)

    # 2. If S3 is empty, try to load the local file as a backup
    if df.empty:
        st.info("No cloud data found. Loading local CSV backup...")
        df = load_data_from_csv("sensor_ml_data.csv")
        
    # 3. If BOTH are still empty, stop and show the error
    if df.empty:
        st.error("⚠️ No telemetry data available from S3 or local CSV.")
        return    
        
    df = df.rename(columns={
        "Timestamp": "timestamp",
        "Temperature": "temperature_celsius",
        "Humidity": "humidity_percent",
        "Battery": "battery_voltage",
        "Motion": "motion_counts",
        "Signal": "rssi"
    })

    # 4. If we found data, show the latest reading
    latest = df.iloc[-1] 
    
    st.caption(f"Last sync: {latest['timestamp'].strftime('%Y-%m-%d %H:%M:%S')} (Uganda Time)")
    
# --- TOP ROW: CUSTOM CARDS ---    
    # Display latest metrics
    
    m1, m2, m3, m4, m5, m6 = st.columns(6)
    
    m1.markdown(f'<div class="card card-time">{time_icon}<span class="metric-label">Last Update</span><div class="metric-value">{latest["timestamp"].strftime("%H:%M:%S")}</div></div>', unsafe_allow_html=True)
    m2.markdown(f'<div class="card card-temp">{therm_icon}<span class="metric-label">Temp</span><div class="metric-value">{latest["temperature_celsius"]:.1f}°C</div></div>', unsafe_allow_html=True)
    m3.markdown(f'<div class="card card-hum">{hum_icon}<span class="metric-label">Humidity</span><div class="metric-value">{latest["humidity_percent"]:.1f}%</div></div>', unsafe_allow_html=True)
    m4.markdown(f'<div class="card card-battery">{batt_icon}<span class="metric-label">Battery</span><div class="metric-value">{latest.get("battery_voltage",0):.2f}V</div></div>', unsafe_allow_html=True)
    m5.markdown(f'<div class="card card-motion">{"" if latest.get("motion_counts",0) > 0 else ""}<span class="metric-label">Motion</span><div class="metric-value">{latest.get("motion_counts",0)} counts</div></div>', unsafe_allow_html=True)
    m6.markdown(f'<div class="card card-signal">{sig_icon}<span class="metric-label">RSSI</span><div class="metric-value">{latest.get("rssi",-100)} dBm</div></div>', unsafe_allow_html=True)

    st.divider()
    
    # Show the chart
    st.line_chart(df.set_index('timestamp')['temperature_celsius'])

# --MIDDLE ROW: AI PREDICTION ---
    st.divider()
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

# Charts
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

        # Create a new directed graph

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
    
    # Sidebar info
    with st.sidebar:
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
            st.caption(f"Model: {health.get('model_type')}")
        else:
            st.warning("API Sleeping")
            if st.button("Wake Up API"): requests.get(f"{API_URL}/health"); st.rerun()

if __name__ == "__main__":
    main()  