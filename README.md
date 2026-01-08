# 🌡️ IoT Environmental Sensor System

A real-time monitoring and predictive analytics system using the **Dragino LHT65N** sensor and **LoRaWAN** technology.

## 🔒 Security Best Practices

This project follows strict security protocols to protect cloud credentials:

* **Credential Masking** : All sensitive keys (AWS, ThingSpeak, TTN) are managed via Streamlit's encrypted Secrets Manager.
* **Git Integrity** : A `.gitignore` file is implemented to ensure `secrets.toml` and environment files are never committed to the public repository.
* **Least Privilege** : System components access AWS services via a dedicated IAM user with restricted permissions, rather than using Root credentials.

## 🏗️ System Architecture

The data flow is orchestrated across a multi-cloud environment:

1. **Edge** : LHT65N sensors transmit data via LoRaWAN to a Dragino Gateway.
2. **Connectivity** : The Things Network (TTN) handles device management and MQTT routing.
3. **Storage (Data Lake)** : Amazon S3 stores historical JSON payloads for long-term analysis.
4. **Real-time Logging** : ThingSpeak provides an immediate data buffer for live metrics.
5. **Analytics** : A Streamlit dashboard runs a **Ridge Regression ML model** to forecast 24-hour environmental trends.

## 🚀 Setup & Installation

1. Clone the repository: `git clone https://github.com/aabbiisshhaa/IoTEnvSensor.git`
2. Install dependencies: `pip install -r requirements.txt`
3. **Local Setup** : Create a `.streamlit/secrets.toml` file with your API keys. **(Do not commit this file!)**
4. Run the dashboard: `streamlit run dashboard.py`
