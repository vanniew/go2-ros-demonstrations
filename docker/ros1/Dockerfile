FROM ros:noetic-ros-core

# Keep shell interactive and useful for debugging ROS networking.
RUN apt-get update && apt-get install -y --no-install-recommends \
    iproute2 \
    iputils-ping \
    net-tools \
    ros-noetic-message-filters \
    python3-numpy \
    python3-opencv \
    python3-pip \
    && rm -rf /var/lib/apt/lists/*

RUN pip3 install --no-cache-dir ultralytics \
    && pip3 uninstall -y opencv-python opencv-python-headless opencv-contrib-python

SHELL ["/bin/bash", "-c"]

# Source ROS automatically in interactive shells.
RUN echo "source /opt/ros/noetic/setup.bash" >> /root/.bashrc

WORKDIR /ws

CMD ["bash"]
