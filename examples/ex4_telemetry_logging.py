#!/usr/bin/env python3
"""
Example 4: Telemetry Logging
Demonstrates multi-threaded ROS 2 integration by flying a Crazyswarm2 sequence
while simultaneously subscribing to /cf0/pose and /cf0/status topics for CSV logging.
"""

import rclpy
from rclpy.node import Node
from crazyflie_interfaces.msg import Status
from geometry_msgs.msg import PoseStamped
from crazyflie_py import Crazyswarm
import time
import csv
import threading

class TelemetryLogger(Node):
    def __init__(self):
        super().__init__("ex4_telemetry_logger")
        
        # Open CSV file
        self.csv_file = open('flight_log.csv', 'w', newline='')
        self.csv_writer = csv.writer(self.csv_file)
        self.csv_writer.writerow(['timestamp', 'battery_voltage', 'pm_state', 'pos_x', 'pos_y', 'pos_z'])
        
        self.latest_battery = 0.0
        self.latest_pm_state = 0
        
        from rclpy.qos import qos_profile_sensor_data
        
        # Subscriptions (using SensorData QoS to match the publisher)
        self.create_subscription(Status, '/cf0/status', self.status_callback, qos_profile_sensor_data)
        self.create_subscription(PoseStamped, '/cf0/pose', self.pose_callback, qos_profile_sensor_data)

    def status_callback(self, msg):
        self.latest_battery = msg.battery_voltage
        self.latest_pm_state = msg.pm_state

    def pose_callback(self, msg):
        timestamp = msg.header.stamp.sec + msg.header.stamp.nanosec * 1e-9
        x = msg.pose.position.x
        y = msg.pose.position.y
        z = msg.pose.position.z
        self.csv_writer.writerow([f"{timestamp:.3f}", f"{self.latest_battery:.2f}", self.latest_pm_state, f"{x:.3f}", f"{y:.3f}", f"{z:.3f}"])
        self.csv_file.flush()

    def close(self):
        self.csv_file.close()

def main():
    # Initialize Crazyswarm
    swarm = Crazyswarm()
    timeHelper = swarm.timeHelper
    cf = swarm.allcfs.crazyfliesByName['cf0']
    
    # Create the logger node
    logger_node = TelemetryLogger()
    
    # Execute the logger node in a background thread to prevent blocking timeHelper.sleep()
    executor = rclpy.executors.SingleThreadedExecutor()
    executor.add_node(logger_node)
    spin_thread = threading.Thread(target=executor.spin, daemon=True)
    spin_thread.start()

    print("Taking off...")
    cf.takeoff(targetHeight=0.5, duration=3.0)
    
    print("Hovering & logging data for 10 seconds...")
    timeHelper.sleep(13.0)  # 3s takeoff + 10s hover

    print("Landing...")
    cf.land(targetHeight=0.05, duration=3.0)
    timeHelper.sleep(4.0)

    print("Flight complete. Logs saved to flight_log.csv")
    logger_node.close()
    
    # Cleanup
    executor.shutdown()
    logger_node.destroy_node()

if __name__ == "__main__":
    main()
