FROM osrf/ros:humble-desktop

# Install system dependencies
RUN apt-get update && apt-get install -y \
    cmake build-essential genromfs ninja-build \
    protobuf-compiler libgoogle-glog-dev libeigen3-dev libxml2-utils \
    ros-humble-rmw-cyclonedds-cpp ros-humble-xacro \
    ros-humble-crazyflie ros-humble-tf-transformations ros-humble-motion-capture-tracking \
    python3-colcon-common-extensions python3-rosdep python3-pip \
    psmisc libgsl-dev git wget lsb-release gnupg \
    libgtk2.0-dev libcanberra-gtk-module \
    && rm -rf /var/lib/apt/lists/*

# Install Gazebo Harmonic
RUN wget https://packages.osrfoundation.org/gazebo.gpg -O /usr/share/keyrings/pkgs-osrf-archive-keyring.gpg && \
    echo "deb [arch=$(dpkg --print-architecture) signed-by=/usr/share/keyrings/pkgs-osrf-archive-keyring.gpg] http://packages.osrfoundation.org/gazebo/ubuntu-stable $(lsb_release -cs) main" | tee /etc/apt/sources.list.d/gazebo-stable.list > /dev/null && \
    apt-get update && apt-get install -y gz-harmonic && \
    rm -rf /var/lib/apt/lists/*

# Clone and build Crazyswarm2 from source (provides Python API & SITL UDP Backend)
RUN mkdir -p /ros2_ws/src && \
    cd /ros2_ws/src && \
    git clone --recursive https://github.com/IMRCLab/crazyswarm2.git && \
    cd /ros2_ws && \
    /bin/bash -c "source /opt/ros/humble/setup.bash && colcon build --symlink-install"


# Install python dependencies for cfclient, cflib, and MuJoCo
RUN pip3 install --upgrade pip
# Remove conflicting apt version of transforms3d before pip install
RUN rm -rf /usr/lib/python3/dist-packages/transforms3d*
RUN pip3 install pyusb pyzmq transformations transforms3d posix_ipc Jinja2 mujoco "numpy<2.0.0" tomli rowan opencv-python

# Setup script for dependencies
COPY setup.sh /setup.sh

# Run setup to clone and build components
RUN chmod +x /setup.sh && /setup.sh

# Apply runtime patches to cflib to fix SITL initialization delays and swarm stagger
COPY patch_cflib.py /patch_cflib.py
RUN python3 /patch_cflib.py

# Add entrypoint script
COPY entrypoint.sh /entrypoint.sh
RUN chmod +x /entrypoint.sh

# Configure Crazyswarm2 to use a persistent TOC cache to bypass initialization delays
RUN sed -i "s/rw_cache='.\/cache'/rw_cache='\/CrazySim\/ros2_config\/cache'/g" /ros2_ws/src/crazyswarm2/crazyflie_server_py/crazyflie_server_py/crazyflie_server.py

# Optimize cflib parameter fetching for SITL environments
RUN sed -i 's/self.param.request_update_of_all_params()/self.param.all_updated.call()/g' /usr/local/lib/python3.10/dist-packages/cflib/crazyflie/__init__.py

RUN apt-get update && apt-get install -y python-is-python3

ENTRYPOINT ["/entrypoint.sh"]
CMD ["bash"]
