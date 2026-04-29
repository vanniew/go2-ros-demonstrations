FROM ros:noetic-ros-core

# Keep shell interactive and useful for debugging ROS networking.
RUN apt-get update && apt-get install -y --no-install-recommends \
    iproute2 \
    iputils-ping \
    net-tools \
    python3-numpy \
    python3-opencv \
    python3-pip \
    && rm -rf /var/lib/apt/lists/*

SHELL ["/bin/bash", "-c"]

# Source ROS automatically in interactive shells.
RUN echo "source /opt/ros/noetic/setup.bash" >> /root/.bashrc

WORKDIR /ws

CMD ["bash"]
