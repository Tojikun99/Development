# Crazyflie SITL — User Documentation

A complete Software-In-The-Loop (SITL) simulation environment for Bitcraze Crazyflie drones, running inside Docker. No physical hardware required.

---

## Technology Stack

| Component | Version | Source |
|---|---|---|
| **Crazyflie Firmware** | SITL master | [github.com/bitcraze/crazyflie-firmware](https://github.com/bitcraze/crazyflie-firmware) |
| **CrazySim** | v1.0 | [github.com/gtfactslab/CrazySim](https://github.com/gtfactslab/CrazySim) |
| **Physics Engine** | MuJoCo v3.13 / Gazebo Harmonic | [mujoco.org](https://mujoco.org) / [gazebosim.org](https://gazebosim.org) |
| **ROS 2 Framework** | Crazyswarm2 (Humble) | [imrclab.github.io/crazyswarm2](https://imrclab.github.io/crazyswarm2) |
| **Python SDK** | cflib v0.1.33 / cfclient | [github.com/bitcraze/crazyflie-clients-python](https://github.com/bitcraze/crazyflie-clients-python) |
| **Container** | Ubuntu 22.04 + ROS 2 Humble | Docker |

---

## Prerequisites

- **Docker** — Install via `./get-docker.sh` or from [docs.docker.com](https://docs.docker.com/engine/install/)
- **X11** display server (for the simulator GUI window)
- **cfclient** (optional) — to connect a ground-station GUI to the simulated drones

---

## Directory Structure

```
crazyflie-SITL/
├── run_demo.sh              # Main launcher — starts Docker + simulation
├── launch_ros2_sitl.sh      # Starts the Crazyswarm2 ROS 2 server (step 2)
├── examples/                # Ready-to-run flight scripts
│   ├── ex1_single_rectangle.py
│   ├── ex3_camera_feed.py
│   ├── ex4_telemetry_logging.py
│   └── ex7_swarm_wave.py
├── docker/
│   ├── Dockerfile           # Container definition
│   ├── patch_cflib.py       # Runtime patches for cflib/Crazyswarm2
│   └── setup.sh             # Firmware clone & build inside container
└── CrazySim/
    └── ros2_config/
        └── crazyflies.yaml  # Drone count, ports, and initial positions
```

---

## Quickstart

### Step 1 — Launch the Simulation

```bash
# Gazebo Harmonic
./run_demo.sh --sim gazebo

# MuJoCo
./run_demo.sh

# MuJoCo with AI-deck camera stream enabled (required for ex3)
./run_demo.sh --camera
```

> [!IMPORTANT]
> The `--camera` flag is **MuJoCo-only**. Do **not** combine it with `--sim gazebo`.
> When the camera is active you will see in the terminal:
> `[crazysim] Agent 0: camera frames → udp://127.0.0.1:5200`

This will:
1. Build and start the Docker container
2. Compile the Crazyflie firmware (SITL target)
3. Spawn **10 drones** in a grid and open the physics engine GUI

> [!NOTE]
> Leave this terminal running. The simulator runs in the foreground here.

---

### Step 2 — Start the ROS 2 Server

Open a **second terminal**:

```bash
./launch_ros2_sitl.sh
```

This starts the `Crazyswarm2` server which bridges the ROS 2 topics to the UDP firmware sockets. Required for all Python examples (except `ex3`).

> [!NOTE]
> Leave this terminal running too.

---

### Step 3 — Run an Example

Open a **third terminal** and run any example script:

```bash
./examples/run_ex1_single_rectangle.sh
./examples/run_ex3_camera_feed.sh
./examples/run_ex4_telemetry_logging.sh
./examples/run_ex7_swarm_wave.sh
```

---

## Connecting cfclient

You can connect the official Bitcraze **cfclient** ground-station GUI directly to any simulated drone:

1. Open `cfclient` on your host
2. In the connection dialog, enter the URI: `udp://127.0.0.1:19850`
3. Click **Connect**

Each drone runs on its own UDP port:

| Drone | Port |
|---|---|
| cf0 | `19850` |
| cf1 | `19851` |
| cf2 | `19852` |
| ... | ... |
| cf9 | `19859` |

You can change flight parameters, view logs, and visualize attitude live through cfclient just as you would with real hardware.

---

## Configuration

### Change the Number of Drones

Edit `run_demo.sh` — find the line at the bottom and change `-n 10`:

```bash
# MuJoCo
bash ... sitl_multiagent_square.sh -n 10 --vis

# Gazebo
bash ... sitl_multiagent_square.sh -n 10
```

Then update `CrazySim/ros2_config/crazyflies.yaml` to match. Each drone needs a `cfN` entry with its port `1985N`.

### Change PID / Flight Parameters

The firmware parameters are compiled from `CrazySim/crazyflie-firmware/src/`. Key files:

- **Stabilizer PIDs** — `src/modules/src/stabilizer.c`
- **Power distribution** — `src/modules/src/power_distribution_sitl.c`
- **Platform defaults** — `src/platform/interface/platform_defaults_sitl.h`

After editing, the firmware is rebuilt automatically on the next `./run_demo.sh`.

---

## Examples Reference

### ex1 — Single Drone Rectangle
> **Requires:** `run_demo.sh` + `launch_ros2_sitl.sh`

Flies `cf0` in a 1×1 meter rectangle at 0.5m altitude using the Crazyswarm2 high-level commander.

**Concepts demonstrated:** `takeoff()`, `goTo()` with absolute coordinates, `land()`

```bash
./examples/run_ex1_single_rectangle.sh
```

---

### ex3 — Camera Feed Viewer
> **Requires:** `./run_demo.sh --camera` (MuJoCo only — **not** compatible with `--sim gazebo`)

Listens on UDP port `5200` for raw image frames from the simulated AI-Deck camera and displays them live using OpenCV.

**Concepts demonstrated:** UDP socket programming, raw frame reconstruction, OpenCV display

```bash
# Step 1: Launch with camera enabled
./run_demo.sh --camera

# Step 2: In a new terminal, run the viewer
./examples/run_ex3_camera_feed.sh
```

> [!TIP]
> Confirm the camera stream is active by looking for this line in the simulator terminal:
> `[crazysim] Agent 0: camera frames → udp://127.0.0.1:5200`

---

### ex4 — Telemetry Logging
> **Requires:** `run_demo.sh` + `launch_ros2_sitl.sh`

Takes off and hovers for 10 seconds while simultaneously logging pose and battery data from the ROS 2 topics (`/cf0/pose`, `/cf0/status`) to a CSV file.

**Output file:** `examples/flight_log.csv`

**Concepts demonstrated:** ROS 2 subscriptions, multithreaded executor, CSV logging, mixed flight + telemetry

```bash
./examples/run_ex4_telemetry_logging.sh
```

---

### ex7 — Swarm Wave
> **Requires:** `run_demo.sh` + `launch_ros2_sitl.sh`

All 10 drones arrange themselves in a horizontal line, then perform a continuous sinusoidal wave for 15 seconds by streaming `cmdPosition` setpoints at 10Hz with staggered phase offsets.

**Concepts demonstrated:** Continuous setpoint streaming, `cmdPosition()`, swarm kinematics, mathematical phase offsets

```bash
./examples/run_ex7_swarm_wave.sh
```

---

## Stopping Everything

```bash
# Stop the simulation and container
cd docker && docker compose down

# Or just Ctrl+C in the run_demo.sh terminal
```

---

## Troubleshooting

| Problem | Solution |
|---|---|
| `Connection refused` errors in ROS 2 server | The firmware is still starting. Wait a few seconds and retry `./launch_ros2_sitl.sh` |
| Simulator GUI doesn't open | Run `xhost +` on your host, then re-run `./run_demo.sh` |
| Drones don't takeoff in examples | Make sure **both** `run_demo.sh` AND `launch_ros2_sitl.sh` are running |
| `Warning: No joystick found!` | Safe to ignore — this is just a notice that no gamepad is connected |
| Container already running error | Run `cd docker && docker compose down` first |

---

## Architecture Overview

```
┌─────────────────────────────────────────────────────────┐
│                    Host Machine                          │
│  cfclient ──── UDP:19850..19859 ────────────────────┐   │
│  Python Scripts (examples/)                         │   │
│  launch_ros2_sitl.sh                                │   │
└─────────────────────────────────────────────────────│───┘
                                                      │
┌─────────────────────────────────────────────────────│───┐
│                 Docker Container                     │   │
│                                                     │   │
│  ┌──────────────────┐    ┌────────────────────┐    │   │
│  │ Crazyswarm2      │    │ Crazyflie Firmware │◄───┘   │
│  │ (ROS 2 Server)   │◄──►│ (SITL x10)        │        │
│  └──────────────────┘    └─────────┬──────────┘        │
│                                    │ actuator cmds      │
│                           ┌────────▼──────────┐        │
│                           │ CrazySim          │        │
│                           │ (MuJoCo/Gazebo)   │        │
│                           └───────────────────┘        │
└────────────────────────────────────────────────────────┘
```
