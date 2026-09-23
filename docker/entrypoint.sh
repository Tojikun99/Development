#!/bin/bash
set -e

# Source ROS 2
source /opt/ros/humble/setup.bash

# Source workspace
if [ -f "/root/crazyflie_sitl_ws/install/setup.bash" ]; then
    source /root/crazyflie_sitl_ws/install/setup.bash
fi

exec "$@"
