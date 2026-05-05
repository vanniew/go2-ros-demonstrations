# Come get your coffee (banana) demo
## Description
In a prior project we already developed a servo-based camera tracking using YOLO model to detect a specific object like a banana. For this demo the robot only changed its body pose so (roll, yaw, pitch) so the camera could track the object. We want to take it one step further and integrate the intel realsense depth camera that is provided with the unitree GO2 so the robot can actually move towards the object that it wants to track based on depth data. 

The YOLO model that we use for this demo has been trained on the COCO dataset, so any object that is in the COCO dataset can be used for the demo.  We recommend to pick a distinctive object such as a banana or a cup from the coco dataset so that the robot does not move towards an accidentally discovered object in your room. 

Always ensure that the robot has sufficient free space around it and also make sure you are ready to intervene in case the robot wanders of trajectory. 

## Physical Setup

### Prerequisites
There are two prerequisites:
- D435f realsense camera mounted on the robot
- Physical connectivity between laptop and Unitree GO2

### Camera Installation
The Unitree GO2 EDU includes a D435f realsense camera. Mount the realsense camera on the front of the robot (4 screws and a mounting plate are delivered with the robot). Plug the USB from the realsense into the developer board. 

### Connectivity
The unitree development board can be reached on the following IP address: ```192.168.123.18/24```. Give your laptop an IP address in the same range (for instance ```192.168.123.222``) and test connectivity via ping.
The default username is ```unitree```

Make things easier by adding ```192.168.123.18``` to your localhosts file. 
```bash
cp /etc/hosts /etc/hosts.bak
echo "192.168.123.18 go2" | sudo tee -a /etc/hosts
```

Test you can ping the robot from the laptop ```ping 192.168.123.18``` or ```ping go2``` if you have added the unitree to your hosts file. 

## Environment Setup

### Prerequisites
There are two prerequisites
- ROS master node and ROS Realsense node running on the Unitree GO2
- ROS client node running on Laptop

### Clone repository
Clone this repository on your local laptop and cd into the locally cloned repo. 

### Start ROS Master and Realsense Node on Robot
Terminal window 1
```bash
ssh <username>@<IP Address of your Unitree Go2 Robot>
roscore
```

Terminal window 2
```bash
roslaunch realsense2_camera rs_camera.launch \
enable_infra:=false enable_infra1:=false enable_infra2:=false \
enable_confidence:=false \
align_depth:=true \
depth_width:=640 depth_height:=480 depth_fps:=30 \
color_width:=640 color_height:=480 color_fps:=30
```

Verify ROS operational on the robot
```bash
rostopic list
rostopic info /camera/color/camera_info
rostopic echo /camera/color/camera_info
rostopic hz /camera/color/image_raw
```

### Start ROS Client Node on Laptop

#### Create a docker container for running your ROS Node
From this repository you can build a docker container with all the required prerequisites to run the client node. 
```bash
docker compose build --no-cache ros1-client
```
#### Start the docker contianer
Give permissions for the container to acesss the xhost sysem and start the container. Make sure the robot has enough free space before starting the movement script.
Go to the directory where you have cloned this github repo. 
```bash
xhost +local:root
docker compose run --rm ros1-client
```

#### Initialize the container
Inside the container:
```bash
echo "192.168.123.18 ubuntu" | sudo tee -a /etc/hosts
source /opt/ros/noetic/setup.bash
python3 -c "from unitree_sdk2py.core.channel import ChannelFactoryInitialize; print('unitree ok')"
```
#### Test ros connectivity to robot
```bash
rostopic list
rostopic info /camera/color/camera_info
rostopic echo /camera/color/camera_info
rostopic hz /camera/color/image_raw
```
If topics are empty or no messages received. You may need to restart the realsense node on the robot. 

## Functionality Testing

### Motion Controller and Object Tracking
Before testing the full script we do a quick sanity check of the two key functionalities that we will use in this demo:
- Object detection using YOLO obect tracking on realsense data
- Motion control through a servo controller. 

### Test Object tracking
In the container, start this command. A window will pop up that displays the view from the realsense camera. Verify that object detection is working. 

```python3 /ws/src/realsense_yolo_tracker_OO.py```

CTRL-C to interrupt. 

### Test Motion Controller
In the container, start the below command. The robot will execute a fixed routine in which it will briefly move forward, turn, move backward and change its pose. Make sure you have at least 2m of free space around the robot. 

```python3 /ws/src/go2_controller.py```

## Detect and Walk Demo

### Description
This is the main demo. We will detect an object (the code is configured to follow a cup, but you can change it) and follow it. The robot will move towards the object until it is within distance and then stop. 

WARNING: Ensure you do not have the same object in multiple places in the room or the robot may move unpredictabley towards objects that are not part of you intended demo. 

### Start Demo
Use this coammand to start the demo:
```python3 /ws/src/detect_and_walk_OO.py```


## Other
Original ```readme.md``` can be found in ```src/archive```.

## Todos
1. Miscellaneous:
  - Currently ROS messages from Unitree are being sent from host ubuntu instead from a fixed IP. As a result the client needs to be able to resolve the IP address of Ubunut. We fix this by adding ubuntu to the hosts file of the docker container. In the future a permanent fix would be better.  2
  - Make laptop user part of the docker group
  - Edit code in the IDE directly within the docker container. 
  - Make a backup of the computer on the back of the Unitree 
3. Improve YOLO Tracking, so that you can filter detections based on
  - ClassID - Already supported
  - Maximum distance - to be implemented
  - Minimum confidence - to be implemented
4. Implement Safety/Emergency Stop 
5. Work uncabled. Implement controller on a Jetson Nano that can be mounted on the robot back
6. Customize the YOLO tracker so it tracks a VIVES or interreg Logo
7. Improve YOLO tracking so distance estimates are more accurate
8. Improve the servo controller for robot movement so movement is more smooth. 
9. Currently the robot moves towards a target. Implement pose based whole body tracking (ie. let the robot adjust its pose while standing) when the target is close. 
10. Optimize
  - Resolution of camera image from realsense is relatively small, experiment with different resolutions
  - Time synchronization. Currently we are every 100mseconds detecting a new image target and adjusting the pose via the go2_controller. The detect_and_walk_OO script also has a control loop that sends commands every 100ms to the robot. Those two loops probably interfere and it should be avoided.  