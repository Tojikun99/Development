#!/bin/bash
set -e

cd "$(dirname "$0")"

echo "================================================="
echo "   Starting Crazyswarm2 (ROS 2) SITL Server"
echo "================================================="
echo "Bridging UDP firmware sockets to ROS 2 topics..."

# Launch the ROS 2 crazyflie_server with the provided topology configurations
docker exec -it crazyflie_sitl bash -c "source /ros2_ws/install/setup.bash && ros2 launch crazyflie launch.py crazyflies_yaml_file:=/CrazySim/ros2_config/crazyflies.yaml server_yaml_file:=/CrazySim/ros2_config/server.yaml backend:=cflib"
