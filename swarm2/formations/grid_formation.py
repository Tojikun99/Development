#!/usr/bin/env python3
"""
Grid Formation for Crazyflie Swarm (Crazyswarm2 / ROS 2)
Compatible with real hardware (Loco Positioning System) and SITL simulation.

Arranges drones in a clean 2D spatial matrix / grid.
"""

import sys
import math
import numpy as np
from crazyflie_py import Crazyswarm

TARGET_HEIGHT = 1.0    # Flight altitude in meters (1m from ground)
GRID_SPACING = 1.00     # 1 meter spacing between drones
HOLD_DURATION = 10.0
TAKEOFF_DURATION = 3.0
LAND_DURATION = 4.0


def main():
    print("==================================================")
    print("      Swarm2: Grid Formation Flight               ")
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

    # Determine grid rows and columns
    cols = int(math.ceil(math.sqrt(num_drones)))
    rows = int(math.ceil(num_drones / cols))
    print(f"[INFO] Formulating {rows}x{cols} grid (spacing = {GRID_SPACING}m)...")

    targets = {}
    for i, cf in enumerate(cfs):
        r = i // cols
        c = i % cols
        gx = (c - (cols - 1) / 2.0) * GRID_SPACING
        gy = (r - (rows - 1) / 2.0) * GRID_SPACING
        targets[cf] = (gx, gy)
        print(f"  - CF '{cf.prefix}' (row {r}, col {c}) -> ({gx:.2f}, {gy:.2f})")

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
    print(f"\n[STEP 2] Moving into Grid positions centered at ({cx:.2f}, {cy:.2f})...")
    # For 10 drones: 5 columns x 2 rows
    cols = 5 if num_drones == 10 else int(math.ceil(math.sqrt(num_drones)))
    rows = int(math.ceil(num_drones / cols))
    targets = {}
    for i, cf in enumerate(cfs):
        r = i // cols
        c = i % cols
        gx = cx + (c - (cols - 1) / 2.0) * SPACING
        gy = cy + (r - (rows - 1) / 2.0) * SPACING
        targets[cf] = (gx, gy)
        safe_z = TARGET_HEIGHT + (i % 3) * 0.20
        cf.goTo(goal=[gx, gy, safe_z], yaw=0.0, duration=4.0, relative=False)
    timeHelper.sleep(4.5)

    # Level out to target height
    for cf in cfs:
        gx, gy = targets[cf]
        cf.goTo(goal=[gx, gy, TARGET_HEIGHT], yaw=0.0, duration=2.0, relative=False)
    timeHelper.sleep(2.5)

    print(f"\n[STEP 3] Grid locked. Holding for {HOLD_DURATION}s...")
    timeHelper.sleep(HOLD_DURATION)

    print("\n[STEP 4] Returning to home positions...")
    for i, cf in enumerate(cfs):
        hx, hy, _ = home_positions[cf]
        safe_z = TARGET_HEIGHT + (i % 3) * 0.20
        cf.goTo(goal=[hx, hy, safe_z], yaw=0.0, duration=4.0, relative=False)
    timeHelper.sleep(4.5)

    for cf in cfs:
        hx, hy, _ = home_positions[cf]
        cf.goTo(goal=[hx, hy, TARGET_HEIGHT], yaw=0.0, duration=2.0, relative=False)
    timeHelper.sleep(2.5)

    print("\n[STEP 5] Landing safely...")
    swarm.allcfs.land(targetHeight=0.04, duration=LAND_DURATION)
    timeHelper.sleep(LAND_DURATION + 1.0)

    print("[SUCCESS] Grid formation flight complete.")


if __name__ == "__main__":
    main()
