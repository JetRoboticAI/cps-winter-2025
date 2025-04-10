#!/bin/bash

# 先检查是否需要归档
/home/pi/Desktop/G6Final/check_and_rotate_json.sh

DATA_DIR="/home/pi/Desktop/G6Final"
BUCKET="my-frontend-bucket-claire"
DATE=$(date +'%Y-%m-%d_%H-%M-%S')

# 上传 motion_log.json
aws s3 cp "$DATA_DIR/motion_log.json" "s3://$BUCKET/pilogs/motion_log_$DATE.json"
aws s3 cp "$DATA_DIR/motion_log.json" "s3://$BUCKET/motion_log.json"

# 上传 motion_sensor_log.json
aws s3 cp "$DATA_DIR/motion_sensor_log.json" "s3://$BUCKET/pilogs/motion_sensor_log_$DATE.json" 
aws s3 cp "$DATA_DIR/motion_sensor_log.json" "s3://$BUCKET/motion_sensor_log.json" 

