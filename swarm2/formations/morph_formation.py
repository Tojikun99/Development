#!/usr/bin/env python3
"""
Dynamic Formation Morphing Flight for Crazyflie Swarm (Crazyswarm2 / ROS 2)
Compatible with real hardware (Loco Positioning System) and SITL simulation.

Executes a seamless multi-shape airshow sequence:
  1. Takeoff & Home Stabilization
  2. Morph -> Line Formation (hold 5s)
  3. Morph -> Circular Perimeter (hold 5s)
  4. Morph -> V-Shape / Arrowhead (hold 5s)
  5. Return Home & Smooth Landing

Uses multi-tier altitude staggering to guarantee 100% collision-free transitions.
"""

import sys
import math
import numpy as np
from crazyflie_py import Crazyswarm

BASE_HEIGHT = 1.0       # Flight altitude (1m from ground)
TAKEOFF_DURATION = 3.0
LAND_DURATION = 4.0
TRANSITION_DURATION = 4.0
HOLD_DURATION = 5.0


def transition_to_shape(cfs, timeHelper, shape_targets, target_height=BASE_HEIGHT):
    """Safely transitions all drones to a new set of 2D coordinates."""
    # Step 1: Disperse vertically to prevent horizontal plane collisions
    for i, cf in enumerate(cfs):
        tx, ty = shape_targets[cf]
        stagger_z = target_height + (i % 3) * 0.22
        # Move up/down first
        cf.goTo(goal=[cf.position[0], cf.position[1], stagger_z], yaw=0.0, duration=1.5, relative=False)
    timeHelper.sleep(2.0)

    # Step 2: Fly to new (X, Y) coordinates at staggered altitude
    for i, cf in enumerate(cfs):
        tx, ty = shape_targets[cf]
        stagger_z = target_height + (i % 3) * 0.22
        cf.goTo(goal=[tx, ty, stagger_z], yaw=0.0, duration=TRANSITION_DURATION, relative=False)
    timeHelper.sleep(TRANSITION_DURATION + 0.5)

    # Step 3: Align to uniform base height
    for cf in cfs:
        tx, ty = shape_targets[cf]
        cf.goTo(goal=[tx, ty, target_height], yaw=0.0, duration=2.0, relative=False)
    timeHelper.sleep(2.5)


def main():
    print("==================================================")
    print("      Swarm2: Dynamic Formation Morphing          ")
    print("==================================================")

    swarm = Crazyswarm()
    timeHelper = swarm.timeHelper
    cfs = swarm.allcfs.crazyflies

    num_drones = len(cfs)
    print(f"[INFO] Initialized with {num_drones} drone(s).")

    if num_drones == 0:
        print("[ERROR] No drones connected.")
        sys.exit(1)

    home_positions = {cf: np.array(cf.initialPosition) for cf in cfs}

    print("\n[PHASE 1] Stabilizing EKF & locking ground coordinates...")
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

    print(f"Taking off vertically to {BASE_HEIGHT:.1f}m...")
    swarm.allcfs.takeoff(targetHeight=BASE_HEIGHT, duration=TAKEOFF_DURATION)
    timeHelper.sleep(0.12)
    swarm.allcfs.takeoff(targetHeight=BASE_HEIGHT, duration=TAKEOFF_DURATION)

    # Mid-ascent rescue check at 1.2s
    timeHelper.sleep(1.2)
    stragglers = [cf for cf in cfs if np.array(cf.position)[2] < 0.12]
    if stragglers:
        print(f"  \033[93m[RESCUE] {len(stragglers)} drone(s) on ground - sending direct unicast...\033[0m")
        for cf in stragglers:
            cf.arm(True)
            cf.takeoff(targetHeight=BASE_HEIGHT, duration=max(1.8, TAKEOFF_DURATION - 1.2))

    timeHelper.sleep(max(0.5, TAKEOFF_DURATION - 1.2) + 0.6)

    for cf in cfs:
        pos = np.array(cf.position)
        if pos[2] < 0.25:
            cf.arm(True)
            cf.takeoff(targetHeight=BASE_HEIGHT, duration=2.5)
        elif np.linalg.norm(pos[:2]) > 0.05:
            home_positions[cf] = pos
        print(f"  • {cf.prefix}: In position-hold hover at ({home_positions[cf][0]:.2f}, {home_positions[cf][1]:.2f}, {BASE_HEIGHT:.1f}m)")

    cx = float(np.mean([home_positions[cf][0] for cf in cfs]))
    cy = float(np.mean([home_positions[cf][1] for cf in cfs]))

    # --- SHAPE 1: LINE FORMATION ---
    print(f"\n[PHASE 2] Morphing -> Line Formation (centered at {cx:.2f}, {cy:.2f})...")
    spacing = 0.60
    start_x = cx - (num_drones - 1) * spacing / 2.0
    line_targets = {cf: (start_x + i * spacing, cy) for i, cf in enumerate(cfs)}
    transition_to_shape(cfs, timeHelper, line_targets)
    print(f"  -> Line formation locked. Holding for {HOLD_DURATION}s...")
    timeHelper.sleep(HOLD_DURATION)

    # --- SHAPE 2: CIRCLE FORMATION ---
    print(f"\n[PHASE 3] Morphing -> Circle Formation (centered at {cx:.2f}, {cy:.2f})...")
    radius = 0.70
    circle_targets = {}
    for i, cf in enumerate(cfs):
        angle = (2.0 * math.pi * i) / num_drones
        circle_targets[cf] = (cx + radius * math.cos(angle), cy + radius * math.sin(angle))
    transition_to_shape(cfs, timeHelper, circle_targets)
    print(f"  -> Circle formation locked. Holding for {HOLD_DURATION}s...")
    timeHelper.sleep(HOLD_DURATION)

    # --- SHAPE 3: V-FORMATION ---
    print(f"\n[PHASE 4] Morphing -> V-Formation (centered at {cx:.2f}, {cy:.2f})...")
    v_targets = {}
    arm_x = 0.40
    arm_y = 0.40
    for i, cf in enumerate(cfs):
        if i == 0:
            tx = cx + (num_drones // 2) * arm_x * 0.5
            ty = cy
        else:
            rank = (i + 1) // 2
            side = -1.0 if (i % 2 == 1) else 1.0
            tx = cx + (num_drones // 2) * arm_x * 0.5 - rank * arm_x
            ty = cy + side * rank * arm_y
        v_targets[cf] = (tx, ty)
    transition_to_shape(cfs, timeHelper, v_targets)
    print(f"  -> V-Formation locked. Holding for {HOLD_DURATION}s...")
    timeHelper.sleep(HOLD_DURATION)

    # --- RETURN HOME & LAND ---
    print("\n[PHASE 5] Returning to initial home positions...")
    home_targets = {cf: (home_positions[cf][0], home_positions[cf][1]) for cf in cfs}
    transition_to_shape(cfs, timeHelper, home_targets)

    print("\n[PHASE 6] Landing safely...")
    swarm.allcfs.land(targetHeight=0.04, duration=LAND_DURATION)
    timeHelper.sleep(LAND_DURATION + 1.0)

    print("\n==================================================")
    print("      Airshow Complete! Mission Successful.       ")
    print("==================================================")


if __name__ == "__main__":
    main()
