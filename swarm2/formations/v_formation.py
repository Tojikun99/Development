#!/usr/bin/env python3
"""
V-Formation (Arrowhead) for Crazyflie Swarm (Crazyswarm2 / ROS 2)
Compatible with real hardware (Loco Positioning System) and SITL simulation.

Lead drone positions at the apex with following drones forming symmetrical V-wings.
"""

import sys
import numpy as np
from crazyflie_py import Crazyswarm

TARGET_HEIGHT = 1.0     # Flight altitude in meters (1m from ground)
ARM_SPACING_X = 0.45    # Step back along flight axis
ARM_SPACING_Y = 0.45    # Step outward on wing
HOLD_DURATION = 6.0
TAKEOFF_DURATION = 3.0
LAND_DURATION = 4.0


def main():
    print("==================================================")
    print("      Swarm2: V-Formation Flight                  ")
    print("==================================================")

    swarm = Crazyswarm()
    timeHelper = swarm.timeHelper
    cfs = swarm.allcfs.crazyflies

    num_drones = len(cfs)
    print(f"[INFO] Detected {num_drones} drone(s) connected.")

    if num_drones == 0:
        print("[ERROR] No Crazyflies found.")
        sys.exit(1)

    home_positions = {cf: np.array(cf.initialPosition) for cf in cfs}

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

    for cf in cfs:
        pos = np.array(cf.position)
        if pos[2] < 0.25:
            cf.arm(True)
            cf.takeoff(targetHeight=TARGET_HEIGHT, duration=2.5)
        elif np.linalg.norm(pos[:2]) > 0.05:
            home_positions[cf] = pos
        print(f"  • {cf.prefix}: In position-hold hover at ({home_positions[cf][0]:.2f}, {home_positions[cf][1]:.2f}, {TARGET_HEIGHT:.1f}m)")

    cx = float(np.mean([home_positions[cf][0] for cf in cfs]))
    cy = float(np.mean([home_positions[cf][1] for cf in cfs]))
    print(f"\n[STEP 2] Computing V-Formation coordinates around centroid ({cx:.2f}, {cy:.2f})...")
    # Drone 0: Apex (forward)
    # Drone 1: Left wing 1
    # Drone 2: Right wing 1
    # Drone 3: Left wing 2, etc.
    targets = {}
    for i, cf in enumerate(cfs):
        if i == 0:
            tx = cx + (num_drones // 2) * ARM_SPACING_X * 0.5
            ty = cy
        else:
            rank = (i + 1) // 2
            side = -1.0 if (i % 2 == 1) else 1.0
            tx = cx + (num_drones // 2) * ARM_SPACING_X * 0.5 - rank * ARM_SPACING_X
            ty = cy + side * rank * ARM_SPACING_Y
        targets[cf] = (tx, ty)
        print(f"  - Target for '{cf.prefix}': ({tx:.2f}, {ty:.2f}, {TARGET_HEIGHT:.2f})")

    print("\n[STEP 3] Transitioning to V-Formation with altitude safety...")
    # Safe staggered heights
    for i, cf in enumerate(cfs):
        tx, ty = targets[cf]
        safe_z = TARGET_HEIGHT + (i % 3) * 0.20
        cf.goTo(goal=[tx, ty, safe_z], yaw=0.0, duration=4.0, relative=False)
    timeHelper.sleep(4.5)

    # Level out
    for cf in cfs:
        tx, ty = targets[cf]
        cf.goTo(goal=[tx, ty, TARGET_HEIGHT], yaw=0.0, duration=2.0, relative=False)
    timeHelper.sleep(2.5)

    print(f"\n[STEP 4] V-Formation locked. Holding for {HOLD_DURATION}s...")
    timeHelper.sleep(HOLD_DURATION)

    print("\n[STEP 5] Returning to home positions...")
    for i, cf in enumerate(cfs):
        hx, hy, _ = home_positions[cf]
        safe_z = TARGET_HEIGHT + (i % 3) * 0.20
        cf.goTo(goal=[hx, hy, safe_z], yaw=0.0, duration=4.0, relative=False)
    timeHelper.sleep(4.5)

    for cf in cfs:
        hx, hy, _ = home_positions[cf]
        cf.goTo(goal=[hx, hy, TARGET_HEIGHT], yaw=0.0, duration=2.0, relative=False)
    timeHelper.sleep(2.5)

    print("\n[STEP 6] Landing safely...")
    swarm.allcfs.land(targetHeight=0.04, duration=LAND_DURATION)
    timeHelper.sleep(LAND_DURATION + 1.0)

    print("[SUCCESS] V-Formation flight complete.")


if __name__ == "__main__":
    main()
