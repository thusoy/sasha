#!/bin/bash

set -e

# Update and upgrade, commented out for now since it's awful slow
#sudo apt-get update
#sudo apt-get upgrade -y

# Download files
git clone https://github.com/thusoy/hasas

# Install pip and requirements
sudo apt-get install python-pip -y
sudo pip install -e ./hasas

# Generate private- and public keys
sudo ./hasas/hasas_client/genkeys.sh

# Install PiFace
sudo apt-get install python-pifaced

sudo apt-get install pifacecommon

# Enable SPI module
sudo modprobe spi-bmc2708

# Start the sysinfo service
sudo service pifacecafsysinfo start

# Enable service to run at boot
sudo update-rc.d pifacecadsysinfo defaults


# Disable trigger for led0 [default is echo mmc0 >/sys/class/leds/led0/trigger]
# see http://www.raspberrypi.org/forums/viewtopic.php?f=31&t=12530
sudo sh -c "echo none >/sys/class/leds/led0/trigger"
