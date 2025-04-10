# Importing required libraries
from pubnub.pubnub import PubNub
from pubnub.pnconfiguration import PNConfiguration
import RPi.GPIO as GPIO
import time
import threading
import json
from datetime import datetime

# PubNub Configuration
pnconf = PNConfiguration()
pnconf.publish_key = 'pub-c-85ba3694-4855-4861-a14b-fdfcb90cf839'
pnconf.subscribe_key = 'sub-c-7c1de1d9-ea5b-451f-bb88-35ae502a81c4'
pnconf.uuid = 'userId'
pubnub = PubNub(pnconf)
channel = 'chenweisong728'

# GPIO Setup for motion sensor
GPIO.setmode(GPIO.BCM)
GPIO.setwarnings(False)
pir_pin = 19  # Motion sensor on GPIO pin 26
GPIO.setup(pir_pin, GPIO.IN)

# Global variables
last_motion_time = time.time()
no_motion_threshold = 10  # seconds before sending alert
alert_sent = False  # Flag to track if alert has been sent
last_motion_state = False  # Track the last motion state
motion_log_file = 'motion_sensor_log.json'  # File to store motion events

def load_motion_log():
    """Load existing motion log or create new one"""
    try:
        with open(motion_log_file, 'r') as f:
            data = json.load(f)
            if isinstance(data, list):
                return data
            return []
    except (FileNotFoundError, json.JSONDecodeError):
        return []

def save_motion_event(event):
    """Save motion event to JSON file"""
    log_data = load_motion_log()
    log_data.append(event)
    with open(motion_log_file, 'w') as f:
        json.dump(log_data, f, indent=4)

def check_motion():
    """Thread function to continuously check for motion"""
    global last_motion_time, alert_sent, last_motion_state
    
    while True:
        current_motion = GPIO.input(pir_pin)
        
        # Check if motion state has changed
        if current_motion != last_motion_state:
            event = {
                'timestamp': datetime.now().isoformat(),
                'status': 'motion_detected' if current_motion else 'no_motion',
                'gpio_state': current_motion
            }
            save_motion_event(event)
            last_motion_state = current_motion
            
            if current_motion:
                print("Motion detected!")
                last_motion_time = time.time()
                alert_sent = False
            else:
                print("Motion stopped")
        
        time.sleep(0.5)  # Small delay to avoid multiple detections

def monitor_no_motion():
    """Thread function to monitor for lack of motion and send alerts"""
    global last_motion_time, alert_sent
    
    while True:
        current_time = time.time()
        time_since_last_motion = current_time - last_motion_time
        
        # Check if no motion for threshold period and alert hasn't been sent
        if (time_since_last_motion >= no_motion_threshold and 
                not alert_sent):
            print(f"ALERT: No motion detected for {no_motion_threshold} seconds!")
            
            # Send alert to PubNub
            try:
                pubnub.publish().channel(channel).message({
                    'alert': 'no_motion',
                    'seconds_inactive': time_since_last_motion,
                    'timestamp': current_time,
                    'device_id': pnconf.uuid
                }).sync()
                print("Alert sent to PubNub")
                alert_sent = True  # Mark alert as sent
                
            except Exception as e:
                print(f"Failed to send alert: {e}")
        
        time.sleep(1)  # Check every second

# Start the threads
motion_thread = threading.Thread(target=check_motion, daemon=True)
alert_thread = threading.Thread(target=monitor_no_motion, daemon=True)

print("Starting motion detection system...")
motion_thread.start()
alert_thread.start()

try:
    # Keep the main thread alive
    while True:
        time.sleep(1)
except KeyboardInterrupt:
    print("Exiting program")
    GPIO.cleanup()  # Clean up GPIO on exit
