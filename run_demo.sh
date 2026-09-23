#!/bin/bash
set -e

# Resolve script directory
cd "$(dirname "$0")"

# Default configuration
SIMULATOR="mujoco"
CAMERA=""

# Parse arguments
while [[ "$#" -gt 0 ]]; do
    case $1 in
        --sim) SIMULATOR="$2"; shift ;;
        --camera) CAMERA="--camera" ;;
        *) echo "Unknown parameter passed: $1"; exit 1 ;;
    esac
    shift
done

if [[ "$SIMULATOR" != "mujoco" && "$SIMULATOR" != "gazebo" ]]; then
    echo "Error: --sim must be either 'mujoco' or 'gazebo'"
    exit 1
fi

# Reset terminal state
printf "\033[0m\033]8;;\033\\"

echo "=========================================================================="
echo "               Crazyflie SITL Simulation Environment"
echo "=========================================================================="
echo " Firmware  : Bitcraze SITL Master"
echo " Physics   : $SIMULATOR"
echo " ROS 2     : Crazyswarm2 (Humble)"
echo " SDK       : cflib / cfclient"
echo "=========================================================================="

# Allow local X11 connections for the simulator GUI
xhost + >/dev/null 2>&1 || true

echo "[0/3] Initializing Submodules..."
git submodule update --init --recursive

echo "[1/3] Starting Docker Environment..."
cd docker
docker compose down 2>/dev/null || true
docker compose up --build -d

echo "[2/3] Building SITL Firmware..."
docker exec crazyflie_sitl bash -c "git config --global --add safe.directory '*' && cd /CrazySim/crazyflie-firmware && echo '{\"tag\": \"SITL\"}' > build_info.json && make cf2_defconfig && make silentoldconfig && mkdir -p sitl_make/build && cd sitl_make/build && cmake .. && make -j4 cf2 crazysim_gz"

echo "[3/3] Launching $SIMULATOR Backend..."
if [ "$SIMULATOR" == "gazebo" ]; then
    docker exec crazyflie_sitl bash -c "cd /CrazySim/crazyflie-firmware && bash tools/crazyflie-simulation/simulator_files/gazebo/launch/sitl_multiagent_square.sh -n 10"
else
    docker exec crazyflie_sitl bash -c "cd /CrazySim/crazyflie-firmware && bash tools/crazyflie-simulation/simulator_files/mujoco/launch/sitl_multiagent_square.sh -n 10 --vis $CAMERA"
fi
