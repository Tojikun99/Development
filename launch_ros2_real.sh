#!/bin/bash
# ==============================================================================
# Launch Crazyswarm2 for Real Crazyflie Hardware
# Connects to physical Crazyflies via Bitcraze Crazyradio PA
# using Loco Positioning System (LPS / UWB) on-board state estimation.
#
# Features:
#   - Automatic active drone discovery: scans for online drones (up to 10)
#     and enables only the active ones, guaranteeing zero-timeout startup
#     and continuous unbroken connection even if only a subset of drones is on.
#
# Usage:
#   ./launch_ros2_real.sh [options]
#
# Options:
#   --backend <cpp|cflib>   Select Crazyswarm2 backend (default: cpp, recommended for multi-drone swarms)
#   --config <path>         Path to custom crazyflies.yaml
#   --no-scan               Skip auto-discovery and use exact config file
#   --rviz                  Launch RViz2 for live 3D visualization
#   --teleop                Enable gamepad/joystick teleoperation
#   -h, --help              Show this help message
# ==============================================================================

set -e

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
CONTAINER="crazyflie_sitl"

BACKEND="cpp"
CONFIG_FILE=""
AUTO_SCAN=true
RVIZ="False"
TELEOP="False"

# Parse CLI flags
while [[ "$#" -gt 0 ]]; do
    case $1 in
        --backend) BACKEND="$2"; shift ;;
        --config) CONFIG_FILE="$2"; AUTO_SCAN=false; shift ;;
        --no-scan) AUTO_SCAN=false ;;
        --rviz) RVIZ="True" ;;
        --teleop) TELEOP="True" ;;
        -h|--help)
            echo "Usage: ./launch_ros2_real.sh [options]"
            echo "Options:"
            echo "  --backend <cpp|cflib>  Select backend (default: cpp, recommended for swarms)"
            echo "  --config <path>        Custom crazyflies.yaml path"
            echo "  --no-scan              Skip active drone auto-discovery"
            echo "  --rviz                 Launch RViz2 visualization"
            echo "  --teleop               Enable joystick teleoperation"
            echo "  -h, --help             Show help"
            exit 0
            ;;
        *) echo "Unknown option: $1"; exit 1 ;;
    esac
    shift
done

echo "=========================================================================="
echo "          Starting Crazyswarm2 for REAL Crazyflie Hardware                "
echo "=========================================================================="
echo " Radio Backend   : $BACKEND"
echo " Positioning     : Loco Positioning System (LPS UWB / EKF Estimator)"
echo " Auto-Discovery  : $AUTO_SCAN (Max 10 drones)"
echo " RViz2           : $RVIZ"
echo " Teleop          : $TELEOP"
echo "=========================================================================="

# Check for Crazyradio USB device on host
if lsusb 2>/dev/null | grep -q "1915:7777"; then
    echo "[OK] Crazyradio PA detected on USB."
else
    echo "[WARN] Crazyradio PA (USB ID 1915:7777) was not detected in 'lsusb'."
    echo "       Please plug in your Crazyradio PA USB dongle."
    read -p "       Do you want to continue anyway? [y/N]: " proceed
    if [[ ! "$proceed" =~ ^[Yy]$ ]]; then
        echo "Exiting. Plug in Crazyradio PA and rerun."
        exit 1
    fi
fi

# Ensure Docker container is running with USB passthrough
cd "${SCRIPT_DIR}/docker"
if ! docker ps --format '{{.Names}}' | grep -q "^${CONTAINER}$"; then
    echo "[INFO] Starting Docker environment with USB passthrough..."
    docker compose up -d
else
    # Check if /dev/bus/usb is mounted inside container
    if ! docker exec "${CONTAINER}" ls /dev/bus/usb >/dev/null 2>&1; then
        echo "[INFO] Updating container configuration to enable USB device access..."
        docker compose up -d --force-recreate
    fi
fi
cd "${SCRIPT_DIR}"

DOCKER_IT="-i"
if [ -t 0 ] && [ -t 1 ]; then
    DOCKER_IT="-it"
fi

# Perform dynamic active drone discovery if enabled
if [ "$AUTO_SCAN" = true ]; then
    echo ""
    docker exec $DOCKER_IT "${CONTAINER}" bash -c \
        "source /opt/ros/humble/setup.bash && source /ros2_ws/install/setup.bash && \
         python3 /swarm2/tools/detect_active_drones.py /swarm2/config/crazyflies_real.yaml /swarm2/config/crazyflies_active.yaml"
    CONFIG_FILE="/swarm2/config/crazyflies_active.yaml"
fi

if [ -z "$CONFIG_FILE" ]; then
    CONFIG_FILE="/swarm2/config/crazyflies_real.yaml"
fi

# Allow X11 forwarding if RViz is requested
if [ "$RVIZ" == "True" ]; then
    xhost +local:root >/dev/null 2>&1 || xhost + >/dev/null 2>&1 || true
fi

echo ""
echo "Connecting to active Crazyflies using: $CONFIG_FILE"
echo "Communication will remain continuous and unbroken."
echo "Press Ctrl+C to stop the ROS 2 server."
echo "--------------------------------------------------------------------------"

docker exec $DOCKER_IT "${CONTAINER}" bash -c \
    "source /opt/ros/humble/setup.bash && source /ros2_ws/install/setup.bash && \
     ros2 launch crazyflie launch.py \
        crazyflies_yaml_file:=\"${CONFIG_FILE}\" \
        backend:=\"${BACKEND}\" \
        mocap:=False \
        teleop:=\"${TELEOP}\" \
        rviz:=\"${RVIZ}\""
