#!/bin/bash
# ==============================================================================
# Arm Crazyflie Drone(s)
# Usage:
#   ./arm_drone.sh       # Arm all connected drones
#   ./arm_drone.sh cf1   # Arm cf1 only
# ==============================================================================

set -e

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
TARGET_DRONE="$1"

if [ -n "$TARGET_DRONE" ]; then
    "${SCRIPT_DIR}/swarm2/run_formation.sh" "tools/arm_drone.py" "$TARGET_DRONE"
else
    "${SCRIPT_DIR}/swarm2/run_formation.sh" "tools/arm_drone.py"
fi
