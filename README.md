# ELM327 OBD-II Monitor

A Python application for monitoring vehicle data using an ELM327 OBD-II adapter with a PyQt5 GUI.

## Features

- Connect to ELM327 adapters (WiFi or Bluetooth)
- Monitor real-time vehicle metrics
- Read and clear diagnostic trouble codes (DTCs)
- Save metrics to CSV files
- User-friendly interface

## Installation

### Prerequisites

- Python 3.6+
- pip package manager

### Windows

```bash
# Install dependencies
pip install -r requirements.txt
```

### Linux/MacOS

```bash
# Make the install script executable
chmod +x install.sh

# Run the installation script
./install.sh
```

## Usage

Run the application with:

```bash
python main.py
```

### Connection

1. Enter your ELM327 adapter's IP and port (e.g., `192.168.0.10:35000`) or leave blank for auto-detection
2. Click "Connect"
3. Once connected, real-time metrics will display on the interface

### Features

- **Read DTCs**: Read diagnostic trouble codes from the vehicle
- **Clear DTCs**: Clear diagnostic trouble codes (use with caution)
- **Save Metrics**: Export current metrics to a CSV file

## Supported OBD-II Commands

The application supports standard OBD-II PIDs including:

- RPM
- Vehicle Speed
- Coolant Temperature
- Engine Load
- Fuel Level
- Throttle Position
- And more, depending on vehicle support 