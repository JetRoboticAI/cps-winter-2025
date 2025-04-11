import os
import time
import torch
import torch.nn as nn
import torch.nn.functional as F
from torchvision import transforms
from PIL import Image
import RPi.GPIO as GPIO
import paho.mqtt.client as mqtt
from datetime import datetime
import board
import busio
import adafruit_ads1x15.ads1115 as ADS
from adafruit_ads1x15.analog_in import AnalogIn

# ========== Setting GPIO ==========
GPIO.setmode(GPIO.BCM)
RED_LED = 17
GREEN_LED = 27

GPIO.setup(GREEN_LED, GPIO.OUT)
GPIO.setup(RED_LED, GPIO.OUT)



# ========== LED Blink ==========
def blink_led(duration=5, interval=0.5):
    end_time = time.time() + duration
    while time.time() < end_time:
        GPIO.output(GREEN_LED, GPIO.LOW)
        GPIO.output(RED_LED, GPIO.HIGH)
        time.sleep(interval)
        GPIO.output(RED_LED, GPIO.LOW)
        time.sleep(interval)
        

# ========== Model Structure ==========
def createTheNet(printtoggle=False):
    class cnnNet(nn.Module):
        def __init__(self, printtoggle):
            super().__init__()
            self.conv1 = nn.Conv2d(3, 32, kernel_size=3, stride=1, padding=1)
            self.conv2 = nn.Conv2d(32, 64, kernel_size=3, stride=1, padding=1)
            self.conv3 = nn.Conv2d(64, 128, kernel_size=3, stride=1, padding=1)
            self.pool = nn.MaxPool2d(kernel_size=2, stride=2)
            self.fc1 = nn.Linear(128 * 16 * 16, 256)
            self.out = nn.Linear(256, 2)
            self.print = printtoggle

        def forward(self, x):
            x = self.pool(F.relu(self.conv1(x)))
            x = self.pool(F.relu(self.conv2(x)))
            x = self.pool(F.relu(self.conv3(x)))
            x = x.view(x.size(0), -1)
            x = F.relu(self.fc1(x))
            x = self.out(x)
            return x

    return cnnNet(printtoggle)
def predict_image(image_path):
    img = Image.open(image_path).convert('RGB')
    img_t = transform(img).unsqueeze(0)
    with torch.no_grad():
        output = model(img_t)
        pred = torch.argmax(output, dim=1).item()
    return pred

# ========== Loading Model ==========
model = createTheNet()
model.load_state_dict(torch.load('/home/lia/Fruit/fruit_model_16000.pth', map_location=torch.device('cpu')))
model.eval()

# ========== Preprocess ==========
transform = transforms.Compose([
    transforms.Resize((128, 128)),
    transforms.ToTensor(),
])

# ========== Lable map ==========
label_map = {0: 'Fresh 🍏', 1: 'Rotten 🥴'}

# ========== Gas Sensor ==========
def try_init_ads():
    try:
        i2c = busio.I2C(board.SCL, board.SDA)
        time.sleep(1)
        ads = ADS.ADS1115(i2c)
        chan = AnalogIn(ads, ADS.P0)
        print("Successfully inited ADS1115")
        return chan
    except Exception as e:
        print(f"Fail to init ADS1115：{e}")
        return None
    
def sensegas():
    mq135_channel = None

    # init
    while mq135_channel is None:
        print("Initing MQ135 chanel...")
        mq135_channel = try_init_ads()
        time.sleep(1)

    # load data
    while True:
        try:
            voltage = mq135_channel.voltage
            if voltage >= 2:
                return True
        except Exception as e:
            print(f"Fail to get gas data：{e}")
            mq135_channel = None
            while mq135_channel is None:
                print("Reconnecting...")
                mq135_channel = try_init_ads()
                time.sleep(1)
        time.sleep(1)

def detectfruit():
    print(f"\n{datetime.now().strftime('%Y-%m-%d %H:%M:%S')} - Detecting the fruits...")
    rotten_detected = False
    captured_images = []

    for i in range(5):
        filename = f'/home/lia/Fruit/image_{i+1}.jpg'
        os.system(f'libcamera-jpeg -o {filename} -t 1000')
        captured_images.append(filename)

        pred = predict_image(filename)
        print(f'image {i+1} → {label_map[pred]}')

        if pred == 1:
            rotten_detected = True
        time.sleep(3)

    # if rotten
    if rotten_detected:
        print("Detected rotten, LED + MQTT Alert")
        blink_led(duration=5)
        timestamp = datetime.now().strftime('%Y-%m-%d %H:%M:%S')
        message = f'Rotten fruit detected! Time: {timestamp}'
        result=client.publish(MQTT_TOPIC, message)
        print(f"MQTT message sent：{message}")
        status = result.rc
        if status == 0:
            print(f"MQTT sent to topic `{MQTT_TOPIC}`：{message}")
        else:
            print(f"Fail to sent MQTT：{status}")
    else:
        print("No rotten fruit detected. Everything looks good~")

# ========== MQTT ==========

MQTT_BROKER = 'test.mosquitto.org'
MQTT_PORT = 1883  
MQTT_TOPIC = 'fruitdetection'

# init MQTT 
client = mqtt.Client()
client.connect(MQTT_BROKER, MQTT_PORT, 60)

# ========== Main ==========
check_interval = 3 * 60 * 60
last_check_time = 0

try:
    while True:
        GPIO.output(GREEN_LED, GPIO.HIGH)
        now = time.time()
        if now - last_check_time >= check_interval:
            detectfruit()
            print("Waiting for the next detection...")

        if sensegas():
            detectfruit()

except KeyboardInterrupt:
    print("The program was interrupted")

finally:
    GPIO.cleanup()
    print(" GPIO cleaned")