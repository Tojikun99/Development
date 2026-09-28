#!/bin/bash
set -e

# Resolve script directory
cd "$(dirname "$0")"

# Default configuration
SIMULATOR="mujoco"
CAMERA=""
MODEL=""
NUM_VEHICLES=10
SKIP_CONFIG=false

# Parse arguments
while [[ "$#" -gt 0 ]]; do
    case $1 in
        --sim) SIMULATOR="$2"; shift ;;
        --camera) CAMERA="--camera" ;;
        --model) MODEL="$2"; shift ;;
        -n|--num-vehicles) NUM_VEHICLES="$2"; shift ;;
        --skip-config) SKIP_CONFIG=true ;;
        -h|--help)
            echo "Usage: ./run_demo.sh [options]"
            echo "Options:"
            echo "  --sim <mujoco|gazebo>   Select simulator backend (default: mujoco)"
            echo "  --camera                Enable camera rendering"
            echo "  --model <model_name>    Specify drone model (e.g. cf2x_T350, indoor_urdf)"
            echo "  -n, --num-vehicles <N>  Number of simulated drones (default: 10)"
            echo "  --skip-config           Skip the defconfig GUI and use existing config"
            echo "  -h, --help              Show this help message"
            exit 0
            ;;
        *) echo "Unknown parameter passed: $1"; exit 1 ;;
    esac
    shift
done

if [[ "$SIMULATOR" != "mujoco" && "$SIMULATOR" != "gazebo" ]]; then
    echo "Error: --sim must be either 'mujoco' or 'gazebo'"
    exit 1
fi

# Reset terminal state
printf "\033[0m\033]8;;\033\\"

echo "=========================================================================="
echo "               Crazyflie SITL Simulation Environment"
echo "=========================================================================="
echo " Firmware  : Bitcraze SITL Master"
echo " Physics   : $SIMULATOR"
echo " ROS 2     : Crazyswarm2 (Humble)"
echo " SDK       : cflib / cfclient"
echo "=========================================================================="

# Allow local X11 connections for the simulator & defconfig GUI
xhost +local:root >/dev/null 2>&1 || xhost + >/dev/null 2>&1 || true

echo "[0/3] Initializing Submodules..."
git submodule update --init --recursive

echo "[1/3] Starting Docker Environment..."
cd docker
docker compose up -d
cd ..

echo "[2/3] Building SITL Firmware..."
# If not skipping configuration, open guiconfig GUI first
if [ "$SKIP_CONFIG" = false ]; then
    echo "--------------------------------------------------------------------------"
    echo " Launching Firmware Defconfig GUI (guiconfig)..."
    echo " Customize firmware features, Save (Ctrl+S), and close the window to build."
    echo "--------------------------------------------------------------------------"
    docker exec -e DISPLAY="$DISPLAY" -e QT_X11_NO_MITSHM=1 crazyflie_sitl bash -c \
        "git config --global --add safe.directory '*' && cd /CrazySim/crazyflie-firmware && [ ! -f .config ] && make cf2_defconfig || true; guiconfig Kconfig"
else
    echo "Skipping defconfig GUI (--skip-config was specified)."
fi

echo "Compiling SITL Firmware..."
docker exec crazyflie_sitl bash -c \
    "git config --global --add safe.directory '*' && cd /CrazySim/crazyflie-firmware && echo '{\"tag\": \"SITL\"}' > build_info.json && [ ! -f .config ] && make cf2_defconfig || true; make silentoldconfig && mkdir -p sitl_make/build && cd sitl_make/build && cmake .. && make -j\$(nproc) cf2 crazysim_gz"

# Detect models in workspace/ directory
WORKSPACE_MODELS=()
if [ -d "workspace" ]; then
    for dir in workspace/*/; do
        if [ -d "$dir" ]; then
            urdf_file=$(find "$dir" -maxdepth 2 -name "*.urdf" 2>/dev/null | head -n 1)
            if [ -n "$urdf_file" ]; then
                model_name=$(basename "$dir")
                WORKSPACE_MODELS+=("$model_name")
            fi
        fi
    done
fi

# Model Selection
SELECTED_MODEL=""

if [ -n "$MODEL" ]; then
    # Model passed as CLI argument
    case "$MODEL" in
        "indoor Urdf"|"indoor_urdf"|"indoor")
            SELECTED_MODEL="indoor_urdf"
            ;;
        *)
            SELECTED_MODEL="$MODEL"
            ;;
    esac
else
    # Interactive menu for model selection
    echo ""
    echo "=========================================================================="
    echo "                    Simulation Model Selection"
    echo "=========================================================================="
    echo " Select drone model to simulate:"
    if [ "$SIMULATOR" == "gazebo" ]; then
        echo "   1) Default Crazyflie (crazyflie)"
        echo "   2) Crazyflie Thrust Upgrade (crazyflie_thrust_upgrade)"
    else
        echo "   1) Default Crazyflie (cf2x_T350)"
        echo "   2) Crazyflie Variants (cf2x_L250, cf2x_P250, cf21B_500)"
    fi

    idx=3
    declare -A WS_MAP
    for wm in "${WORKSPACE_MODELS[@]}"; do
        echo "   $idx) [Workspace URDF] $wm"
        WS_MAP[$idx]="$wm"
        idx=$((idx + 1))
    done
    echo "=========================================================================="

    read -p "Enter choice [1-$((idx - 1))] (default: 1): " choice
    choice=${choice:-1}

    if [ "$choice" -eq 1 ]; then
        if [ "$SIMULATOR" == "gazebo" ]; then
            SELECTED_MODEL="crazyflie"
        else
            SELECTED_MODEL="cf2x_T350"
        fi
    elif [ "$choice" -eq 2 ]; then
        if [ "$SIMULATOR" == "gazebo" ]; then
            SELECTED_MODEL="crazyflie_thrust_upgrade"
        else
            echo "Choose variant: 1) cf2x_L250  2) cf2x_P250  3) cf21B_500"
            read -p "Select variant [1-3] (default: 1): " vchoice
            vchoice=${vchoice:-1}
            case "$vchoice" in
                2) SELECTED_MODEL="cf2x_P250" ;;
                3) SELECTED_MODEL="cf21B_500" ;;
                *) SELECTED_MODEL="cf2x_L250" ;;
            esac
        fi
    elif [ -n "${WS_MAP[$choice]}" ]; then
        ws_name="${WS_MAP[$choice]}"
        case "$ws_name" in
            "indoor Urdf"|"indoor_urdf")
                SELECTED_MODEL="indoor_urdf"
                ;;
            *)
                # Format model identifier without spaces
                SELECTED_MODEL=$(echo "$ws_name" | tr ' ' '_')
                ;;
        esac
    else
        echo "Invalid selection, defaulting to standard Crazyflie model."
        if [ "$SIMULATOR" == "gazebo" ]; then
            SELECTED_MODEL="crazyflie"
        else
            SELECTED_MODEL="cf2x_T350"
        fi
    fi
fi

# TTY detection for docker exec
DOCKER_IT="-i"
if [ -t 0 ] && [ -t 1 ]; then
    DOCKER_IT="-it"
fi

echo ""
echo "[3/3] Launching $SIMULATOR Backend..."
echo " Active Model : $SELECTED_MODEL"
echo " Vehicles     : $NUM_VEHICLES"
echo "--------------------------------------------------------------------------"

if [ "$SIMULATOR" == "gazebo" ]; then
    docker exec $DOCKER_IT crazyflie_sitl bash -c \
        "cd /CrazySim/crazyflie-firmware && bash tools/crazyflie-simulation/simulator_files/gazebo/launch/sitl_multiagent_square.sh -n $NUM_VEHICLES -m $SELECTED_MODEL"
else
    docker exec $DOCKER_IT crazyflie_sitl bash -c \
        "cd /CrazySim/crazyflie-firmware && bash tools/crazyflie-simulation/simulator_files/mujoco/launch/sitl_multiagent_square.sh -n $NUM_VEHICLES -m $SELECTED_MODEL --vis $CAMERA"
fi
