# Unified Dockerfile for Unitree G1 Navigation and Perception System
# Includes: Navigation (Nav2, FAST-LIO), Perception (g1_vis), Bringup

FROM nvidia/cuda:12.2.2-devel-ubuntu22.04

ARG UID=1001
ARG GID=1001
ARG HOST_IP="192.168.123.222"

ENV DEBIAN_FRONTEND=noninteractive
ENV TZ=Asia/Tokyo

# =============================================================================
# STAGE 1: System packages and ROS2 Humble
# =============================================================================

RUN apt-get update && \
    apt-get install -y software-properties-common && \
    add-apt-repository -y ppa:deadsnakes/ppa && \
    add-apt-repository -y universe

RUN apt-get update && \
    apt-get install -y \
    curl gpg less vim wget pciutils libopencv-dev python3-opencv x11-apps libicu-dev unzip \
    xorg xorg-dev git sudo iproute2 ifstat net-tools

# CA certificates for github
RUN mkdir -p /usr/share/ca-certificates/github && \
    echo -n | openssl s_client -showcerts -connect github.com:443 2>/dev/null | \
    sed -ne '/-BEGIN CERTIFICATE-/,/-END CERTIFICATE-/p' > /usr/share/ca-certificates/github/ca.crt && \
    echo "github/ca.crt" >> /etc/ca-certificates.conf && \
    mkdir -p /usr/share/ca-certificates/githubusercontent && \
    echo -n | openssl s_client -showcerts -connect githubusercontent.com:443 2>/dev/null | \
    sed -ne '/-BEGIN CERTIFICATE-/,/-END CERTIFICATE-/p' > /usr/share/ca-certificates/githubusercontent/ca.crt && \
    echo "githubusercontent/ca.crt" >> /etc/ca-certificates.conf && \
    update-ca-certificates

# Install ROS2 Humble
RUN curl -sSL https://raw.githubusercontent.com/ros/rosdistro/master/ros.key -o /usr/share/keyrings/ros-archive-keyring.gpg && \
    echo "deb [arch=$(dpkg --print-architecture) signed-by=/usr/share/keyrings/ros-archive-keyring.gpg] http://packages.ros.org/ros2/ubuntu $(. /etc/os-release && echo $UBUNTU_CODENAME) main" | tee /etc/apt/sources.list.d/ros2.list > /dev/null && \
    apt-get update && \
    apt-get install -y ros-humble-desktop ros-humble-navigation2 ros-humble-nav2-bringup

# Install ROS2 dependencies
RUN apt-get update && apt-get install -y \
    cmake libatlas-base-dev libeigen3-dev libpcl-dev libgoogle-glog-dev \
    libsuitesparse-dev libglew-dev python3-pip \
    ros-humble-tf2 ros-humble-tf2-ros ros-humble-tf2-geometry-msgs \
    ros-humble-cv-bridge ros-humble-pcl-conversions ros-humble-xacro \
    ros-humble-robot-state-publisher ros-humble-rviz2 \
    ros-humble-python-qt-binding ros-humble-rqt ros-humble-rqt-gui \
    ros-humble-rqt-gui-py python3-pyqt5 \
    ros-humble-image-transport ros-humble-image-transport-plugins \
    ros-humble-pcl-ros ros-humble-octomap-server \
    ros-humble-turtlebot3-teleop python3-colcon-common-extensions python3-rosdep \
    ros-humble-rmw-cyclonedds-cpp ros-humble-rosidl-generator-dds-idl \
    ros-humble-foxglove-bridge ros-humble-visualization-msgs

# =============================================================================
# STAGE 2: External SDKs and libraries
# =============================================================================

# Create user (handle existing GID gracefully)
RUN groupadd -g $GID ubuntu || groupadd ubuntu && \
    useradd --create-home --home-dir /home/ubuntu --shell /bin/bash -u $UID -g ubuntu --groups adm,sudo ubuntu && \
    echo ubuntu:ubuntu | chpasswd && \
    echo "ubuntu ALL=(ALL) NOPASSWD:ALL" >> /etc/sudoers
USER ubuntu

# Install Unitree SDK2
WORKDIR /home/ubuntu
RUN git clone https://github.com/unitreerobotics/unitree_sdk2.git -b add_api_for_arm_tasks_in_g1
WORKDIR /home/ubuntu/unitree_sdk2/build
RUN mkdir -p /home/ubuntu/unitree_sdk2/build && \
    cmake .. -DCMAKE_INSTALL_PREFIX=/opt/unitree_robotics && \
    sudo make install

# Install Livox SDK2
WORKDIR /home/ubuntu
RUN git clone https://github.com/Livox-SDK/Livox-SDK2.git
WORKDIR /home/ubuntu/Livox-SDK2/build
RUN mkdir -p /home/ubuntu/Livox-SDK2/build && \
    cmake .. && make -j2 && sudo make install


# Install TEASER++ (point cloud registration)
WORKDIR /home/ubuntu
RUN git clone https://github.com/MIT-SPARK/TEASER-plusplus.git
WORKDIR /home/ubuntu/TEASER-plusplus/build
RUN mkdir -p /home/ubuntu/TEASER-plusplus/build && \
    cmake .. -DBUILD_TEASER_FPFH=ON && \
    make && sudo make install && sudo ldconfig

# =============================================================================
# STAGE 3: ROS2 base packages (FAST-LIO, Livox driver, Unitree ROS2)
# =============================================================================

# Create workspace structure
WORKDIR /home/ubuntu
RUN mkdir -p ros2_ws/src

# Copy all ROS2 packages
COPY --chown=ubuntu:ubuntu src/FAST_LIO /home/ubuntu/ros2_ws/src/FAST_LIO
COPY --chown=ubuntu:ubuntu src/livox_ros_driver2 /home/ubuntu/ros2_ws/src/livox_ros_driver2
COPY --chown=ubuntu:ubuntu src/unitree_ros2 /home/ubuntu/ros2_ws/src/unitree_ros2

WORKDIR /home/ubuntu/ros2_ws

# Build Livox driver first
RUN bash -c "source /opt/ros/humble/setup.bash && \
    colcon build --packages-select livox_ros_driver2 \
    --cmake-args -DROS_EDITION=humble -DHUMBLE_ROS=humble"

# Build FAST-LIO (heavy build)
RUN bash -c "source /opt/ros/humble/setup.bash && \
    source install/setup.bash && \
    colcon build --packages-select fast_lio"

# Build Unitree ROS2 packages
RUN bash -c "source /opt/ros/humble/setup.bash && \
    source install/setup.bash && \
    colcon build --packages-select unitree_api unitree_go unitree_hg"

# =============================================================================
#   Python dependencies for perception
# =============================================================================

RUN pip install --no-cache-dir moondream moondream-station scikit-image "numpy<2"


# =============================================================================
# STAGE 4: ROS2 application packages (navigation, perception, bringup)
# =============================================================================

COPY --chown=ubuntu:ubuntu src/g1_control /home/ubuntu/ros2_ws/src/g1_control
COPY --chown=ubuntu:ubuntu src/g1_nav2 /home/ubuntu/ros2_ws/src/g1_nav2
COPY --chown=ubuntu:ubuntu src/g1_tf /home/ubuntu/ros2_ws/src/g1_tf
COPY --chown=ubuntu:ubuntu src/global_pose_initializer /home/ubuntu/ros2_ws/src/global_pose_initializer

# Copy perception packages
COPY --chown=ubuntu:ubuntu src/g1_vis/vector_list_msgs /home/ubuntu/ros2_ws/src/vector_list_msgs
COPY --chown=ubuntu:ubuntu src/g1_vis/lab_proc /home/ubuntu/ros2_ws/src/lab_proc
COPY --chown=ubuntu:ubuntu src/g1_vis/livox_zbuffer /home/ubuntu/ros2_ws/src/livox_zbuffer

# Copy integration packages (g1_vis_nav removed in phase3_minimal refactor)
COPY --chown=ubuntu:ubuntu src/g1_bringup /home/ubuntu/ros2_ws/src/g1_bringup

# Copy params and config
COPY --chown=ubuntu:ubuntu params /home/ubuntu/ros2_ws/params

# Configure Livox IP
WORKDIR /home/ubuntu/ros2_ws/src/livox_ros_driver2/config
RUN sed -i "s/192.168.123.222/$HOST_IP/" MID360_config.json && \
    sed -i "s/192.168.123.222/$HOST_IP/" MID360_trans_config.json


WORKDIR /home/ubuntu/ros2_ws


# =============================================================================
# STAGE 5: Setup scripts and entrypoint
# =============================================================================

WORKDIR /home/ubuntu

# Copy network configuration (single source of truth)
COPY --chown=ubuntu:ubuntu docker/network.conf /home/ubuntu/network.conf
COPY --chown=ubuntu:ubuntu docker/scripts/configure_cyclonedds.sh /home/ubuntu/configure_cyclonedds.sh

# Copy utility scripts
COPY --chown=ubuntu:ubuntu docker/ros_entrypoint.sh /home/ubuntu/ros_entrypoint.sh
COPY --chown=ubuntu:ubuntu docker/MapNoiseRemoval.py /home/ubuntu/MapNoiseRemoval.py

RUN sudo chmod +x ros_entrypoint.sh configure_cyclonedds.sh *.sh

# Setup .bashrc
RUN echo "" >> .bashrc && \
    echo "# ROS2 Environment" >> .bashrc && \
    echo "source /opt/ros/humble/setup.bash" >> .bashrc && \
    echo "source ~/ros2_ws/install/setup.bash" >> .bashrc && \
    echo "source ~/configure_cyclonedds.sh" >> .bashrc && \
    echo "export RMW_IMPLEMENTATION=rmw_cyclonedds_cpp" >> .bashrc && \
    echo "export ROS_DOMAIN_ID=0" >> .bashrc && \
    echo "" >> .bashrc && \
    echo "echo '=== Unitree G1 Navigation + Perception System ==='" >> .bashrc && \
    echo "echo 'Launch full system:  ros2 launch g1_bringup g1_full.launch.py'" >> .bashrc && \
    echo "echo 'Commands: go | cancel | stop'" >> .bashrc

# Ensure login shells (including docker exec bash -lc) always get DDS NIC pinning.
RUN echo 'source /home/ubuntu/configure_cyclonedds.sh >/dev/null 2>&1 || true' | sudo tee /etc/profile.d/99-cyclonedds.sh >/dev/null && \
    sudo chmod +x /etc/profile.d/99-cyclonedds.sh

# Clean up
RUN sudo apt-get clean && sudo rm -rf /var/lib/apt/lists/*

ENTRYPOINT ["/home/ubuntu/ros_entrypoint.sh"]
CMD ["bash"]
