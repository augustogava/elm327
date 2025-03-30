import sys
import argparse
from PyQt5.QtWidgets import (QApplication, QMainWindow, QLabel, QLineEdit, 
                             QPushButton, QComboBox, QVBoxLayout, QWidget, QMessageBox)
from PyQt5.QtCore import pyqtSignal, Qt, QTimer
import obd
import time

class MainWindow(QMainWindow):
    """Main GUI window for the OBD-II Reader application."""
    data_updated = pyqtSignal(str)  # Signal to update GUI from another thread
    
    # Default connection settings
    DEFAULT_HOST = "192.168.0.10"
    DEFAULT_PORT = "35000"
    DEFAULT_CONNECTION_STRING = f"{DEFAULT_HOST}:{DEFAULT_PORT}"
    AUTO_CONNECT = True  # Set to True to automatically connect on startup

    def __init__(self, host=None, port=None):
        super().__init__()
        self.setWindowTitle("OBD-II Reader")
        self.setGeometry(100, 100, 400, 500)

        # Set connection parameters from constructor arguments (if provided)
        # Otherwise use the default values
        self.host = host or self.DEFAULT_HOST
        self.port = port or self.DEFAULT_PORT

        # Initialize connection variables
        self.connection = None
        self.async_connection = None
        self.data_log = []  # To store metric data for potential saving

        # GUI Components
        # Connection Section
        self.host_label = QLabel("Host:")
        self.host_input = QLineEdit(self.host)
        self.port_label = QLabel("Port:")
        self.port_input = QLineEdit(self.port)
        self.connect_button = QPushButton("Connect")
        self.connect_button.clicked.connect(self.connect_to_adapter)
        self.disconnect_button = QPushButton("Disconnect")
        self.disconnect_button.clicked.connect(self.disconnect_from_adapter)
        self.disconnect_button.setEnabled(False)

        # Status and Info
        self.status_label = QLabel("Status: Disconnected")
        self.vin_label = QLabel("VIN: N/A")

        # Metrics Selection
        self.metrics_combo = QComboBox()
        self.metrics_combo.addItem("Select a metric")
        self.start_button = QPushButton("Start Monitoring")
        self.start_button.clicked.connect(self.start_monitoring)
        self.start_button.setEnabled(False)
        self.stop_button = QPushButton("Stop Monitoring")
        self.stop_button.clicked.connect(self.stop_monitoring)
        self.stop_button.setEnabled(False)

        # Data Display
        self.data_label = QLabel("Data: N/A")

        # Layout
        layout = QVBoxLayout()
        layout.addWidget(self.host_label)
        layout.addWidget(self.host_input)
        layout.addWidget(self.port_label)
        layout.addWidget(self.port_input)
        layout.addWidget(self.connect_button)
        layout.addWidget(self.disconnect_button)
        layout.addWidget(self.status_label)
        layout.addWidget(self.vin_label)
        layout.addWidget(self.metrics_combo)
        layout.addWidget(self.start_button)
        layout.addWidget(self.stop_button)
        layout.addWidget(self.data_label)
        layout.addStretch()  # Pushes content to the top

        # Set up the central widget
        container = QWidget()
        container.setLayout(layout)
        self.setCentralWidget(container)

        # Connect signal to slot for thread-safe GUI updates
        self.data_updated.connect(self.update_data_label)
        
        # Auto-connect on startup if enabled
        if self.AUTO_CONNECT:
            # Use a short timer to allow the UI to fully initialize before connecting
            QTimer.singleShot(500, self.connect_to_adapter)

    def connect_to_adapter(self):
        """Attempt to connect to the Wi-Fi ELM327 adapter."""
        host = self.host_input.text() or self.host
        port = self.port_input.text() or self.port
        connection_string = f"{host}:{port}"

        try:
            self.status_label.setText("Status: Connecting...")
            QApplication.processEvents()  # Update GUI immediately
            self.connection = obd.OBD(connection_string)
            if self.connection.is_connected():
                self.status_label.setText(f"Status: Connected to {connection_string}")
                self.connect_button.setEnabled(False)
                self.disconnect_button.setEnabled(True)
                self.start_button.setEnabled(True)

                # Retrieve VIN (if supported)
                vin_cmd = obd.commands.VIN
                if self.connection.supports(vin_cmd):
                    response = self.connection.query(vin_cmd)
                    if not response.is_null():
                        self.vin_label.setText(f"VIN: {response.value}")
                    else:
                        self.vin_label.setText("VIN: Not Available")
                
                # Populate metrics combo box with supported commands
                self.metrics_combo.clear()
                supported_cmds = [cmd for cmd in self.connection.supported_commands if cmd.name != "VIN"]
                for cmd in supported_cmds:
                    self.metrics_combo.addItem(cmd.name)
            else:
                self.status_label.setText("Status: Connection Failed")
                QMessageBox.critical(self, "Error", f"Failed to connect to the adapter at {connection_string}.")
        except Exception as e:
            self.status_label.setText("Status: Disconnected")
            QMessageBox.critical(self, "Error", f"Connection error: {str(e)}")

    def disconnect_from_adapter(self):
        """Disconnect from the adapter and clean up."""
        if self.async_connection:
            self.async_connection.stop()
            self.async_connection = None
        if self.connection:
            self.connection.close()
            self.connection = None
        self.status_label.setText("Status: Disconnected")
        self.connect_button.setEnabled(True)
        self.disconnect_button.setEnabled(False)
        self.start_button.setEnabled(False)
        self.stop_button.setEnabled(False)
        self.vin_label.setText("VIN: N/A")
        self.data_label.setText("Data: N/A")
        self.metrics_combo.setCurrentIndex(0)

    def start_monitoring(self):
        """Start asynchronous monitoring of the selected metric."""
        if not self.connection or not self.connection.is_connected():
            QMessageBox.warning(self, "Warning", "Not connected to the adapter.")
            return

        selected_metric = self.metrics_combo.currentText()
        if selected_metric == "Select a metric" or not selected_metric:
            QMessageBox.warning(self, "Warning", "Please select a metric to monitor.")
            return

        try:
            cmd = obd.commands[selected_metric]
            self.async_connection = obd.Async(port=self.connection.port)  # Reuse existing connection port
            self.async_connection.watch(cmd, callback=self.on_data_received)
            self.async_connection.start()
            self.start_button.setEnabled(False)
            self.stop_button.setEnabled(True)
        except Exception as e:
            QMessageBox.critical(self, "Error", f"Failed to start monitoring: {str(e)}")
            self.stop_monitoring()

    def stop_monitoring(self):
        """Stop asynchronous monitoring."""
        if self.async_connection:
            self.async_connection.stop()
            self.async_connection = None
        self.start_button.setEnabled(True)
        self.stop_button.setEnabled(False)
        self.data_label.setText("Data: N/A")

    def on_data_received(self, response):
        """Callback for when new data is received."""
        if not response.is_null():
            value = str(response.value)
            timestamp = time.time()
            self.data_log.append((timestamp, value))  # Store data for potential saving
            self.data_updated.emit(value)  # Emit signal to update GUI

    def update_data_label(self, value):
        """Slot to update the data label in the main thread."""
        self.data_label.setText(f"Data: {value}")

    def closeEvent(self, event):
        """Handle window close event to clean up resources."""
        self.disconnect_from_adapter()
        event.accept()

if __name__ == "__main__":
    # Parse command line arguments
    parser = argparse.ArgumentParser(description='OBD-II Wi-Fi Adapter Connection')
    parser.add_argument('--host', help='ELM327 adapter IP address')
    parser.add_argument('--port', help='ELM327 adapter port number')
    parser.add_argument('--no-auto-connect', action='store_true', help='Disable auto-connect on startup')
    args = parser.parse_args()
    
    # Set auto-connect flag based on command line argument
    if args.no_auto_connect:
        MainWindow.AUTO_CONNECT = False
    
    app = QApplication(sys.argv)
    window = MainWindow(host=args.host, port=args.port)
    window.show()
    sys.exit(app.exec_())