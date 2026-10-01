#!/bin/bash
# Emergency motor stop for all Crazyflies
set -e

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
"${SCRIPT_DIR}/swarm2/run_formation.sh" "tools/emergency_stop.py"
