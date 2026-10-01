#!/usr/bin/env python3
"""
Arm Crazyflie Drone(s)
Enables drone motors for flight operations.

Usage:
  python3 arm_drone.py [drone_name]
  python3 arm_drone.py          # Arms all connected drones
  python3 arm_drone.py cf1      # Arms cf1 only
"""

import sys
from crazyflie_py import Crazyswarm

def main():
    target_drone = sys.argv[1] if len(sys.argv) > 1 else None

    print("==================================================")
    print("           Arming Crazyflie Drone(s)              ")
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
            print(f"[ACTION] Arming drone '{matched.prefix}'...")
            matched.arm(True)
            timeHelper.sleep(1.0)
            print(f"\033[92m[SUCCESS] Drone '{matched.prefix}' armed successfully.\033[0m")
        else:
            available = [cf.prefix for cf in allcfs.crazyflies]
            print(f"[ERROR] Drone '{target_drone}' not found among active drones: {available}")
            sys.exit(1)
    else:
        print(f"[ACTION] Arming all {len(allcfs.crazyflies)} connected drone(s)...")
        for cf in allcfs.crazyflies:
            print(f"  • Arming '{cf.prefix}'...")
            cf.arm(True)
            timeHelper.sleep(0.5)

        timeHelper.sleep(1.0)
        print("\033[92m[SUCCESS] All drones armed and ready for flight commands.\033[0m")

if __name__ == "__main__":
    main()
