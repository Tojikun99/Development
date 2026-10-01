#!/usr/bin/env python3
"""
Real-time Telemetry Monitor for Crazyflie Drones
Subscribes to ROS 2 pose and status topics and prints a clean live dashboard.
"""

import sys
import rclpy
from rclpy.node import Node
from geometry_msgs.msg import PoseStamped
from crazyflie_interfaces.msg import Status

class SwarmTelemetryMonitor(Node):
    def __init__(self):
        super().__init__('swarm_telemetry_monitor')
        self.drones = {}

        # Discover active drone topics
        topic_names_and_types = self.get_topic_names_and_types()
        found_drones = set()
        for topic_name, types in topic_names_and_types:
            parts = topic_name.strip('/').split('/')
            if len(parts) >= 2 and parts[1] == 'pose':
                drone_name = parts[0]
                found_drones.add(drone_name)

        if not found_drones:
            print("[WARN] No active drone topics detected. Are the Crazyflies connected to Crazyswarm2?")
            # Default fallback for cf1 and cf2
            found_drones = {'cf1', 'cf2'}

        print(f"Subscribing to telemetry for: {', '.join(sorted(found_drones))}")
        for drone in sorted(found_drones):
            self.drones[drone] = {'x': 0.0, 'y': 0.0, 'z': 0.0, 'vbat': 0.0, 'rssi': 0}
            
            # Subscribe to pose
            self.create_subscription(
                PoseStamped,
                f'/{drone}/pose',
                lambda msg, d=drone: self.pose_callback(d, msg),
                10
            )
            # Subscribe to status
            self.create_subscription(
                Status,
                f'/{drone}/status',
                lambda msg, d=drone: self.status_callback(d, msg),
                10
            )

        self.timer = self.create_timer(0.5, self.render_dashboard)

    def pose_callback(self, drone, msg):
        self.drones[drone]['x'] = msg.pose.position.x
        self.drones[drone]['y'] = msg.pose.position.y
        self.drones[drone]['z'] = msg.pose.position.z

    def status_callback(self, drone, msg):
        self.drones[drone]['vbat'] = getattr(msg, 'battery_voltage', getattr(msg, 'vbat', 0.0))
        self.drones[drone]['rssi'] = getattr(msg, 'rssi', 0)

    def render_dashboard(self):
        # Clear screen and render
        print("\033[H\033[J", end="")
        print("==========================================================================")
        print("                   Crazyflie ROS 2 Telemetry Dashboard                   ")
        print("==========================================================================")
        print(f"{'Drone':<10} | {'X (m)':<10} | {'Y (m)':<10} | {'Z (m)':<10} | {'Battery (V)':<12} | {'RSSI':<8}")
        print("-" * 74)
        for drone, data in sorted(self.drones.items()):
            vbat_str = f"{data['vbat']:.2f} V" if data['vbat'] > 0 else "N/A"
            rssi_str = f"{data['rssi']} dBm" if data['rssi'] != 0 else "N/A"
            print(f"{drone:<10} | {data['x']:<10.3f} | {data['y']:<10.3f} | {data['z']:<10.3f} | {vbat_str:<12} | {rssi_str:<8}")
        print("==========================================================================")
        print("Press Ctrl+C to exit monitor.")

def main():
    rclpy.init()
    monitor = SwarmTelemetryMonitor()
    try:
        rclpy.spin(monitor)
    except KeyboardInterrupt:
        pass
    finally:
        monitor.destroy_node()
        rclpy.shutdown()

if __name__ == '__main__':
    main()
