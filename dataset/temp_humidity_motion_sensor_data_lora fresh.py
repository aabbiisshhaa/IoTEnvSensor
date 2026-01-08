import paho.mqtt.client as mqtt
import json
from datetime import datetime, timedelta
import time
import os
import requests
import json


# Configuration
broker = "eu1.cloud.thethings.network"  #The MQTT Broker URL
port = 1883 # Use 1883 for unencrypted, 8883 for TLS
username = "bd-test-app2@ttn" # The TTN application ID
password = "NNSXS.NGFSXX4UXDX55XRIDQZS6LPR4OJXKIIGSZS56CQ.6O4WUAUHFUAHSTEYRWJX6DDO7TL2IBLC7EV2LS4EHWZOOEPCEUOA" # The TTN API key
device_id = "lht65n-01-temp-humidity-sensor" #The sensor

# ThingSpeak Configuration
THINGSPEAK_API_KEY = "AJNIMCCAIEK2SVEG"  # Your Write API Key
THINGSPEAK_URL = "https://api.thingspeak.com/update"

# Data filtering configuration
MIN_SEND_INTERVAL = 30  # Minimum seconds between ThingSpeak updates (ThingSpeak free limit is 15s, using 30s for safety)
TEMP_THRESHOLD = 0.5    # Only send if temperature changes by more than 0.5°C
HUMIDITY_THRESHOLD = 2  # Only send if humidity changes by more than 2%
BATTERY_THRESHOLD = 0.1 # Only send if battery voltage changes by more than 0.1V

# Global variables to track last sent values and timestamps
last_sent_data = {
    'temperature': None,
    'humidity': None,
    'battery_voltage': None,
    'motion_count': None,
    'timestamp': 0
}

retry_count = 0
max_retries = 3

# Function to check if data should be sent to ThingSpeak
def should_send_data(battery_voltage, temperature, humidity, motion_count):
    """
    Determine if data should be sent based on:
    1. Time interval (rate limiting)
    2. Significant data changes
    3. Motion detection (always send if motion detected)
    """
    global last_sent_data
    
    current_time = time.time()
    
    # Check time interval - respect ThingSpeak rate limits
    time_since_last = current_time - last_sent_data['timestamp']
    if time_since_last < MIN_SEND_INTERVAL:
        print(f"⏱️  Rate limit: {MIN_SEND_INTERVAL - time_since_last:.1f}s remaining until next allowed send")
        return False
    
    # Always send if motion is detected and it's different from last count
    if motion_count != last_sent_data['motion_count'] and motion_count > 0:
        print("🚶 Motion detected! Sending data...")
        return True
    
    # Check if we have previous data to compare
    if last_sent_data['temperature'] is None:
        print("📡 First data transmission...")
        return True
    
    # Check for significant changes
    temp_changed = abs(temperature - last_sent_data['temperature']) >= TEMP_THRESHOLD
    humidity_changed = abs(humidity - last_sent_data['humidity']) >= HUMIDITY_THRESHOLD
    battery_changed = abs(battery_voltage - last_sent_data['battery_voltage']) >= BATTERY_THRESHOLD
    
    if temp_changed or humidity_changed or battery_changed:
        reasons = []
        if temp_changed:
            reasons.append(f"temp: {last_sent_data['temperature']}°C → {temperature}°C")
        if humidity_changed:
            reasons.append(f"humidity: {last_sent_data['humidity']}% → {humidity}%")
        if battery_changed:
            reasons.append(f"battery: {last_sent_data['battery_voltage']}V → {battery_voltage}V")
        
        print(f"📊 Significant change detected: {', '.join(reasons)}")
        return True
    
    print("📊 No significant changes detected, skipping transmission")
    return False

# Function to send data to ThingSpeak
def send_to_thingspeak(battery_voltage, temperature, humidity, motion_count):
    """
    Send sensor data to ThingSpeak with retry logic
    Field mapping:
    - Field 1: Battery Voltage
    - Field 2: Temperature 
    - Field 3: Humidity
    - Field 4: Motion Count
    """
    global last_sent_data, retry_count
    
    try:
        # Prepare the data payload
        payload = {
            'api_key': THINGSPEAK_API_KEY,
            'field1': battery_voltage,
            'field2': temperature,
            'field3': humidity,
            'field4': motion_count
        }
        
        # Send POST request to ThingSpeak with timeout
        response = requests.post(THINGSPEAK_URL, data=payload, timeout=10)
        
        if response.status_code == 200:
            entry_id = response.text.strip()
            if entry_id != '0':
                print(f"✅ Data sent to ThingSpeak successfully! Entry ID: {entry_id}")
                print(f"   📊 Temp: {temperature}°C, Humidity: {humidity}%, Battery: {battery_voltage}V, Motion: {motion_count}")
                
                # Update last sent data tracking
                last_sent_data.update({
                    'temperature': temperature,
                    'humidity': humidity,
                    'battery_voltage': battery_voltage,
                    'motion_count': motion_count,
                    'timestamp': time.time()
                })
                retry_count = 0  # Reset retry count on success
                return True
            else:
                print("❌ ThingSpeak rejected the data (API key might be invalid or rate limit exceeded)")
                return False
        else:
            print(f"❌ Failed to send to ThingSpeak. Status code: {response.status_code}")
            return False
            
    except requests.exceptions.Timeout:
        print("❌ ThingSpeak request timed out")
        return False
    except requests.exceptions.ConnectionError:
        print("❌ Network connection error")
        return False
    except Exception as e:
        print(f"❌ Error sending data to ThingSpeak: {str(e)}")
        return False

#Fetch Historical Data 
def get_historical_sensor_data():
    app_id = "bd-test-app2"
    
    api_key = "NNSXS.NGFSXX4UXDX55XRIDQZS6LPR4OJXKIIGSZS56CQ.6O4WUAUHFUAHSTEYRWJX6DDO7TL2IBLC7EV2LS4EHWZOOEPCEUOA"
    url = f"https://{broker}/api/v3/as/applications/{app_id}/devices/{device_id}/packages/storage/uplink_message"

    # Set authorization header
    headers = {"Authorization": f"Bearer {api_key}"}
    params = {
        "last": "12h"  # get messages from last 12 hours. Max 48 hours. Possible values: 12m (12 minutes)
    }
    response = requests.get(url, headers=headers, params=params)
    if response.status_code == 200:
        response_text = response.text 
        #response_text is a json file containing historical sensor readings. Each top-level 'result' key is a sensor reading
        #parse the json text to extract the following Fields of interest and use them to build your Dashboard
        # Key_Name          Meaning
        # field1            Battery Voltage
        # field3            Humidity
        # field4            Motion Counts
        # field5            Temperature (in Celcius)
        # received_at       UTC (Coordinated Universal Time), Uganda is UTC+3
        
        with open("message_history.json", "w") as f: #optionally write data to file
            f.write(response.text.strip())
        # use the response.text to save data in persistent storage and use it to build your dashboard
    else:
        print("Error:", response.status_code, response.text)

get_historical_sensor_data()



#listen for instant notifications
topic = f"v3/{username}/devices/{device_id}/up"  # Topic for uplink messages automatically create by TTN for each sensor/device in your app

# Callback: When connected to broker
def on_connect(client, userdata, flags, rc):
    global retry_count
    
    if rc == 0:
        print("✅ Connected to TTN MQTT broker!")
        print(f"🔄 Subscribed to topic: {topic}")
        client.subscribe(topic)  # Subscribe to uplink topic
        retry_count = 0  # Reset retry count on successful connection
    else:
        print(f"❌ Failed to connect, return code {rc}")
        retry_count += 1
        if retry_count < max_retries:
            wait_time = min(60 * retry_count, 300)  # Exponential backoff, max 5 minutes
            print(f"🔄 Retrying connection in {wait_time} seconds... (attempt {retry_count}/{max_retries})")
            time.sleep(wait_time)
        else:
            print("❌ Max connection retries reached. Exiting...")
            exit(1)

# Callback for disconnection
def on_disconnect(client, userdata, rc):
    if rc != 0:
        print("⚠️  Unexpected disconnection from TTN MQTT broker")
        print("🔄 Will attempt to reconnect automatically...")

# Add heartbeat to monitor connection
def on_log(client, userdata, level, buf):
    if "PINGRESP" in buf:
        print(f"💓 Connection heartbeat: {datetime.now().strftime('%H:%M:%S')}")

# Graceful shutdown handler
import signal
import sys

def signal_handler(sig, frame):
    print('\n🛑 Gracefully shutting down...')
    client.disconnect()
    print('👋 Goodbye!')
    sys.exit(0)

signal.signal(signal.SIGINT, signal_handler)


# Callback: When a message is received
def on_message(client, userdata, msg):
    # print(f"Message received on topic {msg.topic}")
    
    payload = json.loads(msg.payload.decode())
    #payload contains sensor data with fields 1 to 5 as described before in get_historical_sensor_data() function
    with open("message.json", "w") as f: #optionally save data to a file
            f.write(json.dumps(payload, indent=4))
    
    # Extract the sensor data from the payload and use it for realtime notifications and building your dashboard
    try:
        # Navigate to the decoded payload in the TTN message structure
        if 'uplink_message' in payload and 'decoded_payload' in payload['uplink_message']:
            decoded_data = payload['uplink_message']['decoded_payload']
            
            # Extract sensor values based on TTN field mapping
            battery_voltage = decoded_data.get('field1', 0)  # Battery Voltage
            temperature = decoded_data.get('field5', 0)      # Temperature (in Celsius)
            humidity = decoded_data.get('field3', 0)         # Humidity
            motion_count = decoded_data.get('field4', 0)     # Motion Counts
            
            # Get timestamp
            received_at = payload.get('received_at', 'Unknown')
            
            # Print received data
            print(f"\n📡 New sensor data received at {received_at}")
            print(f"   🌡️  Temperature: {temperature}°C")
            print(f"   💧 Humidity: {humidity}%")
            print(f"   🔋 Battery: {battery_voltage}V")
            print(f"   🚶 Motion Count: {motion_count}")
            
            # Check if data should be sent to ThingSpeak
            if should_send_data(battery_voltage, temperature, humidity, motion_count):
                send_to_thingspeak(battery_voltage, temperature, humidity, motion_count)
            
        else:
            print("⚠️  No decoded payload found in the message")
            
    except Exception as e:
        print(f"❌ Error processing sensor data: {str(e)}")
        print("📄 Raw payload structure:")
        print(json.dumps(payload, indent=2))
    
          
   
    

# Set up MQTT client
client = mqtt.Client()
client.username_pw_set(username, password)
# client.tls_set()  # Use TLS for secure connection
client.on_connect = on_connect
client.on_message = on_message
client.on_disconnect = on_disconnect
client.on_log = on_log

print("🚀 Starting IoT sensor monitoring with ThingSpeak integration...")
print(f"📡 Device: {device_id}")
print(f"⏱️  Data filtering enabled (min interval: {MIN_SEND_INTERVAL}s)")
print("🔄 Press Ctrl+C to stop")

# Connect to broker and start loop
try:
    client.connect(broker, port, 60)
    client.loop_forever()
except KeyboardInterrupt:
    print("\n🛑 Script interrupted by user")
except Exception as e:
    print(f"❌ Unexpected error: {str(e)}")
finally:
    print("🔌 Disconnecting from broker...")
    client.disconnect()






