#!/bin/bash

echo "Installing ELM327 OBD-II application dependencies..."

# Update package lists
sudo apt-get update

# Install required system packages
sudo apt-get install -y python3-pip python3-dev bluetooth bluez

# Install Python dependencies
pip3 install -r requirements.txt

echo "Installation complete!"
echo "You can now run the application with: python3 main.py" 