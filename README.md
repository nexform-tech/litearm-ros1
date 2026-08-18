# litearm-ros1

[ROS1](http://wiki.ros.org/noetic) bridge package for the LiteArm robotic arm.
Wraps [litearm-python](../litearm-python) so the arm shows up as standard ROS
topics, transforms and services: joint states, TCP pose + TF, joint commands,
and `movej`/`movel`/`fk`/`ik` services.

## Features

- 📡 **Publishers** — `/joint_states`, `/litearm/tcp_pose`, TF `base_link → tool0`
- 🎮 **Subscribers** — `/litearm/cmd_joint` (JointState → movej), `/litearm/stop` (E-stop)
- 🛠️ **Services** — `/litearm/movej`, `/litearm/movel`, `/litearm/fk`, `/litearm/ik`,
  `/litearm/get_state` + std_srvs Trigger (`request_stop`/`clear_stop`/`enable`/`disable`)
- 🧪 **ROS-agnostic core** — `bridge.py` + `pose_utils.py` have no `rospy` imports
  and are unit-tested on any machine

> 📖 Full developer guide & API reference: [docs/DEVELOPER_GUIDE.md](docs/DEVELOPER_GUIDE.md)
> · 中文文档：[README.zh-CN.md](README.zh-CN.md)

## Requirements

- ROS **Noetic** (tested) with the standard catkin toolchain
- Python 3.8+ with `rospy`/`roslib`
- [litearm-python](https://pypi.org/project/litearm-python) (pip; **not** rosdep-resolvable)

## Build

```bash
source /opt/ros/noetic/setup.bash
mkdir -p ~/catkin_ws/src && cd ~/catkin_ws/src
git clone <this-repo> litearm_ros1
# install the base SDK into the python used by rospy:
pip install litearm-python        # or: pip install -e /path/to/litearm-python
cd ~/catkin_ws && catkin_make
source ~/catkin_ws/devel/setup.bash
```

> `catkin_make` auto-runs `catkin_python_setup()`, so the Python package
> `litearm_ros1` and the generated messages are installed automatically.

## Launch

```bash
roslaunch litearm_ros1 litearm.launch \
  endpoint:=tcp/192.168.31.237:7447   # address of the litearm-server
```

Inspect the arm state:

```bash
rostopic echo /joint_states
rostopic echo /litearm/tcp_pose
```

Drive a motion:

```bash
# via the subscriber
rostopic pub -1 /litearm/cmd_joint sensor_msgs/JointState \
  '{name: [joint0..joint6], position: [0.1, 0.1, 0.1, 0.1, 0.1, 0.1, 0.1]}'
# or via the service
rosservice call /litearm/movej '{q_target: [0.1, 0.1, 0.1, 0.1, 0.1, 0.1, 0.1], speed: 0.3, settle_s: 0.5}'
```

## Package layout

```text
litearm_ros1/
├── CMakeLists.txt          catkin + message_generation
├── package.xml             catkin package manifest
├── setup.py                catkin_python_setup (installs litearm_ros1 python package)
├── src/litearm_ros1/
│   ├── bridge.py           ROS-agnostic bridge logic (no rospy imports)
│   └── pose_utils.py       pure-Python litearm ⇄ ROS pose conversion
├── nodes/litearm_node.py   rospy bridge node
├── srv/                    custom services: Movej, Movel, Fk, Ik, GetState
├── launch/litearm.launch
├── config/litearm.yaml
└── tests/                  mock unit tests (no ROS required)
```
