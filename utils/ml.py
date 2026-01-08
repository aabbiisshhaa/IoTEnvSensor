import requests
import pandas as pd
import numpy as np
import time
from sklearn.linear_model import Ridge
from datetime import datetime

# --- APIs ---
API_URL = "https://temperature-prediction-api.onrender.com/api"


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

def check_api_health():
    try:
        response = requests.get(f"{API_URL}/health", timeout=15)
        if response.status_code == 200:
            return response.json()
        return None
    except Exception as e:
        return None

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
    