# litearm-ros1

A [ROS1](http://wiki.ros.org/noetic) bridge package for the **LiteArm** robotic
arm. It wraps [litearm-python](https://pypi.org/project/litearm-python) so the
arm appears as standard ROS topics, transforms and services: joint states, TCP
pose + TF, joint commands, and `movej`/`movel`/`fk`/`ik` services.

```text
ROS topics / services ──→ litearm_node.py ──→ LiteArmBridge ──→ litearm.Arm ──→ litearm-server
```

> 📖 Full developer guide & API reference: [docs/DEVELOPER_GUIDE.md](docs/DEVELOPER_GUIDE.md)
> · 中文文档：[README.zh-CN.md](README.zh-CN.md)

---

## Table of contents

- [Overview & architecture](#overview--architecture)
- [Requirements](#requirements)
- [Install & build](#install--build)
- [Launch](#launch)
- [Node interface](#node-interface)
- [Usage examples](#usage-examples)
- [TF & visualization](#tf--visualization)
- [Troubleshooting](#troubleshooting)
- [Package layout](#package-layout)
- [Documentation & license](#documentation--license)

---

## Overview & architecture

`litearm-ros1` is a standard **catkin** package. A single node,
`litearm_node.py`, connects to a running **litearm-server** over its Zenoh
endpoint and relays data between ROS and the arm:

| Direction | ROS side | Arm side |
|---|---|---|
| Out (state) | `/joint_states`, `/litearm/tcp_pose`, `/tf` | `Arm.get_state()`, `Arm.get_tcp_pose()` |
| In (command) | `/litearm/cmd_joint`, `/litearm/stop` | `Arm.movej()`, `Arm.request_stop()` |
| In (service) | `/litearm/movej`, `/litearm/movel`, `/litearm/fk`, `/litearm/ik`, `/litearm/get_state`, `/litearm/request_stop`, `/litearm/clear_stop`, `/litearm/enable`, `/litearm/disable` | `Arm.*` RPCs |

The bridge logic lives in `src/litearm_ros1/bridge.py` + `pose_utils.py`, which
contain **no `rospy` imports** — they work on plain dicts/tuples, are shared
with the ROS2 bridge, and can be unit-tested on any machine without ROS.

## Requirements

| Item | Requirement |
|---|---|
| ROS | **Noetic** (tested) with the standard catkin toolchain |
| Python | 3.8+ with `rospy` / `roslib` |
| Base SDK | `litearm-python` (pip; **not** rosdep-resolvable) |
| Runtime | A reachable **litearm-server** (Zenoh endpoint, e.g. `tcp/192.168.31.237:7447`) |

> `litearm-python` talks to litearm-server over Zenoh; the server owns the
> actual hardware or simulation. Make sure it is running before launch.

## Install & build

```bash
source /opt/ros/noetic/setup.bash
mkdir -p ~/catkin_ws/src && cd ~/catkin_ws/src
git clone git@github.com:nexform-tech/litearm-ros1.git litearm_ros1

# install the base SDK into the python that rospy uses (see note below):
pip install litearm-python        # or: pip install -e /path/to/litearm-python

cd ~/catkin_ws && catkin_make
source ~/catkin_ws/devel/setup.bash
```

- `catkin_make` runs `catkin_python_setup()`, so the Python package
  `litearm_ros1` and the generated message/service classes are installed into
  the devel space automatically — no extra step.
- **Install the SDK into the right interpreter.** The node imports `litearm`,
  so `litearm-python` must be importable from the same python that runs rospy.
  On a stock Noetic install, that is usually the system python:
  `sudo python3 -m pip install litearm-python` (if the default `pip` is a
  conda/venv python, rospy may not be in it).
- If the node fails at import with a protobuf error, upgrade the ROS python
  environment with `protobuf>=7.35.1`.

Run the mock unit tests on any machine (no ROS required):

```bash
cd litearm_ros1 && PYTHONPATH=src python3 -m pytest tests/ -q
```

## Launch

```bash
roslaunch litearm_ros1 litearm.launch \
  endpoint:=tcp/192.168.31.237:7447   # address of the litearm-server
```

The launch file accepts the following arguments (defaults come from
`config/litearm.yaml`, which is merged as private node parameters):

| Arg | Default | Meaning |
|---|---|---|
| `endpoint` | `tcp/192.168.31.237:7447` | Zenoh endpoint of the litearm-server |
| `arm_id` | `armA` | Arm id registered on the server |
| `loop_hz` | `50.0` | State publish rate in Hz |
| `cmd_speed` | `0.5` | Default joint move speed (0..1) |

All parameters can also be overridden in `config/litearm.yaml` or passed as
`~param` values (see [Parameters](#parameters)).

## Node interface

### Publishers

| Topic | Type | Contents |
|---|---|---|
| `/joint_states` | `sensor_msgs/JointState` | `q` / `dq` / `tau` published at `loop_hz` |
| `/litearm/tcp_pose` | `geometry_msgs/PoseStamped` | TCP pose in `base_frame` |
| `/tf` | `tf2_msgs/TFMessage` | `base_frame → tcp_frame` transform |

### Subscribers

| Topic | Type | Action |
|---|---|---|
| `/litearm/cmd_joint` | `sensor_msgs/JointState` | `movej(position, speed=cmd_speed)` |
| `/litearm/stop` | `std_msgs/Empty` | Emergency stop: `request_stop()` |

### Services

Custom services (`srv/*.srv`). Every response carries `success` + `message`.

| Service | Request | Response |
|---|---|---|
| `/litearm/movej` | `float64[] q_target, float64 speed, float64 settle_s` | `bool success, string message` |
| `/litearm/movel` | `geometry_msgs/Pose pose, float64 speed, float64 settle_s` | `bool success, string message` |
| `/litearm/fk` | `float64[] q` | `geometry_msgs/Pose pose, bool success, string message` |
| `/litearm/ik` | `geometry_msgs/Pose pose, float64[] q_seed` | `float64[] q, bool success, string message` |
| `/litearm/get_state` | *(empty)* | `float64[] q/dq/tau, string state, bool fault, string message` |
| `/litearm/request_stop` | `std_srvs/Trigger` | `bool success, string message` |
| `/litearm/clear_stop` | `std_srvs/Trigger` | `bool success, string message` |
| `/litearm/enable` | `std_srvs/Trigger` | `bool success, string message` |
| `/litearm/disable` | `std_srvs/Trigger` | `bool success, string message` |

### Parameters

All are private node parameters (`~name`), with the defaults below:

| Param | Default | Meaning |
|---|---|---|
| `endpoint` | `tcp/192.168.31.237:7447` | Zenoh endpoint of the litearm-server |
| `arm_id` | `armA` | Arm id registered on the server |
| `loop_hz` | `50.0` | State publish rate in Hz |
| `cmd_speed` | `0.5` | Default joint move speed (0..1) used by `/litearm/cmd_joint` |
| `joint_names` | `joint0 … joint6` | Joint names used in `/joint_states` |
| `base_frame` | `base_link` | Frame of the robot base |
| `tcp_frame` | `tool0` | Frame of the tool center point |

## Usage examples

### Inspect the arm state

```bash
rostopic echo /joint_states
rostopic echo /litearm/tcp_pose
rosrun tf tf_echo base_link tool0     # live TF between the two frames
```

### Drive a joint-space motion (topic)

```bash
rostopic pub -1 /litearm/cmd_joint sensor_msgs/JointState \
  '{name: [joint0, joint1, joint2, joint3, joint4, joint5, joint6], \
    position: [0.1, 0.1, 0.1, 0.1, 0.1, 0.1, 0.1]}'
```

`position` is passed to `movej()` with the node's `cmd_speed`.

### Drive a joint-space motion (service)

```bash
rosservice call /litearm/movej \
  '{q_target: [0.1, 0.1, 0.1, 0.1, 0.1, 0.1, 0.1], speed: 0.3, settle_s: 0.5}'
```

`q_target` holds 7 joint positions, `speed` is a normalized velocity in `0..1`,
and `settle_s` is the dwell time after the motion settles.

### Move to a Cartesian pose

```bash
rosservice call /litearm/movel \
  '{pose: {position: {x: 0.25, y: 0.0, z: 0.35}, \
    orientation: {x: 0.0, y: 0.0, z: 0.0, w: 1.0}}, speed: 0.3, settle_s: 0.5}'
```

The pose is a `geometry_msgs/Pose` in the `base_frame`; orientation is a
quaternion `(x, y, z, w)`.

### Forward / inverse kinematics

```bash
# FK: joints → TCP pose
rosservice call /litearm/fk '{q: [0.0, 0.0, 0.0, 0.0, 0.0, 0.0, 0.0]}'

# IK: TCP pose → joints (q_seed is optional, helps pick a solution)
rosservice call /litearm/ik \
  '{pose: {position: {x: 0.25, y: 0.0, z: 0.35}, \
    orientation: {x: 0.0, y: 0.0, z: 0.0, w: 1.0}}, \
    q_seed: [0.0, 0.0, 0.0, 0.0, 0.0, 0.0, 0.0]}'
```

### Read the full state

```bash
rosservice call /litearm/get_state
# → q, dq, tau arrays, state string, fault bool, message
```

### Emergency stop and recovery

```bash
# immediate stop (topic):
rostopic pub -1 /litearm/stop std_msgs/Empty '{}'
# or as a service:
rosservice call /litearm/request_stop

# clear the stop once it is safe to move again:
rosservice call /litearm/clear_stop
```

### Enable / disable

```bash
rosservice call /litearm/enable
rosservice call /litearm/disable
```

## TF & visualization

The node broadcasts a static transform `base_link → tool0` at every state
update, so any TF consumer can track the arm. To visualize:

```bash
rosrun rviz rviz
# Add → TF, set the fixed frame to base_link
```

> This package does not ship a URDF or a MoveIt configuration — it exposes the
> live TF `base_link → tool0` and the `/litearm/tcp_pose` topic, which is enough
> to visualize the arm pose. If you have a URDF for your LiteArm, match its
> base/tool frame names via `base_frame` / `tcp_frame`.

## Troubleshooting

| Symptom | Likely cause / fix |
|---|---|
| `ModuleNotFoundError: No module named 'litearm'` | `litearm-python` is installed into a different python than rospy. `sudo python3 -m pip install litearm-python`. |
| Import error mentioning `protobuf` | Upgrade the ROS python: `python3 -m pip install 'protobuf>=7.35.1'`. |
| No data on `/joint_states` | litearm-server unreachable. Check `endpoint` (`tcp/<host>:<port>`), that the server is up, and that `arm_id` matches a registered arm. |
| `movej` returns `success: True` but the arm does not move | Check the arm state via `/litearm/get_state`; the arm may be disabled or in a stop state — call `/litearm/enable` / `/litearm/clear_stop`. |
| Commands feel stuck / queued | `movej`/`movel` are **blocking** RPCs — the node (and a `/litearm/cmd_joint` publish) blocks until the motion finishes. Issue commands at a sensible rate. |
| `catkin_make` fails with missing message packages | Ensure `message_generation`, `geometry_msgs`, `sensor_msgs`, `std_msgs`, `std_srvs`, `tf` are installed (usually present with a desktop-full ROS1 install). |

## Package layout

```text
litearm_ros1/
├── CMakeLists.txt          catkin + message_generation
├── package.xml             catkin package manifest
├── setup.py                catkin_python_setup (installs the python package)
├── src/litearm_ros1/
│   ├── bridge.py           ROS-agnostic bridge logic (no rospy imports)
│   └── pose_utils.py       pure-Python litearm ⇄ ROS pose conversion
├── nodes/litearm_node.py   rospy bridge node
├── srv/                    custom services: Movej, Movel, Fk, Ik, GetState
├── launch/litearm.launch
├── config/litearm.yaml
└── tests/                  mock unit tests (no ROS required)
```

## Documentation & license

- Developer guide & API reference (interface details, pose conventions, core
  internals): [docs/DEVELOPER_GUIDE.md](docs/DEVELOPER_GUIDE.md)
- 中文使用说明：[README.zh-CN.md](README.zh-CN.md)
- License: see `package.xml` (`Proprietary`).
