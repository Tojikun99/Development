#!/bin/bash
# run_formation.sh — Run any Swarm2 formation script inside the Docker container
#
# Usage:
#   ./swarm2/run_formation.sh [script_name_or_path]
#
# Examples:
#   ./swarm2/run_formation.sh line_formation.py
#   ./swarm2/run_formation.sh circle_formation.py
#   ./swarm2/run_formation.sh v_formation.py
#   ./swarm2/run_formation.sh grid_formation.py
#   ./swarm2/run_formation.sh morph_formation.py
#   ./swarm2/run_formation.sh formation_manager.py

set -e

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PROJECT_ROOT="$(cd "${SCRIPT_DIR}/.." && pwd)"
CONTAINER="crazyflie_sitl"

TARGET_SCRIPT="$1"

if [ -z "$TARGET_SCRIPT" ]; then
    echo "=========================================================="
    echo "            Swarm2 Formation Script Runner                "
    echo "=========================================================="
    echo "Usage: ./swarm2/run_formation.sh <script_name>"
    echo ""
    echo "Available Scripts & Formations:"
    echo "  1) line_formation.py     - Linear flight with safe staggering"
    echo "  2) circle_formation.py   - Circular ring perimeter and orbit"
    echo "  3) v_formation.py        - Arrowhead / V-formation"
    echo "  4) grid_formation.py     - 2D matrix grid"
    echo "  5) morph_formation.py    - Multi-shape continuous airshow"
    echo "  6) formation_manager.py  - Interactive terminal flight controller"
    echo "  7) tools/arm_drone.py    - Arm drone motors"
    echo "  8) tools/disarm_drone.py - Disarm drone motors"
    echo "  9) tools/cf_telemetry.py - Live coordinates & battery monitor"
    echo "=========================================================="
    read -p "Select a script to run [1-9]: " CHOICE
    case "$CHOICE" in
        1) TARGET_SCRIPT="formations/line_formation.py" ;;
        2) TARGET_SCRIPT="formations/circle_formation.py" ;;
        3) TARGET_SCRIPT="formations/v_formation.py" ;;
        4) TARGET_SCRIPT="formations/grid_formation.py" ;;
        5) TARGET_SCRIPT="formations/morph_formation.py" ;;
        6) TARGET_SCRIPT="formation_manager.py" ;;
        7) TARGET_SCRIPT="tools/arm_drone.py" ;;
        8) TARGET_SCRIPT="tools/disarm_drone.py" ;;
        9) TARGET_SCRIPT="tools/cf_telemetry.py" ;;
        *) echo "Invalid choice"; exit 1 ;;
    esac
fi

# Resolve file inside /swarm2
if [[ "$TARGET_SCRIPT" != /* ]]; then
    if [ -f "${SCRIPT_DIR}/${TARGET_SCRIPT}" ]; then
        CONTAINER_PATH="/swarm2/${TARGET_SCRIPT}"
    elif [ -f "${SCRIPT_DIR}/formations/${TARGET_SCRIPT}" ]; then
        CONTAINER_PATH="/swarm2/formations/${TARGET_SCRIPT}"
    elif [ -f "${SCRIPT_DIR}/tools/${TARGET_SCRIPT}" ]; then
        CONTAINER_PATH="/swarm2/tools/${TARGET_SCRIPT}"
    else
        echo "Error: Cannot find script '${TARGET_SCRIPT}' in ${SCRIPT_DIR}"
        exit 1
    fi
else
    CONTAINER_PATH="$TARGET_SCRIPT"
fi

# Check container status
if ! docker ps --format '{{.Names}}' | grep -q "^${CONTAINER}$"; then
    echo "[INFO] Container '${CONTAINER}' is not running. Starting Docker..."
    cd "${PROJECT_ROOT}/docker"
    docker compose up -d
    cd "${PROJECT_ROOT}"
fi

# Check TTY
DOCKER_IT="-i"
if [ -t 0 ] && [ -t 1 ]; then
    DOCKER_IT="-it"
fi

# Check if Crazyswarm2 server is running for flight/formation scripts
if [[ "$CONTAINER_PATH" != *"scan_drones.py"* ]]; then
    if ! docker exec "${CONTAINER}" bash -c "source /opt/ros/humble/setup.bash && ros2 node list 2>/dev/null" | grep -q "/crazyflie_server"; then
        echo ""
        echo "=========================================================="
        echo "[ERROR] Crazyswarm2 server (/crazyflie_server) is NOT running!"
        echo "=========================================================="
        echo " Formation and flight scripts communicate with real drones"
        echo " through the background ROS 2 Crazyflie server."
        echo ""
        echo " Please open a separate terminal and start the server first:"
        echo "   ./launch_ros2_real.sh"
        echo "=========================================================="
        echo ""
        exit 1
    fi
fi

echo "----------------------------------------------------------"
echo " Executing: ${CONTAINER_PATH} inside Docker"
echo "----------------------------------------------------------"

EXTRA_ARGS=("${@:2}")

docker exec $DOCKER_IT "${CONTAINER}" bash -c \
    "source /opt/ros/humble/setup.bash && source /ros2_ws/install/setup.bash && export PYTHONPATH=\"/swarm2:\$PYTHONPATH\" && python3 \"${CONTAINER_PATH}\" $(printf '%q ' "${EXTRA_ARGS[@]}")"

