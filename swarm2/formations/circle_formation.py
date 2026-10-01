#!/usr/bin/env python3
"""
Circle Formation for Crazyflie Swarm (Crazyswarm2 / ROS 2)
Compatible with real hardware (Loco Positioning System) and SITL simulation.

Arranges drones uniformly in a circular perimeter of radius R.
Optionally performs a coordinated orbital rotation before returning to base.
"""

import sys
import math
import numpy as np
from crazyflie_py import Crazyswarm

RADIUS = 0.75           # Circle radius in meters
TARGET_HEIGHT = 1.0    # Altitude in meters (1m from ground)
HOLD_DURATION = 6.0     # Time to hold circle
ORBIT_ROUNDS = 1        # Set to 1 for an orbital spin, 0 for static hold
TAKEOFF_DURATION = 3.0
LAND_DURATION = 4.0


def main():
    print("==================================================")
    print("      Swarm2: Circle Formation Flight            ")
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
    print(f"\n[STEP 2] Forming Circle (radius = {RADIUS}m around centroid X={cx:.2f}, Y={cy:.2f})...")
    # Compute angles for each drone
    for i, cf in enumerate(cfs):
        angle = (2.0 * math.pi * i) / num_drones
        tx = cx + RADIUS * math.cos(angle)
        ty = cy + RADIUS * math.sin(angle)
        safe_z = TARGET_HEIGHT + (i % 2) * 0.20
        print(f"  -> CF '{cf.prefix}' moving to ({tx:.2f}, {ty:.2f}, {safe_z:.2f})")
        cf.goTo(goal=[tx, ty, safe_z], yaw=angle, duration=4.0, relative=False)
    timeHelper.sleep(4.5)

    # Level all to uniform height
    for i, cf in enumerate(cfs):
        angle = (2.0 * math.pi * i) / num_drones
        tx = cx + RADIUS * math.cos(angle)
        ty = cy + RADIUS * math.sin(angle)
        cf.goTo(goal=[tx, ty, TARGET_HEIGHT], yaw=angle, duration=2.0, relative=False)
    timeHelper.sleep(2.5)

    print(f"\n[STEP 3] Circle formed. Holding for {HOLD_DURATION}s...")
    timeHelper.sleep(HOLD_DURATION)

    # Optional coordinated orbit
    if ORBIT_ROUNDS > 0 and num_drones >= 2:
        print("\n[STEP 4] Executing synchronized circular orbit...")
        steps = 36
        dt = 0.25
        for s in range(steps):
            phase = (2.0 * math.pi * s) / steps
            for i, cf in enumerate(cfs):
                angle = (2.0 * math.pi * i) / num_drones + phase
                tx = cx + RADIUS * math.cos(angle)
                ty = cy + RADIUS * math.sin(angle)
                cf.goTo(goal=[tx, ty, TARGET_HEIGHT], yaw=angle, duration=dt * 1.5, relative=False)
            timeHelper.sleep(dt)

    print("\n[STEP 5] Returning to home positions...")
    for i, cf in enumerate(cfs):
        hx, hy, _ = home_positions[cf]
        safe_z = TARGET_HEIGHT + (i % 2) * 0.20
        cf.goTo(goal=[hx, hy, safe_z], yaw=0.0, duration=4.0, relative=False)
    timeHelper.sleep(4.5)

    for cf in cfs:
        hx, hy, _ = home_positions[cf]
        cf.goTo(goal=[hx, hy, TARGET_HEIGHT], yaw=0.0, duration=2.0, relative=False)
    timeHelper.sleep(2.5)

    print("\n[STEP 6] Landing safely...")
    swarm.allcfs.land(targetHeight=0.04, duration=LAND_DURATION)
    timeHelper.sleep(LAND_DURATION + 1.0)

    print("[SUCCESS] Circle formation flight complete.")


if __name__ == "__main__":
    main()
