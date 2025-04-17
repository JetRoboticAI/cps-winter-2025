#!/usr/bin/env python3
# -*- coding: utf-8 -*-

'''
Integrated Raspberry Pi Sensor and Control System
Combines the following functions:
1. Temperature/humidity sensor (DHT11) reading and display on LCD 1602A
2. PIR motion detection
3. Servo motor control for air vent with remote web API (Modified for SG90 servo)
4. MQ-2 gas/smoke detection
5. Real-time data publishing to PubNub cloud

Author: Integrated from original separate files
Date: 2025-04-09 (Modified)
'''

from config import publish_key, subscribe_key, uuid, channel
import RPi.GPIO as GPIO
import time
import dht11
import socket
import json
import os
from http.server import HTTPServer, BaseHTTPRequestHandler
from urllib.parse import urlparse, parse_qs
import threading
from pubnub.pnconfiguration import PNConfiguration
from pubnub.pubnub import PubNub
from pubnub.exceptions import PubNubException

# ===== PUBNUB CONFIGURATION =====
# Use Pubnub to send and receive the data and message
pnconfig = PNConfiguration()
pnconfig.publish_key = publish_key
pnconfig.subscribe_key = subscribe_key
pnconfig.uuid = uuid
pubnub = PubNub(pnconfig)
CHANNEL = channel

# ===== PIN CONFIGURATION =====
# DHT11 temperature and humidity sensor
DHT_PIN = 4  # GPIO4

# LCD 1602A display
LCD_RS = 26  # GPIO26
LCD_E = 19   # GPIO19
LCD_D4 = 13  # GPIO13
LCD_D5 = 6   # GPIO6
LCD_D6 = 5   # GPIO5
LCD_D7 = 11  # GPIO11

# PIR motion sensor
PIR_PIN = 17  # GPIO17

# Servo motor
SERVO_PIN = 18  # GPIO18

# MQ-2 Gas sensor
MQ2_PIN = 16   # GPIO16
LED_PIN = 20   # GPIO20 for alarm LED indicator
BUZZER_PIN = 21  # GPIO21 for buzzer

# Web server port for remote control
WEB_PORT = 5500

# ===== LCD DISPLAY CONSTANTS =====
LCD_WIDTH = 16    # LCD character width
LCD_LINE_1 = 0x80 # LCD RAM address for 1st line
LCD_LINE_2 = 0xC0 # LCD RAM address for 2nd line
LCD_LINE_3 = 0x94 # LCD RAM address for 3rd line (if available)
LCD_LINE_4 = 0xD4 # LCD RAM address for 4th line (if available)
LCD_CHR = True    # Send data
LCD_CMD = False   # Send command
E_PULSE = 0.0005  # E pulse width
E_DELAY = 0.0005  # E delay

# ===== SERVO MOTOR CONSTANTS =====
# Modified for SG90 servo (0-180 degrees)
MIN_PULSE_WIDTH = 500   # Corresponds to 0 degrees 
MAX_PULSE_WIDTH = 2400  # Corresponds to 180 degrees
MID_PULSE_WIDTH = 1450  # Corresponds to 90 degrees

# Global variables
current_angle = 90  # Current servo angle
gas_detected = False  # Gas detection status
gas_detected_last_state = False  # Last gas detection state
pwm = None  # Global PWM object for servo
last_motion_time = 0  # Last time motion was detected
current_reason = "Initial state"  # Current reason for vent position
display_toggle_time = 0  # Last display toggle time
servo_position = 90  # Current servo position
last_detected_motion = False  # Last motion state
last_vent_change_time = 0  # Last time vent position was changed
motion_count = 0  # Motion detection counter

# ===== LCD DISPLAY FUNCTIONS =====
def lcd_init():
    '''Initialize LCD display'''
    # Set GPIO
    GPIO.setwarnings(False)
    GPIO.setmode(GPIO.BCM)
    GPIO.setup(LCD_E, GPIO.OUT)
    GPIO.setup(LCD_RS, GPIO.OUT)
    GPIO.setup(LCD_D4, GPIO.OUT)
    GPIO.setup(LCD_D5, GPIO.OUT)
    GPIO.setup(LCD_D6, GPIO.OUT)
    GPIO.setup(LCD_D7, GPIO.OUT)

    # Initialize display
    lcd_byte(0x33, LCD_CMD) # 110011 Initialize
    lcd_byte(0x32, LCD_CMD) # 110010 Initialize
    lcd_byte(0x06, LCD_CMD) # 000110 Cursor move direction
    lcd_byte(0x0C, LCD_CMD) # 001100 Display On, Cursor Off
    lcd_byte(0x28, LCD_CMD) # 101000 Data length, number of lines, font size
    lcd_byte(0x01, LCD_CMD) # 000001 Clear display
    time.sleep(E_DELAY)

def lcd_byte(bits, mode):
    '''Send byte to LCD'''
    # Set RS pin
    GPIO.output(LCD_RS, mode)

    # Send high 4 bits
    GPIO.output(LCD_D4, False)
    GPIO.output(LCD_D5, False)
    GPIO.output(LCD_D6, False)
    GPIO.output(LCD_D7, False)
    if bits & 0x10 == 0x10:
        GPIO.output(LCD_D4, True)
    if bits & 0x20 == 0x20:
        GPIO.output(LCD_D5, True)
    if bits & 0x40 == 0x40:
        GPIO.output(LCD_D6, True)
    if bits & 0x80 == 0x80:
        GPIO.output(LCD_D7, True)

    # Enable pulse
    lcd_toggle_enable()

    # Send low 4 bits
    GPIO.output(LCD_D4, False)
    GPIO.output(LCD_D5, False)
    GPIO.output(LCD_D6, False)
    GPIO.output(LCD_D7, False)
    if bits & 0x01 == 0x01:
        GPIO.output(LCD_D4, True)
    if bits & 0x02 == 0x02:
        GPIO.output(LCD_D5, True)
    if bits & 0x04 == 0x04:
        GPIO.output(LCD_D6, True)
    if bits & 0x08 == 0x08:
        GPIO.output(LCD_D7, True)

    # Enable pulse
    lcd_toggle_enable()

def lcd_toggle_enable():
    '''Toggle enable pulse'''
    time.sleep(E_DELAY)
    GPIO.output(LCD_E, True)
    time.sleep(E_PULSE)
    GPIO.output(LCD_E, False)
    time.sleep(E_DELAY)

def lcd_string(message, line):
    '''Send string to LCD'''
    message = message.ljust(LCD_WIDTH, " ")
    lcd_byte(line, LCD_CMD)

    for i in range(LCD_WIDTH):
        lcd_byte(ord(message[i]), LCD_CHR)

def lcd_clear():
    '''Clear LCD display'''
    lcd_byte(0x01, LCD_CMD)
    time.sleep(E_DELAY)

# ===== SERVO CONTROL FUNCTIONS =====
def servo_init():
    '''Initialize servo motor'''
    global pwm
    GPIO.setup(SERVO_PIN, GPIO.OUT)
    pwm = GPIO.PWM(SERVO_PIN, 50)  # 50Hz frequency
    pwm.start(0)
    print("Servo initialized")

def pulse_width_to_duty_cycle(pulse_width):
    '''Convert pulse width to duty cycle'''
    return pulse_width / 20000 * 100

def angle_to_duty_cycle(angle):
    '''Convert angle to duty cycle - Modified for SG90 range (0 to 180 degrees)'''
    # Limit to 0 to 180 degrees range for SG90
    if angle < 0:
        angle = 0
    elif angle > 180:
        angle = 180
    
    # Map angle to pulse width
    pulse_width = MIN_PULSE_WIDTH + (angle / 180) * (MAX_PULSE_WIDTH - MIN_PULSE_WIDTH)
    
    # Convert pulse width to duty cycle
    duty_cycle = pulse_width_to_duty_cycle(pulse_width)
    return duty_cycle

def set_angle(angle):
    '''Set servo angle - for automatic vent control'''
    global servo_position
    
    # Limit to SG90 range (0-180)
    if angle < 0:
        angle = 0
    elif angle > 180:
        angle = 180
        
    duty = angle_to_duty_cycle(angle)
    GPIO.output(SERVO_PIN, True)
    pwm.ChangeDutyCycle(duty)
    time.sleep(0.3)  # Give servo time to move
    GPIO.output(SERVO_PIN, False)
    pwm.ChangeDutyCycle(0)  # Stop pulse to prevent jitter
    
    servo_position = angle

def set_servo_angle(angle):
    '''Set servo angle - for API control'''
    global current_angle
    try:
        angle = int(angle)
        # Validate angle is within SG90 range
        if angle < 0 or angle > 180:
            return {"status": "error", "message": "Angle must be between 0 and 180 degrees for SG90 servo"}
        
        duty_cycle = angle_to_duty_cycle(angle)
        pwm.ChangeDutyCycle(duty_cycle)
        current_angle = angle
        time.sleep(0.5)  # Wait for servo to move to position
        pwm.ChangeDutyCycle(0)  # Stop PWM signal to prevent jitter
        
        return {"status": "success", "angle": angle}
    except Exception as e:
        return {"status": "error", "message": str(e)}

def set_preset_position(position):
    '''Set preset position for API control'''
    # Modified for SG90 range
    if position == 'far_left':
        angle = 0  # Changed from -100 to 0
    elif position == 'left':
        angle = 45  # Changed from 0 to 45
    elif position == 'center':
        angle = 90
    elif position == 'right':
        angle = 135  # Changed from 180 to 135
    elif position == 'far_right':
        angle = 180  # Changed from 270 to 180
    else:
        return {"status": "error", "message": "Invalid preset position"}
    
    result = set_servo_angle(angle)
    if result["status"] == "success":
        result["position"] = position
    
    return result

def sweep_servo(start_angle, end_angle, step, delay):
    '''Execute sweep motion for API control'''
    global current_angle
    try:
        start_angle = int(start_angle)
        end_angle = int(end_angle)
        step = int(step)
        delay = float(delay)
        
        # Validate angles are within SG90 range
        if start_angle < 0 or start_angle > 180 or end_angle < 0 or end_angle > 180:
            return {"status": "error", "message": "Angle must be between 0 and 180 degrees for SG90 servo"}
        
        # Determine step direction
        if start_angle <= end_angle:
            angle_range = range(start_angle, end_angle + 1, step)
        else:
            angle_range = range(start_angle, end_angle - 1, -step)
        
        # Execute sweep
        for angle in angle_range:
            duty_cycle = angle_to_duty_cycle(angle)
            pwm.ChangeDutyCycle(duty_cycle)
            current_angle = angle
            time.sleep(delay)
        
        # Stop PWM signal to prevent jitter
        pwm.ChangeDutyCycle(0)
        
        return {"status": "success", "start": start_angle, "end": end_angle}
    except Exception as e:
        return {"status": "error", "message": str(e)}

# ===== PIR MOTION SENSOR FUNCTIONS =====
def pir_init():
    '''Initialize PIR sensor'''
    GPIO.setup(PIR_PIN, GPIO.IN)
    print(f"PIR sensor initialized on GPIO{PIR_PIN}")
    
    # Wait for PIR sensor to initialize
    print("Waiting for PIR sensor to stabilize...")
    time.sleep(2)
    print("PIR sensor ready")

def check_motion():
    '''Check if motion is detected'''
    return GPIO.input(PIR_PIN)

# ===== MQ-2 GAS SENSOR FUNCTIONS =====
def mq2_init():
    '''Initialize MQ-2 gas sensor'''
    GPIO.setup(MQ2_PIN, GPIO.IN)
    
    # Setup LED and buzzer pins as output
    GPIO.setup(LED_PIN, GPIO.OUT)
    GPIO.setup(BUZZER_PIN, GPIO.OUT)
    
    print(f"MQ-2 gas sensor initialized on GPIO{MQ2_PIN}")
    print("Waiting for gas sensor to stabilize...")
    time.sleep(10)  # Give the sensor time to warm up
    print("Gas sensor ready")

def check_gas():
    '''Check if gas/smoke is detected'''
    return not GPIO.input(MQ2_PIN)  # Invert the signal based on sensor type

def callback_gas_detected(channel):
    '''Callback function for gas detection events'''
    global gas_detected
    if GPIO.input(MQ2_PIN):  # High means no gas (depends on your sensor)
        gas_detected = False
        print("No gas/smoke detected")
        # Turn off LED and buzzer
        GPIO.output(LED_PIN, GPIO.LOW)
        GPIO.output(BUZZER_PIN, GPIO.LOW)
    else:  # Low means gas detected
        gas_detected = True
        print("Gas/Smoke detected!")
        # Turn on LED and buzzer
        GPIO.output(LED_PIN, GPIO.HIGH)
        GPIO.output(BUZZER_PIN, GPIO.HIGH)

# ===== PUBNUB FUNCTIONS =====
def publish_to_pubnub(temp, humidity, motion, gas):
    '''Publish sensor data to PubNub'''
    try:
        message = {
            "temperature": temp,
            "humidity": humidity,
            "motion": motion,
            "gas": gas,
            # "vent_angle": servo_position
        }
        
        envelope = pubnub.publish().channel(CHANNEL).message(message).sync()
        if envelope.status.is_error():
            print(f"[PubNub] Error: {envelope.status.error}")
        else:
            print(f"[PubNub] Message published successfully")
    except PubNubException as e:
        print(f"[PubNub] Exception: {e}")
    except Exception as e:
        print(f"[PubNub] Unexpected error: {e}")

# ===== SMART CONTROL LOGIC =====
def decide_vent_position(temp, humidity, motion_detected, last_motion_time, current_time, gas_detected):
    '''Decide vent position based on sensor data - Modified for SG90 range'''
    # Configuration parameters
    TEMP_HIGH = 26  # High temperature threshold (Celsius)
    TEMP_LOW = 18   # Low temperature threshold (Celsius)
    HUMIDITY_HIGH = 70  # High humidity threshold (percentage)
    NO_MOTION_TIME = 600  # Time without motion to consider room empty (10 minutes = 600 seconds)
    
    # Default position: half open (90 degrees)
    position = 90
    reason = "Normal ventilation"
    
    # Gas detection takes highest priority - fully open if gas detected
    if gas_detected:
        position = 180  # Gas detected, fully open
        reason = "Gas/smoke detected!"
        return position, reason
    
    # Adjust based on temperature
    if temp > TEMP_HIGH:
        position = 180  # High temp, fully open
        reason = f"High temp ({temp}C)"
    elif temp < TEMP_LOW:
        position = 0  # Low temp, closed
        reason = f"Low temp ({temp}C)"
    
    # Adjust based on humidity (only when temperature is in normal range)
    if TEMP_LOW <= temp <= TEMP_HIGH and humidity > HUMIDITY_HIGH:
        position = 180  # High humidity, fully open
        reason = f"High humidity ({humidity}%)"
    
    # Adjust based on motion detection
    no_motion_time = current_time - last_motion_time
    if not motion_detected and no_motion_time > NO_MOTION_TIME:
        # Long time no motion - room is likely empty, open vent to refresh air
        position = 180  # Fully open for ventilation
        reason = f"No motion ({int(no_motion_time//60)}min) - ventilating"
    
    return position, reason
  
# ===== WEB SERVER FUNCTIONS =====
def get_ip_address():
    '''Get Raspberry Pi IP address'''
    s = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
    try:
        # Don't really send data, just get the routing
        s.connect(('10.255.255.255', 1))
        IP = s.getsockname()[0]
    except Exception:
        IP = '127.0.0.1'
    finally:
        s.close()
    return IP

# HTTP request handler
class ServoRequestHandler(BaseHTTPRequestHandler):
    def _set_headers(self, content_type='application/json'):
        self.send_response(200)
        self.send_header('Content-type', content_type)
        self.send_header('Access-Control-Allow-Origin', '*')  # Allow cross-origin requests
        self.send_header('Access-Control-Allow-Methods', 'GET, POST, OPTIONS')
        self.send_header('Access-Control-Allow-Headers', 'Content-Type')
        self.end_headers()
    
    def _set_error_headers(self, error_code=400):
        self.send_response(error_code)
        self.send_header('Content-type', 'application/json')
        self.send_header('Access-Control-Allow-Origin', '*')
        self.send_header('Access-Control-Allow-Methods', 'GET, POST, OPTIONS')
        self.send_header('Access-Control-Allow-Headers', 'Content-Type')
        self.end_headers()
    
    def do_GET(self):
        global current_angle, gas_detected
        parsed_path = urlparse(self.path)
        path = parsed_path.path
        
        if path == '/api/get_angle':
            self._set_headers('application/json')
            response = json.dumps({"angle": current_angle})
            self.wfile.write(response.encode())
        
        elif path == '/api/system_status':
            self._set_headers('application/json')
            # Get the latest system status
            response = json.dumps({
                "angle": current_angle,
                "gas_detected": gas_detected,
                "motion_detected": last_detected_motion,
                "vent_reason": current_reason
            })
            self.wfile.write(response.encode())
            
        else:
            self._set_error_headers(404)
            response = json.dumps({"status": "error", "message": "Resource not found"})
            self.wfile.write(response.encode())
    
    def do_POST(self):
        content_length = int(self.headers['Content-Length'])
        post_data = self.rfile.read(content_length)
        parsed_path = urlparse(self.path)
        path = parsed_path.path
        
        try:
            data = json.loads(post_data.decode())
            
            if path == '/api/set_angle':
                angle = data.get('angle', 90)
                response = set_servo_angle(angle)
                
            elif path == '/api/preset':
                position = data.get('position', 'center')
                response = set_preset_position(position)
                
            elif path == '/api/sweep':
                start_angle = data.get('start', 0)  # Changed from -100 to 0
                end_angle = data.get('end', 180)    # Changed from 270 to 180
                step = data.get('step', 10)
                delay = data.get('delay', 0.1)
                response = sweep_servo(start_angle, end_angle, step, delay)
                
            else:
                self._set_error_headers(404)
                response = {"status": "error", "message": "Unknown API endpoint"}
                
            self._set_headers('application/json')
            self.wfile.write(json.dumps(response).encode())
            
        except json.JSONDecodeError:
            self._set_error_headers(400)
            self.wfile.write(json.dumps({"status": "error", "message": "Invalid JSON data"}).encode())
    
    def do_OPTIONS(self):
        # Handle preflight requests, important for cross-origin requests
        self._set_headers()

def start_web_server():
    '''Start web server in a separate thread'''
    server_address = ('0.0.0.0', WEB_PORT) 
    httpd = HTTPServer(server_address, ServoRequestHandler)
    ip_address = get_ip_address()
    print(f"Servo motor API server started!")
    print(f"API address: http://{ip_address}:{WEB_PORT}")
    print(f"Angle range: 0° to 180° (SG90 servo)")  # Updated angle range
    print(f"Ensure the frontend page API_BASE_URL is set to: 'http://{ip_address}:{WEB_PORT}'")
    
    try:
        httpd.serve_forever()
    except Exception as e:
        print(f"Web server error: {e}")

# ===== MAIN PROGRAM =====
def main():
    global last_motion_time, current_reason, gas_detected, gas_detected_last_state
    global display_toggle_time, servo_position, last_detected_motion
    global last_vent_change_time, motion_count

    try:
        # Set GPIO mode
        GPIO.setwarnings(False)
        GPIO.setmode(GPIO.BCM)
        GPIO.cleanup()  # Clean up previous settings
        
        # Initialize LCD
        lcd_init()
        print("LCD screen initialized")
        
        # Initialize DHT11
        dht_sensor = dht11.DHT11(pin=DHT_PIN)
        print("DHT11 temperature/humidity sensor initialized")
        
        # Initialize servo
        servo_init()
        
        # Initialize PIR sensor
        pir_init()
        
        # Initialize MQ-2 gas sensor
        mq2_init()
        
        gas_detected = check_gas()
        gas_detected_last_state = gas_detected
        
        try:
            GPIO.add_event_detect(MQ2_PIN, GPIO.BOTH, callback=callback_gas_detected)
            print("MQ2 gas detection event set up successfully with BOTH edge detection")
        except RuntimeError as e:
            print(f"Failed to set up MQ2 event detection with BOTH edge: {e}")
            try:
                # 尝试RISING
                GPIO.add_event_detect(MQ2_PIN, GPIO.RISING, callback=callback_gas_detected)
                print("MQ2 gas detection event set up with RISING edge detection")
            except RuntimeError as e:
                print(f"Failed to set up MQ2 event detection with RISING edge: {e}")
                try:
                    # 尝试FALLING
                    GPIO.add_event_detect(MQ2_PIN, GPIO.FALLING, callback=callback_gas_detected)
                    print("MQ2 gas detection event set up with FALLING edge detection")
                except RuntimeError as e:
                    print(f"Failed to set up MQ2 event detection: {e}")
                    print("Will use polling for gas detection instead")
        
        # Display welcome message
        lcd_string("Smart Air System", LCD_LINE_1)
        lcd_string("Initializing...", LCD_LINE_2)
        time.sleep(2)
        
        # Initial values
        motion_count = 0
        last_motion_time = time.time()  # Initialize to current time
        servo_position = 90  # Initial servo position (half open)
        set_angle(servo_position)  # Set initial position
        last_detected_motion = False  # Last motion state
        display_toggle_time = time.time()  # Last display toggle time
        last_vent_change_time = 0  # Last vent position change time
        current_reason = "Initial state"  # Current reason for vent position
        last_pubnub_time = 0  # Last time data was published to PubNub
        last_gas_check_time = 0  # 上次检查气体的时间
        
        # Start web server in a separate thread
        web_server_thread = threading.Thread(target=start_web_server, daemon=True)
        web_server_thread.start()
        
        print("System startup complete, monitoring...")
        
        while True:
            current_time = time.time()
            time_str = time.strftime("%H:%M:%S")
            
            # 定期检查气体状态（作为事件检测的备份）
            if current_time - last_gas_check_time > 0.5:  # 每0.5秒检查一次
                # 只有在未使用事件检测时才采用轮询方式
                if not GPIO.event_detected(MQ2_PIN):
                    current_gas = check_gas()
                    if current_gas != gas_detected:
                        gas_detected = current_gas
                        if gas_detected:
                            print("Gas/Smoke detected! (polling)")
                            GPIO.output(LED_PIN, GPIO.HIGH)
                            GPIO.output(BUZZER_PIN, GPIO.HIGH)
                        else:
                            print("No gas/smoke detected (polling)")
                            GPIO.output(LED_PIN, GPIO.LOW)
                            GPIO.output(BUZZER_PIN, GPIO.LOW)
                
                last_gas_check_time = current_time
            
            # 1. Read DHT11 temperature/humidity data
            result = dht_sensor.read()
            current_second = int(time.strftime("%S"))
            # Cycle display mode every 5 seconds (0=temp/humidity, 1=PIR data, 2=vent status, 3=gas status)
            display_mode = (current_second // 5) % 4  
            
            if result.is_valid():
                temp = result.temperature
                humidity = result.humidity
                
                # Detect current motion state
                current_motion = check_motion()
                if current_motion and not last_detected_motion:
                    if current_time - last_motion_time > 1:  # Avoid consecutive triggers
                        motion_count += 1
                        print(f"[{time_str}] Motion detected! Total: {motion_count}")
                        last_motion_time = current_time
                
                # Update motion state
                last_detected_motion = current_motion
                
                # Decide vent position
                if current_time - last_vent_change_time > 10:  # Adjust vent position at most once every 10 seconds
                    new_position, reason = decide_vent_position(
                        temp, humidity, current_motion, last_motion_time, current_time, gas_detected
                    )
                    
                    # If position needs to change, control servo
                    if new_position != servo_position:
                        print(f"[{time_str}] Adjusting vent: {servo_position}° -> {new_position}° (Reason: {reason})")
                        servo_position = new_position
                        set_angle(servo_position)
                        current_reason = reason
                        last_vent_change_time = current_time
                
                # Decide what to display based on display mode
                if display_mode == 0:  # Display temperature/humidity
                    temp_str = f"Temp: {temp}C"
                    hum_str = f"Hum: {humidity}% {time_str[-5:]}"
                    
                    lcd_string(temp_str, LCD_LINE_1)
                    lcd_string(hum_str, LCD_LINE_2)
                elif display_mode == 1:  # Display PIR data
                    lcd_string("Motion Detector", LCD_LINE_1)
                    status = "ACTIVE" if current_motion else "Inactive"
                    lcd_string(f"Status: {status}", LCD_LINE_2)
                elif display_mode == 2:  # Display vent status
                    vent_status = "Off" if servo_position == 0 else "On"
                    if 0 < servo_position < 180:
                        vent_status = f"{int(servo_position/180*100)}%"
                    
                    lcd_string(f"Vent: {vent_status}", LCD_LINE_1)
                    lcd_string(f"Reason: {current_reason[:16]}", LCD_LINE_2)  # Limit to 16 characters
                else:  # Display gas sensor status
                    lcd_string("Gas Detector", LCD_LINE_1)
                    gas_status = "DANGER!" if gas_detected else "Normal"
                    lcd_string(f"Status: {gas_status}", LCD_LINE_2)
                
                print(f"[{time_str}] Temp: {temp}°C, Humidity: {humidity}%, Vent: {servo_position}°, Gas: {gas_detected}")
                
                # Publish data to PubNub every 5 seconds
                if current_time - last_pubnub_time > 5:
                    publish_to_pubnub(temp, humidity, current_motion, gas_detected)
                    last_pubnub_time = current_time
                    
            else:
                error_count = 0
                error_count += 1
                print(f"[{time_str}] Sensor read failed, attempt: {error_count}")
                
                if error_count > 5:
                    lcd_string("Sensor Error!", LCD_LINE_1)
                    lcd_string("Check Connection", LCD_LINE_2)
            
            # Pause to reduce CPU usage
            time.sleep(1)
            
    except KeyboardInterrupt:
        print("\nProgram exited")
    finally:
        lcd_string("System Shutdown", LCD_LINE_1)
        lcd_string("Goodbye!", LCD_LINE_2)
        time.sleep(1)
        
        # Clean up and close
        if 'pwm' in globals():
            pwm.stop()
        GPIO.cleanup()
        print("System shut down, GPIO cleaned up")

if __name__ == "__main__":
    # 初始化保存气体状态的变量
    gas_detected_last_state = False
    main()