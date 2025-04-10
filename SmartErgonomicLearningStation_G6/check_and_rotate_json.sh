#!/bin/bash

DATA_DIR="/home/pi/Desktop/G6Final"
ARCHIVE_DIR="$DATA_DIR/ArchieveLog"
DATE_FILE="$DATA_DIR/last_log_date.txt"
TODAY=$(date +'%Y-%m-%d')

mkdir -p "$ARCHIVE_DIR"

# 如果没记日期，就写今天
#if [ ! -f "$DATE_FILE" ]; then
#    echo "$TODAY" > "$DATE_FILE"
#fi

LAST_DATE=$(cat "$DATE_FILE")

if [ "$LAST_DATE" != "$TODAY" ]; then
    echo "New date, archieve previous json file"

    mv "$DATA_DIR/motion_log.json" "$ARCHIVE_DIR/motion_log_$LAST_DATE.json"
    mv "$DATA_DIR/motion_sensor_log.json" "$ARCHIVE_DIR/motion_sensor_log_$LAST_DATE.json"

    echo "[]" > "$DATA_DIR/motion_log.json"
    echo "[]" > "$DATA_DIR/motion_sensor_log.json"

    echo "$TODAY" > "$DATE_FILE"
else
    echo "Same date, no need to archieve"
fi

