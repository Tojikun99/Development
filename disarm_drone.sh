#!/bin/bash
# ==============================================================================
# Disarm Crazyflie Drone(s)
# Usage:
#   ./disarm_drone.sh       # Disarm all connected drones
#   ./disarm_drone.sh cf1   # Disarm cf1 only
# ==============================================================================

set -e

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
TARGET_DRONE="$1"

if [ -n "$TARGET_DRONE" ]; then
    "${SCRIPT_DIR}/swarm2/run_formation.sh" "tools/disarm_drone.py" "$TARGET_DRONE"
else
    "${SCRIPT_DIR}/swarm2/run_formation.sh" "tools/disarm_drone.py"
fi
