This project detects rotten fruits using a Raspberry Pi, a camera, and a gas sensor (MQ135), powered by a CNN image classifier and optional MQTT alerting.

Overview
fruitdetection.py: Main script. Captures images, predicts freshness, reads gas sensor data, and sends alerts via LEDs and MQTT.
addpadding.py: Preprocessing script to add random padding and background (color or image) to dataset images.
fruit_model_16000.pth: Trained PyTorch model for classifying fruits as Fresh or Rotten.
CNN_basic_raspi.ipynb: Notebook for training the CNN on Raspberry Pi-compatible settings.

Hardware Requirements
Raspberry Pi (tested on Pi 4)
Pi Camera Module
MQ135 Gas Sensor (via ADS1115 ADC)
LEDs (Red & Green)
Breadboard and wires

Detection Flow (fruitdetection.py)
Loads pre-trained model (fruit_model_16000.pth)
Waits for:
Scheduled interval (e.g., every 3 hours), or
High gas readings from MQ135 sensor
Captures 5 images using the camera
Classifies each image (Fresh or Rotten)
If any image is Rotten:
Blinks RED LED
Sends MQTT alert to topic fruitdetection