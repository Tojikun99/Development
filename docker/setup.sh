#!/bin/bash
set -e

echo "Installing crazyflie-lib-python from source..."
pip3 install git+https://github.com/bitcraze/crazyflie-lib-python.git

echo "Done setting up!"
