import streamlit as st
import boto3
import pandas as pd
import logging
from pathlib import Path


# --- AWS credentials from Streamlit secrets ---
# BUCKET_NAME = st.secrets.get("BUCKET_NAME", "iot-amzn-bucket")
# AWS_REGION = st.secrets.get("AWS_REGION", "us-east-1")
# AWS_SECRET_ACCESS_KEY = st.secrets["AWS_SECRET_ACCESS_KEY"]
# AWS_ACCESS_KEY_ID = st.secrets["AWS_ACCESS_KEY_ID"]
    
try:
    BUCKET_NAME = st.secrets.get("BUCKET_NAME", "iot-amzn-bucket")
    AWS_REGION = st.secrets.get("AWS_REGION", "us-east-1")
    AWS_SECRET_ACCESS_KEY = st.secrets["AWS_SECRET_ACCESS_KEY"]
    AWS_ACCESS_KEY_ID = st.secrets["AWS_ACCESS_KEY_ID"]
    
    # Initialize s3
    s3 = boto3.client(
        's3',
        aws_access_key_id=st.secrets["AWS_ACCESS_KEY_ID"],
        aws_secret_access_key=st.secrets["AWS_SECRET_ACCESS_KEY"],
        region_name=AWS_REGION
    )
except Exception as e:
    st.error(f"Setup Error: {e}")
    st.stop()
    
print(f"--- 🔍 S3 Debugger Started ---")

try:
    # Test connection
    print(f"Testing connection to {BUCKET_NAME} in {AWS_REGION}...")
    s3.head_bucket(Bucket=BUCKET_NAME)
    print("✅ Connection Successful!")

    # Check for your specific file
    print(f"Looking for: sensor_ml_data.csv")
    response = s3.list_objects_v2(Bucket=BUCKET_NAME, Prefix='sensor_ml_data.csv')
    
    if 'Contents' in response:
        print(f"✅ Found File: {response['Contents'][0]['Key']}")
    else:
        print("❌ File NOT FOUND. Please upload sensor_ml_data.csv to the bucket.")

except Exception as e:
    print(f"❌ Error: {e}")
    print("💡 Tip: Ensure your IAM user has 'AmazonS3FullAccess' and your bucket name is correct.")    
    
# --- S3 DATA LOADING ENGINE ---    
@st.cache_resource
def get_s3_client():
    return boto3.client('s3', aws_access_key_id=AWS_ACCESS_KEY_ID, aws_secret_access_key=AWS_SECRET_ACCESS_KEY, region_name=AWS_REGION)

@st.cache_data(ttl=300)
def load_data_from_s3():
    s3_client = get_s3_client()
    file_key = "sensor_ml_data.csv" 
    
    try:
        # Fetch the specific CSV file
        resp = s3_client.get_object(Bucket=BUCKET_NAME, Key=file_key)
        df = pd.read_csv(resp['Body'])
        
        # Standardize column names for your dashboard
        df.columns = df.columns.str.strip().str.lower()
        
        # Handle the timestamp (Using Uganda time as per your CSV logic)
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
            
        return df.sort_values("timestamp")
    
    except Exception as e:
        logging.warning(f"S3 CSV Load failed: {e}")
        return pd.DataFrame()


# --- CSV DATA LOAD ENGINE ---   
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
    
        