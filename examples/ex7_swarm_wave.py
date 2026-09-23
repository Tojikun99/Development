#!/usr/bin/env python3
"""
Example 7: Swarm Wave
Demonstrates a coordinated kinematic flight pattern by streaming continuous
sinusoidal setpoints (cmdPosition) to a 10-drone swarm.

Note: Transitioning from low-level setpoint streaming back to the high-level
commander requires calling `notifySetpointsStop()` to prevent firmware motor-cutoff.
"""

from crazyflie_py import Crazyswarm
import time
import math
import numpy as np

def main():
    swarm = Crazyswarm()
    timeHelper = swarm.timeHelper
    cfs = swarm.allcfs.crazyflies

    print(f"Found {len(cfs)} drones in the swarm.")

    print("Waiting for live positions...")
    timeHelper.sleep(2.0)

    # Cache initial spawn coordinates for accurate return-to-home
    spawn = {cf: np.array(cf.position[:2]) for cf in cfs}

    BASE_HEIGHT = 1.0
    swarm.allcfs.takeoff(targetHeight=BASE_HEIGHT, duration=3.0)
    timeHelper.sleep(4.5)

    print("Forming a line for the wave...")
    spacing = 1.0
    start_x = -(len(cfs) - 1) * spacing / 2.0

    # Step 1: Disperse to safe staggered altitudes to avoid crossing collisions
    for i, cf in enumerate(cfs):
        x, y = spawn[cf]
        safe_height = BASE_HEIGHT + (i % 4) * 0.3
        cf.goTo(goal=[x, y, safe_height], yaw=0.0, duration=3.0, relative=False)
    timeHelper.sleep(4.0)

    # Step 2: Move to the line at staggered altitudes
    for i, cf in enumerate(cfs):
        x = start_x + i * spacing
        safe_height = BASE_HEIGHT + (i % 4) * 0.3
        cf.goTo(goal=[x, 0.0, safe_height], yaw=0.0, duration=5.0, relative=False)
    timeHelper.sleep(6.0)

    # Step 3: Settle down to the BASE_HEIGHT before starting the wave
    for i, cf in enumerate(cfs):
        x = start_x + i * spacing
        cf.goTo(goal=[x, 0.0, BASE_HEIGHT], yaw=0.0, duration=3.0, relative=False)
    timeHelper.sleep(4.0)

    print("Executing the swarm wave...")
    wave_amplitude = 0.5   # Vertical amplitude (meters)
    wave_frequency = 0.5   # Frequency (Hz)
    phase_offset = math.pi / 4.0  # Radian phase difference between adjacent drones

    duration = 15.0  # Fly the wave for 15 seconds
    dt = 0.1         # Update at 10Hz

    steps = int(duration / dt)
    start_time = time.time()

    for step in range(steps):
        t = time.time() - start_time
        for i, cf in enumerate(cfs):
            phase = i * phase_offset
            z = BASE_HEIGHT + wave_amplitude * math.sin(2.0 * math.pi * wave_frequency * t - phase)
            x = start_x + i * spacing
            cf.cmdPosition(pos=[x, 0.0, z], yaw=0.0)
        timeHelper.sleep(dt)

    # IMPORTANT: Transitioning from low-level cmdPosition streaming to high-level
    # commands (goTo/land) requires an explicit notifySetpointsStop().
    # Without this, the firmware's commander watchdog will trigger a motor-cutoff
    # when the setpoint stream terminates.
    print("Transitioning control to high-level commander...")
    for cf in cfs:
        cf.notifySetpointsStop()
    timeHelper.sleep(1.0)  # Allow firmware state transition

    print("Returning to spawn positions...")
    # Step 1: Disperse to staggered altitudes
    for i, cf in enumerate(cfs):
        x = start_x + i * spacing
        safe_height = BASE_HEIGHT + (i % 4) * 0.3
        cf.goTo(goal=[x, 0.0, safe_height], yaw=0.0, duration=3.0, relative=False)
    timeHelper.sleep(4.0)

    # Step 2: Move back to spawn X,Y at staggered altitudes
    for i, cf in enumerate(cfs):
        x, y = spawn[cf]
        safe_height = BASE_HEIGHT + (i % 4) * 0.3
        cf.goTo(goal=[x, y, safe_height], yaw=0.0, duration=5.0, relative=False)
    timeHelper.sleep(6.0)

    # Step 3: Settle back to BASE_HEIGHT
    for i, cf in enumerate(cfs):
        x, y = spawn[cf]
        cf.goTo(goal=[x, y, BASE_HEIGHT], yaw=0.0, duration=3.0, relative=False)
    timeHelper.sleep(4.0)

    print("Landing...")
    for cf in cfs:
        x, y = spawn[cf]
        cf.goTo(goal=[x, y, 0.1], yaw=0.0, duration=5.0, relative=False)
    timeHelper.sleep(6.0)

    print("Flight complete. Motors will cut off safely at 10cm altitude.")

if __name__ == "__main__":
    main()
