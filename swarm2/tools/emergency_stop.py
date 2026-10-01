#!/usr/bin/env python3
"""
Emergency Stop for Crazyflie Swarm
Calls /all/emergency service to immediately cut power to all motors.
"""

import sys
import rclpy
from rclpy.node import Node
from std_srvs.srv import Empty

def main():
    print("==================================================")
    print("      TRIGGERING EMERGENCY MOTOR CUTOFF           ")
    print("==================================================")

    rclpy.init()
    node = Node('emergency_stop_client')
    client = node.create_client(Empty, '/all/emergency')

    if not client.wait_for_service(timeout_sec=2.0):
        print("[ERROR] Service /all/emergency is not available.")
        sys.exit(1)

    req = Empty.Request()
    future = client.call_async(req)
    rclpy.spin_until_future_complete(node, future, timeout_sec=2.0)

    if future.result() is not None:
        print("\033[91m[SUCCESS] Emergency stop signal sent. Motors disabled.\033[0m")
    else:
        print("[ERROR] Failed to send emergency command.")

    node.destroy_node()
    rclpy.shutdown()

if __name__ == '__main__':
    main()
