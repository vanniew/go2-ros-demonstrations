# Intel Realsense Integration
In a prior project we already developed a servo-based camera tracking using YOLO model to detect a specific object. We want to take it one step further and integrate the intel realsense depth camera that is provided with the unitree GO2.
The goal is to make the robot move forward based on measured depth data. 

We proceed through the following steps:
1. Camera Installation
2. Configure connectivity between a laptop and the Unitree GO2
3. Understand how camera data is streamed and configured locally on Unitree Go2
4. Access camera data on the laptop through a ros subscriber

## Camera Installation
Mount the provided realsense camera on the front of the robot (4 screws and a mounting plate are delivered with the robot). Plug the USB from the realsense into the developer board. 

## Connectivity
The unitree development board can be reached on the following IP address: ```192.168.123.18/24```. Give your laptop an IP address in the same range (for instance ```192.168.123.222``) and test connectivity via ping.
The default username is ```unitree```

Make things easier by adding ```192.168.123.18``` to your localhosts file. 
```bash
cp /etc/hosts /etc/hosts.bak
echo "192.168.123.18 go2" | sudo tee -a /etc/hosts
```

Setup cursor or your IDE for passwordless SSH access. For cursor you can do this as follows.
1. Add passwordless SSH access. 
```bash
ssh-keygen -t ed25519 -C "your_email_or_label" #Optional if you do not have an SSH key on your machine yet
ssh-copy-id unitree@192.168.123.18/24
```
2. Install the curosr remote-ssh extension
3. Start cursor in the remote environment with
```bash
cursor --folder-uri vscode-remote://ssh-remote+unitree@192.168.123.18
```

## ROS2 Exploration
### Start ROS2
Open a separate SSH shell into the unitree robot. When logging in you will be prompted to select either ROS2 (FOXY) or ROS1 (Noetic). Select ROS2 (FOXY)

### Useful ROS2 commands
Commands to try
```bash
ros2 topic list #Shows available ROS2 topics on the DDS middleware
ros2 nodes list #Displays all the active ROS2 nodes (If you have not started any nodes, this will be empty)
ros2 pkg list #List all available packages on this system
ros2 topic echo /sportmodestate #Displays robot movement information
```

### Bug Fix
If you are unable to get information from ```ros2 topic echo /sportmodestate```, check if the ROS2 environment is completely sourced. If needed add the following line to the .bahsrc. 
```bash
source /unitree/module/graph_pid_ws/install/setup.bash
```

### Intel Realsense
Try following code again and look for a realsense package
```bash
ros2 pkg list
```
In the software version we are using there is no ros2 realsense package. 

## ROS1 Exploration
### Intel Realsense (ROS1 Only)
Apparently Intel Realsense is currently only available as a ROS1 node. We try it out with the following commands

Terminal window 1
```bash
roscore
```

Terminal window 2
```bash
roslaunch realsense2_camera rs_camera.launch \
  enable_infra:=false enable_infra1:=false enable_infra2:=false \
  enable_confidence:=false \
  depth_width:=640 depth_height:=480 depth_fps:=30 \
  color_width:=640 color_height:=480 color_fps:=30

```

Terminal window 3
```bash
rostopic list
```

You should see realsense related topics listed. 

### Useful ROS1 commands
```bash
rostopic list
rostopic info /camera/color/camera_info
rostopic echo /camera/color/camera_info
rostopic hz /camera/color/image_raw
```


## External ROS Node
Start a ROS1 node on your laptop in Docker and connect it to the GO2 ROS master.

### Docker setup (Laptop)
Create a local env file from the template and adjust the laptop IP:
```bash
cp .env.example .env
```

Set `ROS_IP` and `ROS_HOSTNAME` in `.env` to your laptop address on the `192.168.123.0/24` network.

Build and start the ROS1 client container:
```bash
docker compose run --rm ros1-client
```

Inside the container:
```bash
source /opt/ros/noetic/setup.bash
echo "$ROS_MASTER_URI"
rostopic list #Get all topics
rostopic info /camera/color/camera_info #Inspect a specific topic
rostopic echo /camera/color/camera_info #Inspect the actual streamed data
```

If topics do not appear or you do not see the streaming data
1. Laptop can ping `192.168.123.18`
2. `ROS_MASTER_URI` points to `http://192.168.123.18:11311`
3. `ROS_IP` is the laptop IP reachable by GO2
4. In ```rostopic info``` check that the publisher hostname is resolvable from your system. (Fix it, or temporarily add it to hosts using echo ```echo "192.168.123.18 ubuntu" | sudo tee -a /etc/hosts```)

## Start a script to visualize realsense data from the docker container

The repository contains a simple Python viewer at `src/show_realsense_rgb.py` that subscribes to `/camera/color/image_raw` and opens an OpenCV window.

### Enable GUI forwarding for Docker (Linux/X11)
On your laptop host, allow local root containers to connect to X11:
```bash
xhost +local:root
```

### Build and start the container
If the container has not been built yet, build it. 
From this repository root:
```bash
docker compose build ros1-client
```

If the container is not yet running, run it. 
From this repository root:
```bash
docker compose run --rm ros1-client
```

### Run the RGB viewer script
Inside the container:
```bash
source /opt/ros/noetic/setup.bash
python3 /ws/src/show_realsense_rgb.py
```

If everything is configured correctly, a window named `RealSense RGB` should appear and show the live color stream.

Stop the script with `Ctrl+C`.

### YOLO Tracker Script
After you verified that camera is accessible from the laptop with the script above, try the YOLO tracker script.


#### Start ROS Master and Camera Node on the Robot
Terminal window 1
```bash
roscore
```

Terminal window 2
```bash
roslaunch realsense2_camera rs_camera.launch \
  enable_infra:=false enable_infra1:=false enable_infra2:=false \
  enable_confidence:=false \
  align_depth:=true \     # Align depth camera to rgb
  depth_width:=640 depth_height:=480 depth_fps:=30 \
  color_width:=640 color_height:=480 color_fps:=30
```

#### Start the ros-client on the laptop
If the container has not been built yet, build it. Otherwise skip this step. 
```bash
docker compose build ros1-client
```

Give permissions for the container to acesss the xhost sysem and start the container
```bash
xhost +local:root
docker compose run --rm ros1-client
```
#### Inside the container start the script
Inside the container:
```bash
echo "192.168.123.18 ubuntu" | sudo tee -a /etc/hosts
source /opt/ros/noetic/setup.bash
python3 /ws/src/realsense_yolo_tracker.py
```

The script subscribes to `/camera/color/image_raw` and `/camera/aligned_depth_to_color/image_raw`, runs YOLO on the RGB image, and overlays the target offset plus measured depth.
