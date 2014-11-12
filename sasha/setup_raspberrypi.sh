#!/bin/bash

set -e

# Update and upgrade, commented out for now since it's awful slow
#sudo apt-get update
#sudo apt-get upgrade -y

# Download files
git clone https://github.com/thusoy/sasha

# Install pip and requirements
sudo apt-get install python-pip -y
sudo pip install -e ./sasha

# Generate private- and public keys
sudo ./sasha/sasha/genkeys.sh

# Install PiFace
sudo apt-get install python-pifaced

sudo apt-get install pifacecommon

# Enable SPI module
sudo modprobe spi-bmc2708

# Start the sysinfo service
sudo service pifacecafsysinfo start

# Enable service to run at boot
sudo update-rc.d pifacecadsysinfo defaults
