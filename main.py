import sys
import time
import obd
from PyQt5.QtWidgets import (QApplication, QMainWindow, QPushButton, QLabel, 
                             QVBoxLayout, QHBoxLayout, QWidget, QComboBox, 
                             QLineEdit, QTextEdit, QGridLayout, QMessageBox)
from PyQt5.QtCore import Qt, QTimer, pyqtSlot
from PyQt5.QtGui import QFont

class OBDMonitor(QMainWindow):
    def __init__(self):
        super().__init__()
        self.connection = None
        self.connected = False
        self.metrics = {}
        self.init_ui()

    def init_ui(self):
        self.setWindowTitle('ELM327 OBD-II Monitor')
        self.setMinimumSize(800, 600)

        # Main widget and layout
        main_widget = QWidget()
        main_layout = QVBoxLayout()
        
        # Connection section
        connection_layout = QHBoxLayout()
        
        self.port_input = QLineEdit()
        self.port_input.setPlaceholderText('Enter IP:PORT (e.g., 192.168.0.10:35000)')
        
        self.connect_button = QPushButton('Connect')
        self.connect_button.clicked.connect(self.toggle_connection)
        
        connection_layout.addWidget(QLabel('OBD Connection:'))
        connection_layout.addWidget(self.port_input)
        connection_layout.addWidget(self.connect_button)
        
        # Status section
        status_layout = QHBoxLayout()
        self.status_label = QLabel('Disconnected')
        self.status_label.setStyleSheet('color: red;')
        status_layout.addWidget(QLabel('Status:'))
        status_layout.addWidget(self.status_label)
        status_layout.addStretch()
        
        # Metrics section
        metrics_layout = QGridLayout()
        
        # Create labels for common OBD metrics
        self.metric_widgets = {}
        metrics = [
            ('RPM', obd.commands.RPM),
            ('Speed', obd.commands.SPEED),
            ('Coolant Temp', obd.commands.COOLANT_TEMP),
            ('Intake Temp', obd.commands.INTAKE_TEMP),
            ('Load', obd.commands.ENGINE_LOAD),
            ('Fuel Level', obd.commands.FUEL_LEVEL),
            ('Throttle Pos', obd.commands.THROTTLE_POS),
            ('Timing Advance', obd.commands.TIMING_ADVANCE),
        ]
        
        row = 0
        col = 0
        for i, (name, command) in enumerate(metrics):
            # Create label with name
            label = QLabel(f"{name}:")
            
            # Create value label
            value = QLabel("--")
            value.setStyleSheet("font-size: 16px; font-weight: bold;")
            
            # Save reference to value label and command
            self.metric_widgets[name] = {
                'label': value,
                'command': command
            }
            
            # Add to grid
            metrics_layout.addWidget(label, row, col * 2)
            metrics_layout.addWidget(value, row, col * 2 + 1)
            
            # Update grid position
            col += 1
            if col > 1:  # 2 columns of metrics
                col = 0
                row += 1
        
        # Console output
        self.console = QTextEdit()
        self.console.setReadOnly(True)
        
        # Buttons for additional actions
        actions_layout = QHBoxLayout()
        
        read_dtc_button = QPushButton('Read DTCs')
        read_dtc_button.clicked.connect(self.read_dtc)
        
        clear_dtc_button = QPushButton('Clear DTCs')
        clear_dtc_button.clicked.connect(self.clear_dtc)
        
        save_button = QPushButton('Save Metrics')
        save_button.clicked.connect(self.save_metrics)
        
        actions_layout.addWidget(read_dtc_button)
        actions_layout.addWidget(clear_dtc_button)
        actions_layout.addWidget(save_button)
        
        # Add all layouts to main layout
        main_layout.addLayout(connection_layout)
        main_layout.addLayout(status_layout)
        main_layout.addLayout(metrics_layout)
        main_layout.addWidget(QLabel('Console:'))
        main_layout.addWidget(self.console)
        main_layout.addLayout(actions_layout)
        
        # Set the main layout
        main_widget.setLayout(main_layout)
        self.setCentralWidget(main_widget)
        
        # Timer for updating values
        self.timer = QTimer()
        self.timer.timeout.connect(self.update_metrics)
        
        self.log('Application started')

    def log(self, message):
        timestamp = time.strftime("%Y-%m-%d %H:%M:%S")
        self.console.append(f"[{timestamp}] {message}")

    def toggle_connection(self):
        if self.connected:
            self.disconnect_obd()
        else:
            self.connect_obd()

    def connect_obd(self):
        try:
            port = self.port_input.text()
            
            # If no port specified, try auto-connect
            if not port:
                self.log("No port specified, attempting auto-connect...")
                self.connection = obd.OBD()
            else:
                self.log(f"Connecting to {port}...")
                self.connection = obd.OBD(port)
            
            if self.connection.status() == obd.OBDStatus.CAR_CONNECTED:
                self.connected = True
                self.connect_button.setText('Disconnect')
                self.status_label.setText('Connected')
                self.status_label.setStyleSheet('color: green;')
                self.log("Successfully connected to vehicle")
                
                # Start timer to update metrics
                self.timer.start(1000)  # Update every second
            else:
                self.log(f"Failed to connect: {self.connection.status()}")
                QMessageBox.warning(self, "Connection Error", 
                                  f"Failed to connect to OBD: {self.connection.status()}")
        except Exception as e:
            self.log(f"Error connecting: {str(e)}")
            QMessageBox.critical(self, "Connection Error", 
                               f"Error connecting to OBD: {str(e)}")

    def disconnect_obd(self):
        if self.connection:
            self.timer.stop()
            self.connection.close()
            self.connection = None
        
        self.connected = False
        self.connect_button.setText('Connect')
        self.status_label.setText('Disconnected')
        self.status_label.setStyleSheet('color: red;')
        
        # Reset all metric displays
        for metric in self.metric_widgets.values():
            metric['label'].setText('--')
        
        self.log("Disconnected from vehicle")

    def update_metrics(self):
        if not self.connected or not self.connection:
            return
        
        for name, data in self.metric_widgets.items():
            try:
                response = self.connection.query(data['command'])
                if response.is_null():
                    data['label'].setText('N/A')
                else:
                    # Store metric value
                    self.metrics[name] = response.value
                    
                    # Format and display value
                    if hasattr(response.value, 'magnitude'):
                        # Handle Pint quantities
                        data['label'].setText(f"{response.value.magnitude:.1f} {response.value.units}")
                    else:
                        data['label'].setText(str(response.value))
            except Exception as e:
                self.log(f"Error querying {name}: {str(e)}")
                data['label'].setText('ERR')

    def read_dtc(self):
        if not self.connected or not self.connection:
            QMessageBox.warning(self, "Not Connected", "Please connect to vehicle first")
            return
            
        try:
            self.log("Reading Diagnostic Trouble Codes...")
            response = self.connection.query(obd.commands.GET_DTC)
            
            if response.is_null():
                self.log("No DTCs returned")
            else:
                if not response.value:
                    self.log("No DTCs found")
                else:
                    self.log(f"Found {len(response.value)} DTCs:")
                    for code, desc in response.value:
                        self.log(f"  {code}: {desc}")
        except Exception as e:
            self.log(f"Error reading DTCs: {str(e)}")
            QMessageBox.critical(self, "DTC Error", f"Error reading DTCs: {str(e)}")

    def clear_dtc(self):
        if not self.connected or not self.connection:
            QMessageBox.warning(self, "Not Connected", "Please connect to vehicle first")
            return
            
        reply = QMessageBox.question(self, 'Clear DTCs', 
                                   'Are you sure you want to clear all DTCs?',
                                   QMessageBox.Yes | QMessageBox.No, QMessageBox.No)
        
        if reply == QMessageBox.Yes:
            try:
                self.log("Clearing DTCs...")
                response = self.connection.query(obd.commands.CLEAR_DTC)
                self.log("DTCs cleared successfully")
            except Exception as e:
                self.log(f"Error clearing DTCs: {str(e)}")
                QMessageBox.critical(self, "DTC Error", f"Error clearing DTCs: {str(e)}")

    def save_metrics(self):
        try:
            filename = f"obd_metrics_{time.strftime('%Y%m%d_%H%M%S')}.csv"
            with open(filename, 'w') as f:
                f.write("Metric,Value,Unit\n")
                for name, value in self.metrics.items():
                    if hasattr(value, 'magnitude') and hasattr(value, 'units'):
                        f.write(f"{name},{value.magnitude},{value.units}\n")
                    else:
                        f.write(f"{name},{value},\n")
            self.log(f"Metrics saved to {filename}")
            QMessageBox.information(self, "Metrics Saved", f"Metrics saved to {filename}")
        except Exception as e:
            self.log(f"Error saving metrics: {str(e)}")
            QMessageBox.critical(self, "Save Error", f"Error saving metrics: {str(e)}")

if __name__ == '__main__':
    try:
        app = QApplication(sys.argv)
        window = OBDMonitor()
        window.show()
        sys.exit(app.exec_())
    except Exception as e:
        print(f"Fatal error: {str(e)}")
        sys.exit(1) 