#!/bin/bash
# ==============================================================================
# Setup Bitcraze Crazyradio PA USB udev permissions on Ubuntu/Linux
# Gives regular users and Docker permissions to access the Crazyradio USB dongle.
# ==============================================================================

set -e

RULES_FILE="/etc/udev/rules.d/99-bitcraze.rules"

echo "=========================================================================="
echo "          Setting up Bitcraze Crazyradio USB Permissions                 "
echo "=========================================================================="

echo "[1/3] Adding current user '$USER' to plugdev group..."
sudo usermod -a -G plugdev "$USER"

echo "[2/3] Writing udev rules to $RULES_FILE..."
sudo tee "$RULES_FILE" > /dev/null << 'EOF'
# Crazyradio and Crazyradio PA
SUBSYSTEM=="usb", ATTRS{idVendor}=="1915", ATTRS{idProduct}=="7777", MODE="0664", GROUP="plugdev"
# Crazyradio 2.0
SUBSYSTEM=="usb", ATTRS{idVendor}=="1915", ATTRS{idProduct}=="0141", MODE="0664", GROUP="plugdev"
# Crazyflie 2.0 / 2.1 via USB
SUBSYSTEM=="usb", ATTRS{idVendor}=="0483", ATTRS{idProduct}=="5740", MODE="0664", GROUP="plugdev"
SUBSYSTEM=="usb", ATTRS{idVendor}=="1915", ATTRS{idProduct}=="0140", MODE="0664", GROUP="plugdev"
EOF

echo "[3/3] Reloading udev rules..."
sudo udevadm control --reload-rules
sudo udevadm trigger

echo "=========================================================================="
echo "[SUCCESS] Bitcraze USB udev rules successfully installed!"
echo "If your Crazyradio PA was already plugged in, unplug and replug it now."
echo "=========================================================================="
