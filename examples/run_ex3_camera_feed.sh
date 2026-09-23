#!/bin/bash
# run_ex3_camera_feed.sh — Run Example 3 inside Docker.
#
# Prerequisites:
#   1. Simulation running:   ./run_demo.sh (Make sure you use the --camera flag!)

set -e
cd "$(dirname "$0")"
CONTAINER="crazyflie_sitl"

if ! docker ps --format '{{.Names}}' | grep -q "^${CONTAINER}$"; then
    echo "ERROR: Docker container '${CONTAINER}' is not running. Start ./run_demo.sh first."
    exit 1
fi

echo "Make sure you allowed X11 connections: run 'xhost +' on your host machine."
docker exec -it "${CONTAINER}" bash -c "export DISPLAY=$DISPLAY && cd /examples && python3 /examples/ex3_camera_feed.py"
