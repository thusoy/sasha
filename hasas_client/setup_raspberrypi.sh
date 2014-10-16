#!/bin/bash

# Update and upgrade
sudo apt-get update
sudo apt-get upgrade -y

# Download files
git clone https://github.com/thusoy/hasas
cd hasas

# Install pip and requirements
sudo apt-get install python-pip -y
sudo pip install -r requirements.txt

# Generate private- and public keys
sudo ./client/genkeys.sh

# Install PiFace
sudo apt-get install python-pifaced

sudo apt-get install pifacecommon

# Enable SPI module
sudo modprobe spi-bmc2708

# Start the sysinfo service
sudo service pifacecafsysinfo start
# Enable service to run at boot
sudo update-rc.d pifacecadsysinfo defaults
