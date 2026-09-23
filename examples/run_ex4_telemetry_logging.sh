#!/bin/bash
# run_ex4_telemetry_logging.sh — Run Example 4 inside Docker.
#
# Prerequisites:
#   1. Simulation running:   ./run_demo.sh
#   2. ROS 2 server running: ./launch_ros2_sitl.sh

set -e
cd "$(dirname "$0")"
CONTAINER="crazyflie_sitl"

if ! docker ps --format '{{.Names}}' | grep -q "^${CONTAINER}$"; then
    echo "ERROR: Docker container '${CONTAINER}' is not running. Start ./run_demo.sh first."
    exit 1
fi

docker exec -it "${CONTAINER}" bash -c "source /ros2_ws/install/setup.bash && cd /examples && python3 /examples/ex4_telemetry_logging.py"
echo "Log saved to examples/flight_log.csv"
