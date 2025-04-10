#!/bin/bash

# Default parameter is true if not provided.
if [ -z "$1" ]; then
  PARAM=true
else
  PARAM=$1
fi

# Function to clean up background processes
cleanup() {
  echo "Terminating running processes..."
  # Kill process for fileA.py if still running
  if ps -p $pid_a > /dev/null 2>&1; then
      kill $pid_a
  fi
  # Kill process for fileB.py if it was started and is still running
  if [ ! -z "$pid_b" ] && ps -p $pid_b > /dev/null 2>&1; then
      kill $pid_b
  fi
  exit 1
}

# Trap SIGINT (Ctrl+C) and SIGTERM to run the cleanup function
trap cleanup SIGINT SIGTERM

# Run gpio_control.py in background and save its PID.
echo "Starting gpio_control.py..."
python gpio_control.py &
pid_a=$!

# If PARAM is true, run motion-alert-pubnub.py in background.
if [[ "$PARAM" == "true" || "$PARAM" == "1" || "$PARAM" == "yes" ]]; then
    echo "Parameter is true. Starting motion-alert-pubnub.py concurrently..."
    python motion-alert-pubnub.py &
    pid_b=$!
else
    echo "Parameter is false. Only running gpio_control.py."
fi

# Wait for gpio_control.py to complete.
wait $pid_a

# If motion-alert-pubnub.py was started, wait for it to complete.
if [ ! -z "$pid_b" ]; then
    wait $pid_b
fi

echo "All processes completed."
