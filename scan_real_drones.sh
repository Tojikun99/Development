#!/bin/bash
# Scan for active real Crazyflie drones on the airwaves using Crazyradio PA
set -e

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
"${SCRIPT_DIR}/swarm2/run_formation.sh" "tools/scan_drones.py"
