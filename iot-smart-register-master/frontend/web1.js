document.addEventListener('DOMContentLoaded', function () {
  // Navigation tab switching functionality
  const navButtons = document.querySelectorAll('.nav-button');
  const sections = document.querySelectorAll('.section');

  navButtons.forEach(button => {
    button.addEventListener('click', function () {
      // Remove all active states
      navButtons.forEach(btn => btn.classList.remove('active'));
      sections.forEach(section => section.classList.remove('active'));

      // Set current active state
      this.classList.add('active');
      const targetId = this.getAttribute('data-target');
      document.getElementById(targetId).classList.add('active');
    });
  });

  // ===== Environment Monitoring Initialization =====
  // Enable debug mode
  const DEBUG_MODE = false;

  // Show debug panel if debug mode is on
  if (DEBUG_MODE) {
    document.getElementById('debug-panel').style.display = 'block';
  }

  // Function to add debug entry
  function addDebugEntry(message) {
    if (!DEBUG_MODE) return;

    const debugContainer = document.getElementById('debug-container');
    const entry = document.createElement('div');
    entry.className = 'debug-entry';
    entry.innerText = `[${new Date().toLocaleTimeString()}] ${message}`;
    debugContainer.insertBefore(entry, debugContainer.firstChild);

    // Limit debug entries
    const maxDebugEntries = 20;
    if (debugContainer.children.length > maxDebugEntries) {
      debugContainer.removeChild(debugContainer.lastChild);
    }
  }

  // PubNub Configuration
  const pubnub = new PubNub({
    subscribeKey: "sub-c-600de055-e08b-4dfd-8f69-231ee45b2313",
    uuid: "dashboard-client"
  });

  // Subscribe to the channel
  pubnub.subscribe({
    channels: ["zhaox207"]
  });

  // Data storage for charts
  const maxDataPoints = 20;
  const temperatureData = {
    labels: [],
    datasets: [{
      label: 'Temperature (°C)',
      backgroundColor: 'rgba(255, 99, 132, 0.2)',
      borderColor: 'rgba(255, 99, 132, 1)',
      borderWidth: 2,
      data: [],
      tension: 0.4
    }]
  };

  const humidityData = {
    labels: [],
    datasets: [{
      label: 'Humidity (%)',
      backgroundColor: 'rgba(54, 162, 235, 0.2)',
      borderColor: 'rgba(54, 162, 235, 1)',
      borderWidth: 2,
      data: [],
      tension: 0.4
    }]
  };

  // Initialize charts
  const temperatureChart = new Chart(
    document.getElementById('temperature-chart'),
    {
      type: 'line',
      data: temperatureData,
      options: {
        responsive: true,
        plugins: {
          title: {
            display: true,
            text: 'Temperature History'
          }
        },
        scales: {
          y: {
            beginAtZero: false
          }
        }
      }
    }
  );

  const humidityChart = new Chart(
    document.getElementById('humidity-chart'),
    {
      type: 'line',
      data: humidityData,
      options: {
        responsive: true,
        plugins: {
          title: {
            display: true,
            text: 'Humidity History'
          }
        },
        scales: {
          y: {
            beginAtZero: false,
            suggestedMax: 100
          }
        }
      }
    }
  );

  // Motion detection variables
  let motionDetectionActive = false;
  let motionTimeoutId = null;
  let lastMotionTime = null;

  // Configure motion detection persistence time (in milliseconds)
  const MOTION_PERSISTENCE_DURATION = 10000; // 10 seconds

  // Helper function to determine if motion is detected
  function isMotionDetected(motionValue) {
    // Convert various motion value formats to boolean
    if (typeof motionValue === 'boolean') {
      return motionValue;
    } else if (typeof motionValue === 'number') {
      return motionValue !== 0;
    } else if (typeof motionValue === 'string') {
      return motionValue.toLowerCase() === 'true' || motionValue === '1';
    }
    return Boolean(motionValue);
  }

  // Function to update the "last detected" time display
  function updateLastDetectedTime() {
    if (!lastMotionTime) return;

    const now = new Date();
    const diffSeconds = Math.floor((now - lastMotionTime) / 1000);
    let timeAgo;

    if (diffSeconds < 60) {
      timeAgo = `${diffSeconds} seconds ago`;
    } else if (diffSeconds < 3600) {
      const minutes = Math.floor(diffSeconds / 60);
      timeAgo = `${minutes} minute${minutes !== 1 ? 's' : ''} ago`;
    } else {
      const hours = Math.floor(diffSeconds / 3600);
      timeAgo = `${hours} hour${hours !== 1 ? 's' : ''} ago`;
    }

    document.getElementById('last-detected').innerText = `Last detected: ${timeAgo}`;
  }

  // Function to add data point to chart
  function addDataPoint(chart, label, value) {
    chart.data.labels.push(label);
    chart.data.datasets[0].data.push(value);

    // Remove old data points if exceeding maximum
    if (chart.data.labels.length > maxDataPoints) {
      chart.data.labels.shift();
      chart.data.datasets[0].data.shift();
    }

    chart.update();
  }

  // Function to add log entry
  function addLogEntry(data, time) {
    const logContainer = document.getElementById('log-container');
    const entry = document.createElement('div');
    entry.className = 'log-entry';

    let message = `Temp: ${data.temperature !== null && data.temperature !== undefined ? data.temperature.toFixed(1) + '°C' : 'N/A'}, `;
    message += `Humidity: ${data.humidity !== null && data.humidity !== undefined ? data.humidity.toFixed(1) + '%' : 'N/A'}, `;
    message += `Motion: ${isMotionDetected(data.motion) ? 'Detected' : 'None'}, `;
    message += `Gas: ${data.gas ? 'Detected' : 'None'}, `;
    // message += `Vent: ${data.vent_angle !== null && data.vent_angle !== undefined ? data.vent_angle + '°' : 'N/A'}`;

    entry.innerHTML = `<span class="timestamp">[${time}]</span> ${message}`;
    logContainer.insertBefore(entry, logContainer.firstChild);

    // Limit log entries
    const maxLogEntries = 50;
    if (logContainer.children.length > maxLogEntries) {
      logContainer.removeChild(logContainer.lastChild);
    }
  }

  // ===== Servo Motor Control Initialization =====
  // Get DOM elements
  const angleDisplay = document.getElementById('angle-display');
  const angleSlider = document.getElementById('angle-slider');
  const angleInput = document.getElementById('angle-input');
  const setAngleBtn = document.getElementById('set-angle');
  const servoArm = document.getElementById('servo-arm');

  const farLeftBtn = document.getElementById('far-left');
  const leftBtn = document.getElementById('left');
  const centerBtn = document.getElementById('center');
  const rightBtn = document.getElementById('right');
  const farRightBtn = document.getElementById('far-right');

  const sweepStartInput = document.getElementById('sweep-start');
  const sweepEndInput = document.getElementById('sweep-end');
  const sweepStepInput = document.getElementById('sweep-step');
  const sweepDelayInput = document.getElementById('sweep-delay');
  const startSweepBtn = document.getElementById('start-sweep');

  const statusMessage = document.getElementById('status-message');

  // API base URL - modify according to actual situation
  const API_BASE_URL = 'http://192.168.0.104:5500';  // Please replace with your Raspberry Pi's actual IP address

  // Helper function - display status message
  function showStatus(message, isError = false) {
    if (!statusMessage) return; // Check if element exists

    statusMessage.textContent = message;
    statusMessage.style.backgroundColor = isError ? '#ffcccc' : '#eee';
    setTimeout(() => {
      statusMessage.style.backgroundColor = '#eee';
    }, 3000);
  }

  // Update servo arm visual display
  function updateServoArmVisual(angle) {
    if (!servoArm) return; // Check if element exists

    servoArm.style.transform = `rotate(${angle}deg)`;
  }

  // API - Get current angle
  function fetchCurrentAngle() {
    fetch(`${API_BASE_URL}/api/get_angle`)
      .then(response => response.json())
      .then(data => {
        if (angleDisplay) angleDisplay.textContent = data.angle;
        if (angleSlider) angleSlider.value = data.angle;
        if (angleInput) angleInput.value = data.angle;
        updateServoArmVisual(data.angle);
      })
      .catch(error => {
        console.error('Failed to get angle:', error);
        showStatus('Failed to get angle: ' + error.message, true);
      });
  }

  // Try to get the current angle
  try {
    fetchCurrentAngle();
  } catch (error) {
    console.error('Error initializing servo angle:', error);
  }

  // API - Set angle
  function setAngle(angle) {
    return fetch(`${API_BASE_URL}/api/set_angle`, {
      method: 'POST',
      headers: {
        'Content-Type': 'application/json'
      },
      body: JSON.stringify({ angle: angle })
    })
      .then(response => response.json())
      .then(data => {
        if (data.status === 'success') {
          if (angleDisplay) angleDisplay.textContent = data.angle;
          if (angleSlider) angleSlider.value = data.angle;
          if (angleInput) angleInput.value = data.angle;
          updateServoArmVisual(data.angle);
          showStatus(`Angle set to ${data.angle}°`);
        } else {
          showStatus(`Failed to set angle: ${data.message}`, true);
        }
        return data;
      })
      .catch(error => {
        console.error('Failed to set angle:', error);
        showStatus('Failed to set angle: ' + error.message, true);
        throw error;
      });
  }

  // API - Set preset position
  function setPreset(position) {
    return fetch(`${API_BASE_URL}/api/preset`, {
      method: 'POST',
      headers: {
        'Content-Type': 'application/json'
      },
      body: JSON.stringify({ position: position })
    })
      .then(response => response.json())
      .then(data => {
        if (data.status === 'success') {
          if (angleDisplay) angleDisplay.textContent = data.angle;
          if (angleSlider) angleSlider.value = data.angle;
          if (angleInput) angleInput.value = data.angle;
          updateServoArmVisual(data.angle);
          showStatus(`Moved to ${getPositionName(position)} position (${data.angle}°)`);
        } else {
          showStatus(`Failed to set preset position: ${data.message}`, true);
        }
        return data;
      })
      .catch(error => {
        console.error('Failed to set preset position:', error);
        showStatus('Failed to set preset position: ' + error.message, true);
        throw error;
      });
  }

  // API - Execute sweep
  function startSweep(startAngle, endAngle, step, delay) {
    return fetch(`${API_BASE_URL}/api/sweep`, {
      method: 'POST',
      headers: {
        'Content-Type': 'application/json'
      },
      body: JSON.stringify({
        start: startAngle,
        end: endAngle,
        step: step,
        delay: delay
      })
    })
      .then(response => response.json())
      .then(data => {
        if (data.status === 'success') {
          showStatus(`Sweep completed: ${data.start}° to ${data.end}°`);
          fetchCurrentAngle(); // Update current angle display
        } else {
          showStatus(`Sweep failed: ${data.message}`, true);
        }
        return data;
      })
      .catch(error => {
        console.error('Sweep failed:', error);
        showStatus('Sweep failed: ' + error.message, true);
        throw error;
      });
  }

  // Helper function - Get position name
  function getPositionName(position) {
    switch (position) {
      case 'far_left': return 'Far Left';
      case 'left': return 'Left';
      case 'center': return 'Center';
      case 'right': return 'Right';
      case 'far_right': return 'Far Right';
      default: return position;
    }
  }

  // Add event listeners to all the buttons and inputs
  if (angleSlider) {
    // Event listener - Slider change
    angleSlider.addEventListener('input', function () {
      if (angleInput) angleInput.value = this.value;
      if (angleDisplay) angleDisplay.textContent = this.value;
      updateServoArmVisual(parseInt(this.value));
    });

    angleSlider.addEventListener('change', function () {
      setAngle(parseInt(this.value));
    });
  }

  if (angleInput) {
    // Event listener - Input field change
    angleInput.addEventListener('change', function () {
      let value = parseInt(this.value);

      // Limit range - Modified for SG90 range (0-180)
      if (value < 0) value = 0;
      if (value > 180) value = 180;

      this.value = value;
      if (angleSlider) angleSlider.value = value;
      updateServoArmVisual(value);
    });
  }

  if (setAngleBtn) {
    // Event listener - Set button
    setAngleBtn.addEventListener('click', function () {
      if (angleInput) setAngle(parseInt(angleInput.value));
    });
  }

  // Event listener - Preset position buttons
  if (farLeftBtn) {
    farLeftBtn.addEventListener('click', function () {
      setPreset('far_left');
    });
  }

  if (leftBtn) {
    leftBtn.addEventListener('click', function () {
      setPreset('left');
    });
  }

  if (centerBtn) {
    centerBtn.addEventListener('click', function () {
      setPreset('center');
    });
  }

  if (rightBtn) {
    rightBtn.addEventListener('click', function () {
      setPreset('right');
    });
  }

  if (farRightBtn) {
    farRightBtn.addEventListener('click', function () {
      setPreset('far_right');
    });
  }

  // Event listener - Sweep button
  if (startSweepBtn) {
    startSweepBtn.addEventListener('click', function () {
      const startAngle = parseInt(sweepStartInput.value);
      const endAngle = parseInt(sweepEndInput.value);
      const step = parseInt(sweepStepInput.value);
      const delay = parseFloat(sweepDelayInput.value);

      // Input validation - Modified for SG90 range
      if (startAngle < 0 || startAngle > 180) {
        showStatus('Start angle must be between 0 and 180', true);
        return;
      }

      if (endAngle < 0 || endAngle > 180) {
        showStatus('End angle must be between 0 and 180', true);
        return;
      }

      if (step <= 0 || step > 45) {
        showStatus('Step value must be between 1 and 45', true);
        return;
      }

      if (delay < 0.01 || delay > 1) {
        showStatus('Delay must be between 0.01 and 1 seconds', true);
        return;
      }

      showStatus('Starting sweep...');
      this.disabled = true;
      this.textContent = 'Sweeping...';

      startSweep(startAngle, endAngle, step, delay)
        .finally(() => {
          this.disabled = false;
          this.textContent = 'Start Sweep';
        });
    });
  }

  // Update PubNub Listener for both monitoring and servo control
  pubnub.addListener({
    message: function (event) {
      // Update connection status
      const connectionStatus = document.getElementById('connection-status');
      if (connectionStatus) {
        connectionStatus.className = 'status connected';
        connectionStatus.innerText = 'Connected - Receiving Data';
      }

      const data = event.message;
      const timestamp = new Date();
      const timeString = timestamp.toLocaleTimeString();

      // Debug raw data
      addDebugEntry(`Received raw data: ${JSON.stringify(data)}`);

      // Update dashboard values
      if (data.temperature !== null && data.temperature !== undefined) {
        const tempElement = document.getElementById('temperature-value');
        if (tempElement) tempElement.innerText = data.temperature.toFixed(1);
      }

      if (data.humidity !== null && data.humidity !== undefined) {
        const humidityElement = document.getElementById('humidity-value');
        if (humidityElement) humidityElement.innerText = data.humidity.toFixed(1);
      }

      // Handle smoke/gas detection
      if (data.gas !== undefined) {
        const smokeValueElement = document.getElementById('smoke-value');
        const smokeStatusElement = document.getElementById('smoke-status');

        if (smokeValueElement && smokeStatusElement) {
          if (data.gas) {
            smokeValueElement.innerText = 'Warning';
            smokeValueElement.style.color = '#e74c3c';
            smokeStatusElement.innerText = 'Gas or smoke detected!';
          } else {
            smokeValueElement.innerText = 'Normal';
            smokeValueElement.style.color = '#3498db';
            smokeStatusElement.innerText = 'No gas detected';
          }
        }
      }

      // Handle motion detection with persistence
      const motionElement = document.getElementById('motion-value');
      const lastDetectedElement = document.getElementById('last-detected');

      // Debug motion value
      addDebugEntry(`Motion value: ${data.motion} (Type: ${typeof data.motion})`);

      // Check for motion detection using the helper function
      const motionDetected = isMotionDetected(data.motion);
      addDebugEntry(`Motion detected: ${motionDetected}`);

      if (motionDetected && motionElement && lastDetectedElement) {
        // Clear any existing timeout
        if (motionTimeoutId !== null) {
          clearTimeout(motionTimeoutId);
          addDebugEntry('Cleared previous motion timeout');
        }

        // Set motion to detected state
        motionElement.innerText = 'Motion Detected';
        motionElement.className = 'value motion detected';
        motionDetectionActive = true;

        // Update last detection time
        lastMotionTime = timestamp;
        lastDetectedElement.innerText = 'Last detected: Just now';
        addDebugEntry('Updated motion status to "Detected"');

        // Set timeout to clear motion after persistence duration
        motionTimeoutId = setTimeout(() => {
          motionElement.innerText = 'No Motion';
          motionElement.className = 'value motion';
          motionDetectionActive = false;
          addDebugEntry('Motion persistence timeout expired, status reset to "No Motion"');

          // Update last detection time
          updateLastDetectedTime();
        }, MOTION_PERSISTENCE_DURATION);
      }

      // Update "time ago" display for motion detection
      if (lastMotionTime !== null) {
        updateLastDetectedTime();
      }

      // Update charts
      if (data.temperature !== null && data.temperature !== undefined) {
        addDataPoint(temperatureChart, timeString, data.temperature);
      }
      if (data.humidity !== null && data.humidity !== undefined) {
        addDataPoint(humidityChart, timeString, data.humidity);
      }

      // Add log entry
      addLogEntry(data, timeString);

      // Update servo angle from PubNub data if available
      if (data.vent_angle !== undefined) {
        // Only update the servo visual and form elements when not on the control tab
        const servoControlActive = document.getElementById('servo-control');
        if (servoControlActive && !servoControlActive.classList.contains('active')) {
          updateServoArmVisual(data.vent_angle);
          if (angleDisplay) angleDisplay.textContent = data.vent_angle;
          if (angleSlider) angleSlider.value = data.vent_angle;
          if (angleInput) angleInput.value = data.vent_angle;
        }
      }
    },
    status: function (event) {
      addDebugEntry(`PubNub status: ${event.category}`);

      if (event.category === 'PNConnectedCategory') {
        addDebugEntry('Successfully connected to PubNub');
      } else if (event.category === 'PNDisconnectedCategory') {
        addDebugEntry('Disconnected from PubNub');
      } else if (event.category === 'PNNetworkIssuesCategory') {
        addDebugEntry('Network issues detected');
      }
    },
    error: function (error) {
      addDebugEntry(`PubNub error: ${error.message}`);
    }
  });

  // Handle connection status
  window.addEventListener('online', function () {
    const connectionStatus = document.getElementById('connection-status');
    if (connectionStatus) {
      connectionStatus.className = 'status';
      connectionStatus.innerText = 'Reconnecting...';
    }
    addDebugEntry('Browser online event detected');
  });

  window.addEventListener('offline', function () {
    const connectionStatus = document.getElementById('connection-status');
    if (connectionStatus) {
      connectionStatus.className = 'status disconnected';
      connectionStatus.innerText = 'Disconnected - Check your internet connection';
    }
    addDebugEntry('Browser offline event detected');
  });

  // Update last detected time every minute
  setInterval(updateLastDetectedTime, 60000);

  // Initialize debug functionality
  addDebugEntry('Page initialization complete, waiting for data');
});