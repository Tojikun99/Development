# Project Changelog

## 1. Core Architecture & SITL Integration
* Cloned and embedded `crazyflie-firmware` within the `CrazySim` environment.
* Configured `osrf/ros:humble-desktop` Docker environment with Gazebo Harmonic, MuJoCo, and Crazyswarm2 dependencies.
* Removed git submodules and embedded `CrazySim` and firmware source code directly into the main repository index.
* Configured local X11 connection forwarding in `run_demo.sh` to support GUI rendering for Gazebo and MuJoCo within Docker.
* Resolved `transforms3d` apt/pip package conflicts during the Docker build sequence.

## 2. Firmware & SDK Initialization Patches
* Patched `cflib` (`patch_cflib.py`) to bypass parameter TOC fetching timeouts caused by SITL UDP communication delays.
* Configured Crazyswarm2 ROS server to utilize a persistent TOC cache (`CrazySim/ros2_config/cache`), reducing multi-drone initialization time.
* Updated `run_demo.sh` to compile firmware (`cf2_defconfig` & `crazysim_gz`) dynamically inside the container for the host architecture.
* Optimized `cflib` parameter fetching routines (`self.param.all_updated.call()`) specifically for SITL environments.

## 3. Swarm Logic & Control Fixes
* Modified swarm trajectory logic in `ex7_swarm_wave.py` to stagger altitude transitions by `(i % 4) * 0.3m` for collision avoidance during grid-to-line transitions.
* Replaced `cf.land()` with manual `cf.goTo()` descent to prevent immediate motor cutoff upon ground contact during landing sequences.
* Refactored `ex3_camera_feed.py` to offload ROS 2 image processing to a background thread, preventing blocking of the main flight control loop.
* Adjusted takeoff target heights and durations across examples to ensure stability in physics simulators.

## 4. Telemetry & Quality of Service (QoS)
* Updated ROS 2 subscribers in `ex4_telemetry_logging.py` to match the firmware's `SensorData` QoS profile, enabling reliable logging of `PoseStamped` and `Status` data to CSV.
* Configured `crazyflies.yaml` to ensure firmware logging frequencies for pose (10Hz) and status (1Hz) are explicitly enabled.

## 5. Documentation & Code Cleanup
* Consolidated project documentation into `README.md`.
* Standardized simulator documentation to prioritize Gazebo Harmonic and removed subjective descriptive language.
* Rewrote in-line code comments across Python examples and Bash scripts to follow standard engineering documentation practices.
* Removed 11 deprecated testing scripts and unused files from the repository.
* Reverted the terminal startup banner to the standard ASCII format.
