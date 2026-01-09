# 🌡️ IoT Environmental Sensor System

A real-time monitoring and predictive analytics system using the **Dragino LHT65N** sensor and **LoRaWAN** technology.

[![Streamlit App](https://static.streamlit.io/badges/streamlit_badge_black_white.svg)](https://iot-env-sensor.streamlit.app/)

## 🌟 Why I Built This

This project was designed to solve the challenge of remote environmental monitoring in areas with limited Wi-Fi connectivity. By leveraging **LoRaWAN**, the system can transmit data over long distances with minimal power consumption, while the **Streamlit** dashboard provides actionable insights through **Machine Learning**.

## 🛠️ The Tech Stack

- **Hardware:** Dragino LHT65N (Temperature, Humidity, Battery)
- **Network:** LoRaWAN via The Things Network (TTN)
- **Cloud:** AWS S3 (Data Lake for CSV storage)
- **Intelligence:** Ridge Regression (Predictive Temperature Modeling)
- **Frontend:** Streamlit & Plotly

## 🔒 Security Best Practices

This project follows strict security protocols to protect cloud credentials:

- **Credential Masking** : All sensitive keys (AWS, ThingSpeak, TTN) are managed via Streamlit's encrypted Secrets Manager.
- **Git Integrity** : A `.gitignore` file is implemented to ensure `secrets.toml` and environment files are never committed to the public repository.
- **Least Privilege** : System components access AWS services via a dedicated IAM user with restricted permissions, rather than using Root credentials.

## 🏗️ System Architecture

The data flow is orchestrated across a multi-cloud environment:

**Edge** : LHT65N sensors transmit data via LoRaWAN to a Dragino Gateway.

**Connectivity** : The Things Network (TTN) handles device management and MQTT routing.

**Storage (Data Lake)** : Amazon S3 stores historical JSON payloads for long-term analysis.

**Real-time Logging** : ThingSpeak provides an immediate data buffer for live metrics.

**Analytics** : A Streamlit dashboard runs a **Ridge Regression ML model** to forecast 24-hour environmental trends.

## 🚀 Future Roadmap

**Real-time Alerts:** Integrate Twilio or SendGrid for SMS/Email alerts when thresholds are met.

**Advanced ML:** Move from Ridge Regression to an LSTM (Long Short-Term Memory) neural network for better time-series forecasting.

**Multi-sensor Support:** Add support for soil moisture and air quality sensors.

## 🚀 Setup & Installation

1. Clone the repository: `git clone https://github.com/aabbiisshhaa/IoTEnvSensor.git`
2. Install dependencies: `pip install -r requirements.txt`
3. **Local Setup** : Create a `.streamlit/secrets.toml` file with your API keys. **(Do not commit this file!)**
4. Run the dashboard: `streamlit run dashboard.py`
