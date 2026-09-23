#!/bin/bash
set -e

echo "Setting up locale..."
sudo apt update && sudo apt install -y locales
sudo locale-gen en_US en_US.UTF-8
sudo update-locale LC_ALL=en_US.UTF-8 LANG=en_US.UTF-8
export LANG=en_US.UTF-8

echo "Adding ROS 2 apt repository..."
sudo apt install -y software-properties-common
sudo add-apt-repository universe -y
sudo apt update && sudo apt install -y curl
sudo curl -sSL https://raw.githubusercontent.com/ros/rosdistro/master/ros.key -o /usr/share/keyrings/ros-archive-keyring.gpg
echo "deb [arch=$(dpkg --print-architecture) signed-by=/usr/share/keyrings/ros-archive-keyring.gpg] http://packages.ros.org/ros2/ubuntu $(. /etc/os-release && echo $UBUNTU_CODENAME) main" | sudo tee /etc/apt/sources.list.d/ros2.list > /dev/null

echo "Installing ROS 2 Humble Desktop..."
sudo apt update
sudo apt upgrade -y
sudo apt install -y ros-humble-desktop

echo "Installing Gazebo 11 and ROS 2 integration packages..."
sudo apt install -y gazebo ros-humble-gazebo-ros-pkgs

echo "Installing dependencies for sim_cf2 SITL..."
sudo apt install -y cmake build-essential genromfs ninja-build \
    protobuf-compiler libgoogle-glog-dev libeigen3-dev libxml2-utils \
    ros-humble-rmw-cyclonedds-cpp ros-humble-xacro \
    python3-colcon-common-extensions python3-rosdep python3-pip

echo "Initializing rosdep..."
sudo rosdep init || true
rosdep update

echo "=========================================================="
echo "Installation complete! Please source the ROS 2 setup file:"
echo "source /opt/ros/humble/setup.bash"
echo "=========================================================="
