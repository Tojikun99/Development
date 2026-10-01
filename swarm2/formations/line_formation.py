#!/usr/bin/env python3
"""
Line Formation for Crazyflie Swarm (Crazyswarm2 / ROS 2)
Compatible with both real hardware (LPS / UWB) and SITL simulation.

Drones take off, transition to an evenly spaced linear formation along the X axis,
hold position, and safely return to their home coordinates before landing.
Safe altitude staggering is applied during transitions to eliminate collision risk.
"""

import sys
import numpy as np
from crazyflie_py import Crazyswarm

TARGET_HEIGHT = 1.0     # Flight altitude in meters (1m from ground)
SPACING = 1.0           # Distance between drones in meters
HOLD_DURATION = 20.0     # Time to hold formation in seconds
TAKEOFF_DURATION = 3.0
LAND_DURATION = 4.0
TRANSITION_DURATION = 4.0


def main():
    print("==================================================")
    print("      Swarm2: Linear Formation Flight             ")
    print("==================================================")

    swarm = Crazyswarm()
    timeHelper = swarm.timeHelper
    cfs = swarm.allcfs.crazyflies

    num_drones = len(cfs)
    print(f"[INFO] Detected {num_drones} drone(s) connected.")

    if num_drones == 0:
        print("[ERROR] No Crazyflies found in Crazyswarm2. Check your YAML config and radio connection.")
        sys.exit(1)

    # Cache initial spawn positions for returning home
    home_positions = {}
    for cf in cfs:
        home_positions[cf] = np.array(cf.initialPosition)
        print(f"  - Drone '{cf.prefix}': initial position = {home_positions[cf]}")

    print("\n[STEP 1] Stabilizing EKF & locking ground coordinates...")
    timeHelper.sleep(2.0)
    ground_targets = {}
    for cf in cfs:
        pos = np.array(cf.position)
        if np.linalg.norm(pos[:2]) > 0.05:
            ground_targets[cf] = pos[:2]
            home_positions[cf][:2] = pos[:2]
        else:
            ground_targets[cf] = home_positions[cf][:2]
        print(f"  • {cf.prefix}: Ground locked at ({ground_targets[cf][0]:.2f}, {ground_targets[cf][1]:.2f})")

    print(f"Taking off vertically to {TARGET_HEIGHT:.1f}m...")
    swarm.allcfs.takeoff(targetHeight=TARGET_HEIGHT, duration=TAKEOFF_DURATION)
    timeHelper.sleep(0.12)
    swarm.allcfs.takeoff(targetHeight=TARGET_HEIGHT, duration=TAKEOFF_DURATION)

    # Mid-ascent rescue check at 1.2s
    timeHelper.sleep(1.2)
    stragglers = [cf for cf in cfs if np.array(cf.position)[2] < 0.12]
    if stragglers:
        print(f"  \033[93m[RESCUE] {len(stragglers)} drone(s) on ground - sending direct unicast...\033[0m")
        for cf in stragglers:
            cf.arm(True)
            cf.takeoff(targetHeight=TARGET_HEIGHT, duration=max(1.8, TAKEOFF_DURATION - 1.2))

    timeHelper.sleep(max(0.5, TAKEOFF_DURATION - 1.2) + 0.6)

    # Final verification
    for cf in cfs:
        pos = np.array(cf.position)
        if pos[2] < 0.25:
            cf.arm(True)
            cf.takeoff(targetHeight=TARGET_HEIGHT, duration=2.5)
        elif np.linalg.norm(pos[:2]) > 0.05:
            home_positions[cf] = pos
        print(f"  • {cf.prefix}: In position-hold hover at ({home_positions[cf][0]:.2f}, {home_positions[cf][1]:.2f}, {TARGET_HEIGHT:.1f}m)")

    print("\n[STEP 2] Moving smoothly into Line Formation...")
    cx = float(np.mean([home_positions[cf][0] for cf in cfs]))
    cy = float(np.mean([home_positions[cf][1] for cf in cfs]))
    start_x = cx - (num_drones - 1) * SPACING / 2.0

    # Phase 2a: Altitude staggering during horizontal transit to prevent collision
    for i, cf in enumerate(cfs):
        safe_z = TARGET_HEIGHT + (i % 3) * 0.25
        hx, hy, _ = home_positions[cf]
        cf.goTo(goal=[hx, hy, safe_z], yaw=0.0, duration=2.5, relative=False)
    timeHelper.sleep(3.0)

    # Phase 2b: Move horizontally to line coordinates centered at (cx, cy)
    for i, cf in enumerate(cfs):
        line_x = start_x + i * SPACING
        line_y = cy
        safe_z = TARGET_HEIGHT + (i % 3) * 0.25
        print(f"  -> Moving '{cf.prefix}' to ({line_x:.2f}, {line_y:.2f}, {safe_z:.2f})")
        cf.goTo(goal=[line_x, line_y, safe_z], yaw=0.0, duration=TRANSITION_DURATION, relative=False)
    timeHelper.sleep(TRANSITION_DURATION + 1.0)

    # Phase 2c: Align to uniform target altitude
    print("  -> Leveling swarm to formation altitude...")
    for i, cf in enumerate(cfs):
        line_x = start_x + i * SPACING
        cf.goTo(goal=[line_x, 0.0, TARGET_HEIGHT], yaw=0.0, duration=2.5, relative=False)
    timeHelper.sleep(3.0)

    print(f"\n[STEP 3] Formation locked. Holding for {HOLD_DURATION}s...")
    timeHelper.sleep(HOLD_DURATION)

    print("\n[STEP 4] Returning safely to home positions...")
    # Return with altitude stagger
    for i, cf in enumerate(cfs):
        hx, hy, _ = home_positions[cf]
        safe_z = TARGET_HEIGHT + (i % 3) * 0.25
        cf.goTo(goal=[hx, hy, safe_z], yaw=0.0, duration=TRANSITION_DURATION, relative=False)
    timeHelper.sleep(TRANSITION_DURATION + 1.0)

    # Level down to base height above home
    for cf in cfs:
        hx, hy, _ = home_positions[cf]
        cf.goTo(goal=[hx, hy, TARGET_HEIGHT], yaw=0.0, duration=2.0, relative=False)
    timeHelper.sleep(2.5)

    print("\n[STEP 5] Landing safely...")
    swarm.allcfs.land(targetHeight=0.04, duration=LAND_DURATION)
    timeHelper.sleep(LAND_DURATION + 1.0)

    print("[SUCCESS] Mission complete. Motors safely cut off.")


if __name__ == "__main__":
    main()
