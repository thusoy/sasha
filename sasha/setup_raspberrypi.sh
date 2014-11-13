#!/bin/bash

set -e

# Check that the script was called with the correct number of arguments
if [ $# -ne 2 ]; then
    echo "Usage: sasha-setup.sh <master-url> <config-file>"
    echo
    echo "Master url should be the url to the master you want to associate with,"
    echo "config file should be the path to a config file to use."
    exit 1
fi

# Update and upgrade, commented out for now since it's awful slow
#sudo apt-get update
#sudo apt-get upgrade -y

# Download files
git clone https://github.com/thusoy/sasha

# Install pip and requirements
echo "Installing dependencies..."
sudo apt-get install -y python-pip
sudo pip install -e ./sasha

# Generate private- and public keys
sudo ./sasha/sasha/genkeys.sh

# Install PiFace
sudo apt-get install -y python-pifacecad python-pifacecommon

# Enable SPI module
sudo modprobe spi-bmc2708

# Start the sysinfo service
sudo service pifacecafsysinfo start

# Enable service to run at boot
sudo update-rc.d pifacecadsysinfo defaults

# Run bootstrapping with master
echo "Associating with master $1..."
sudo sasha $1 --setup

sudo sh -c "cat > /etc/init/sasha.conf <<EOF
description \"Sasha client daemon\"

start on (filesystem and net-device-up IFACE=lo)
stop on runlevel [!2345]

respawn

exec sasha -c $2 $1
EOF"

echo "Starting sasha service..."
sudo service sasha start
