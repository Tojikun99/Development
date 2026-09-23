#!/usr/bin/env python3
"""
Example 1: Single Drone Rectangle
Executes a 1x1 meter rectangular flight pattern at 0.5m altitude using the Crazyswarm2 high-level commander.
"""

from crazyflie_py import Crazyswarm
import time

def main():
    # Initialize Crazyswarm (also initializes rclpy)
    swarm = Crazyswarm()
    timeHelper = swarm.timeHelper
    
    # Get the first crazyflie
    cf = swarm.allcfs.crazyfliesByName['cf0']

    # cf0 spawn coordinate is (0, 0)
    HEIGHT = 0.5
    DURATION = 4.0  # Increased duration reduces velocity on arrival to minimize overshoot
    SLEEP = 6.0

    print("Taking off...")
    time.sleep(2.0)  # Wait for ROS 2 publisher connection
    cf.takeoff(targetHeight=HEIGHT, duration=3.0)
    timeHelper.sleep(8.0)

    print("Flying to Corner 1 (1.0, 0.0)...")
    cf.goTo(goal=[1.0, 0.0, HEIGHT], yaw=0.0, duration=DURATION, relative=False)
    timeHelper.sleep(SLEEP)

    print("Flying to Corner 2 (1.0, -1.0)...")
    cf.goTo(goal=[1.0, -1.0, HEIGHT], yaw=0.0, duration=DURATION, relative=False)
    timeHelper.sleep(SLEEP)

    print("Flying to Corner 3 (0.0, -1.0)...")
    cf.goTo(goal=[0.0, -1.0, HEIGHT], yaw=0.0, duration=DURATION, relative=False)
    timeHelper.sleep(SLEEP)

    print("Flying back to Start (0.0, 0.0)...")
    cf.goTo(goal=[0.0, 0.0, HEIGHT], yaw=0.0, duration=DURATION, relative=False)
    timeHelper.sleep(SLEEP)

    print("Landing...")
    cf.land(targetHeight=0.05, duration=3.0)
    timeHelper.sleep(4.0)

    print("Flight complete.")

if __name__ == "__main__":
    main()
