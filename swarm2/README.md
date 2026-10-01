# Swarm2 Formation & Real Drone Flight Suite

This directory (`swarm2/`, also accessible via the `crazyswarm2/` symlink) contains configuration files, tools, and flight scripts for operating single and multi-agent Crazyflie drone formations on **real hardware (Loco Positioning System)** as well as in **SITL simulation**.

---

## Directory Overview

```text
swarm2/ (alias: crazyswarm2)
├── README.md                  # This guide
├── run_formation.sh           # Main runner script to execute formation scripts in Docker
├── formation_manager.py       # Interactive terminal controller (takeoff, switch shapes, land)
├── config/
│   ├── crazyflies_real.yaml   # Real hardware config (radio URIs, LPS EKF estimator)
│   ├── server_real.yaml       # Real Crazyswarm2 server parameters
│   └── crazyflies_sitl.yaml   # SITL simulation config for virtual testing
├── formations/
│   ├── line_formation.py      # Linear formation with altitude collision avoidance
│   ├── circle_formation.py    # Circular ring perimeter and optional orbit
│   ├── v_formation.py         # Arrowhead / V-shape formation
│   ├── grid_formation.py      # 2D matrix grid
│   └── morph_formation.py     # Continuous airshow sequence (morphs between shapes)
└── tools/
    ├── scan_drones.py         # 2.4GHz radio frequency scanner
    ├── cf_telemetry.py        # Real-time LPS coordinates and battery dashboard
    └── emergency_stop.py      # Immediate motor cutoff service caller
```

---

## 1. Hardware Preparation (Real Drones)

### A. Crazyradio PA USB Permissions (One-time setup)
Linux requires udev rules for non-root users and Docker to access the Crazyradio PA USB dongle:
```bash
./setup_usb_udev.sh
```
*If your Crazyradio PA was already plugged in, unplug and replug it.*

### B. Loco Positioning System (LPS) Setup
Ensure your LPS anchors are powered on and set up in **TDoA2** or **TDoA3** mode.
In `swarm2/config/crazyflies_real.yaml`:
```yaml
all:
  firmware_params:
    stabilizer:
      estimator: 2   # 2 = Extended Kalman Filter (EKF) required for LPS
    loco:
      mode: 1        # 1 = TDoA2, 2 = TDoA3, 3 = TWR
```

### C. Configure Drone URIs
Discover the radio URIs of your powered Crazyflies:
```bash
./scan_real_drones.sh
```
Then update `swarm2/config/crazyflies_real.yaml` with your drones' URIs:
```yaml
robots:
  cf1:  {enabled: true, uri: "radio://0/80/2M/E7E7E7E701", initial_position: [1.0, 1.0, 0.0], type: cf2_lps}
  cf2:  {enabled: true, uri: "radio://0/80/2M/E7E7E7E702", initial_position: [2.0, 1.0, 0.0], type: cf2_lps}
  cf3:  {enabled: true, uri: "radio://0/80/2M/E7E7E7E703", initial_position: [3.0, 1.0, 0.0], type: cf2_lps}
  cf4:  {enabled: true, uri: "radio://0/80/2M/E7E7E7E704", initial_position: [4.0, 1.0, 0.0], type: cf2_lps}
  cf5:  {enabled: true, uri: "radio://0/80/2M/E7E7E7E705", initial_position: [5.0, 1.0, 0.0], type: cf2_lps}
  cf6:  {enabled: true, uri: "radio://0/80/2M/E7E7E7E706", initial_position: [1.0, 2.0, 0.0], type: cf2_lps}
  cf7:  {enabled: true, uri: "radio://0/80/2M/E7E7E7E707", initial_position: [2.0, 2.0, 0.0], type: cf2_lps}
  cf8:  {enabled: true, uri: "radio://0/80/2M/E7E7E7E708", initial_position: [3.0, 2.0, 0.0], type: cf2_lps}
  cf9:  {enabled: true, uri: "radio://0/80/2M/E7E7E7E709", initial_position: [4.0, 2.0, 0.0], type: cf2_lps}
  cf10: {enabled: true, uri: "radio://0/80/2M/E7E7E7E70A", initial_position: [5.0, 2.0, 0.0], type: cf2_lps}
```

---

## 2. Launching ROS 2 Communication

### Start the Crazyswarm2 Server for Real Drones
```bash
./launch_ros2_real.sh
```
This connects to your Crazyradio PA, launches Crazyswarm2, and advertises ROS 2 topics and services.

---

## 3. Communicating via ROS 2 Commands

You can run any ROS 2 command directly from your host terminal using the `./ros2` wrapper:

### Check Active Drones & Topics
```bash
./ros2 topic list
```
You will see topics such as `/cf1/pose`, `/cf1/status`, `/all/takeoff`, `/cf1/takeoff`.

### Stream Live 3D Position from LPS
```bash
./ros2 topic echo /cf1/pose
```

### Check Battery Voltage & Link Quality
```bash
./ros2 topic echo /cf1/status
```

### Direct Flight Service Calls

**Arm Drone Motors (Ready for Flight):**
```bash
# Using convenient script
./arm_drone.sh        # Arm all drones
./arm_drone.sh cf1    # Arm cf1 only

# Or via direct ROS 2 service call
./ros2 service call /cf1/arm crazyflie_interfaces/srv/Arm "{arm: true}"
./ros2 service call /all/arm crazyflie_interfaces/srv/Arm "{arm: true}"
```

**Disarm Drone Motors (Safety Cutoff):**
```bash
# Using convenient script
./disarm_drone.sh     # Disarm all drones
./disarm_drone.sh cf1 # Disarm cf1 only

# Or via direct ROS 2 service call
./ros2 service call /cf1/arm crazyflie_interfaces/srv/Arm "{arm: false}"
./ros2 service call /all/arm crazyflie_interfaces/srv/Arm "{arm: false}"
```

**Takeoff CF1 to 0.5m:**
```bash
./ros2 service call /cf1/takeoff crazyflie_interfaces/srv/Takeoff "{height: 0.5, duration: {sec: 2}}"
```

**Move CF1 to target coordinate (X=1.0, Y=0.5, Z=0.8):**
```bash
./ros2 service call /cf1/go_to crazyflie_interfaces/srv/GoTo "{goal: {x: 1.0, y: 0.5, z: 0.8}, yaw: 0.0, duration: {sec: 3}, relative: false}"
```

**Land CF1:**
```bash
./ros2 service call /cf1/land crazyflie_interfaces/srv/Land "{height: 0.0, duration: {sec: 2}}"
```

**Query or Set Firmware Parameters:**
```bash
# Check active estimator (2 = EKF)
./ros2 param get /cf1 stabilizer.estimator

# Change LED ring effect
./ros2 param set /cf1 ring.effect 16
```

---

## 4. Running Formation Scripts

Once the ROS 2 server is running, execute any formation script in a second terminal:

### Interactive Controller
```bash
./swarm2/run_formation.sh formation_manager.py
```
Provides an interactive menu to takeoff, switch shapes (Line, Circle, V, Grid), hold, and land safely.

### Direct Script Execution
```bash
# Line Formation
./swarm2/run_formation.sh line_formation.py

# Circle Formation
./swarm2/run_formation.sh circle_formation.py

# V-Formation (Arrowhead)
./swarm2/run_formation.sh v_formation.py

# 2D Grid Formation
./swarm2/run_formation.sh grid_formation.py

# Dynamic Multi-Shape Airshow Sequence
./swarm2/run_formation.sh morph_formation.py
```

### Live Telemetry Dashboard
```bash
./swarm2/run_formation.sh tools/cf_telemetry.py
```

---

## 5. Emergency Cutoff

If you need to instantly cut motor power to all drones:
```bash
./cf_emergency.sh
```
Or via ROS 2 CLI:
```bash
./ros2 service call /all/emergency std_srvs/srv/Empty "{}"
```
