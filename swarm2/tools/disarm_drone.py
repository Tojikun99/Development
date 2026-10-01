#!/usr/bin/env python3
"""
Disarm Crazyflie Drone(s)
Disables drone motors safely.

Usage:
  python3 disarm_drone.py [drone_name]
  python3 disarm_drone.py          # Disarms all connected drones
  python3 disarm_drone.py cf1      # Disarms cf1 only
"""

import sys
from crazyflie_py import Crazyswarm

def main():
    target_drone = sys.argv[1] if len(sys.argv) > 1 else None

    print("==================================================")
    print("         Disarming Crazyflie Drone(s)             ")
    print("==================================================")

    swarm = Crazyswarm()
    timeHelper = swarm.timeHelper
    allcfs = swarm.allcfs

    if not allcfs.crazyflies:
        print("[ERROR] No Crazyflies found. Ensure Crazyswarm2 server is running.")
        sys.exit(1)

    if target_drone and target_drone.lower() != "all":
        # Find matching drone
        matched = None
        for cf in allcfs.crazyflies:
            if cf.prefix == target_drone or cf.prefix == f"/{target_drone}":
                matched = cf
                break

        if matched:
            print(f"[ACTION] Disarming drone '{matched.prefix}'...")
            matched.arm(False)
            timeHelper.sleep(1.0)
            print(f"\033[93m[SUCCESS] Drone '{matched.prefix}' disarmed successfully.\033[0m")
        else:
            available = [cf.prefix for cf in allcfs.crazyflies]
            print(f"[ERROR] Drone '{target_drone}' not found among active drones: {available}")
            sys.exit(1)
    else:
        print(f"[ACTION] Broadcasting disarm signal to all {len(allcfs.crazyflies)} drone(s)...")
        allcfs.arm(False)
        timeHelper.sleep(1.0)
        print("\033[93m[SUCCESS] All drones disarmed. Motors disabled.\033[0m")

if __name__ == "__main__":
    main()
