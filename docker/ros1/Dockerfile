FROM ros:noetic-ros-core

# Keep the editable Unitree SDK importable when scripts run from /ws/src.
ENV PYTHONPATH=/opt/unitree_sdk2_python:${PYTHONPATH}

# Keep shell interactive and useful for debugging ROS networking.
RUN apt-get update && apt-get install -y --no-install-recommends \
    build-essential \
    cmake \
    git \
    iproute2 \
    iputils-ping \
    net-tools \
    ros-noetic-message-filters \
    python3-numpy \
    python3-opencv \
    python3-pip \
    && rm -rf /var/lib/apt/lists/*

RUN git clone --depth 1 https://github.com/unitreerobotics/unitree_sdk2_python.git /opt/unitree_sdk2_python \
    && pip3 install --no-cache-dir -e /opt/unitree_sdk2_python

RUN pip3 install --no-cache-dir ultralytics \
    && pip3 uninstall -y opencv-python opencv-python-headless opencv-contrib-python

SHELL ["/bin/bash", "-c"]

# Source ROS automatically in interactive shells.
RUN echo "source /opt/ros/noetic/setup.bash" >> /root/.bashrc

WORKDIR /ws

CMD ["bash"]
