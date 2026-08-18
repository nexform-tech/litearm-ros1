# litearm-ros1 Developer Guide & API Reference

`litearm_ros1` is a standard catkin (ROS1 Noetic) package that bridges
[litearm-python](../litearm-python) to ROS: the arm appears as topics, TF and
services, and all bridge logic is kept ROS-free so it can be tested anywhere.

```text
ROS topics/services ──→ litearm_node.py ──→ LiteArmBridge ──→ litearm.Arm ──→ litearm-server
```

---

## 1. Requirements & build

| Item | Requirement |
|---|---|
| ROS | Noetic (tested) |
| Python | 3.8+ with `rospy`, `roslib` |
| Base SDK | `litearm-python` (pip; install into the python used by rospy) |

```bash
source /opt/ros/noetic/setup.bash
cd <your catkin_ws>/src && git clone <this-repo> litearm_ros1
pip install litearm-python
cd <your catkin_ws> && catkin_make && source devel/setup.bash
```

Run the mock unit tests on any machine (no ROS needed):

```bash
cd litearm_ros1 && PYTHONPATH=src python3 -m pytest tests/ -q
```

## 2. The ROS-agnostic core

`src/litearm_ros1/bridge.py` (`LiteArmBridge`) adapts a `litearm.Arm` to plain
dicts/tuples; `pose_utils.py` converts between the litearm pose format
(`[position(3), rotation(3×3 row-major)]`) and ROS `(x, y, z, qx, qy, qz, qw)`.
No `rospy` imports — the node (`nodes/litearm_node.py`) is the only ROS layer.

Key `LiteArmBridge` methods (all return `(bool, message)` or plain data):

| Method | Result |
|---|---|
| `read_joint_state()` | `{name, position, velocity, effort}` or `None` |
| `read_tcp_pose()` | `(x, y, z, qx, qy, qz, qw)` or `None` |
| `get_state()` | `{q, dq, tau, state, fault}` or `None` |
| `movej(q, speed, settle_s)` / `movel(xyz_quat, speed, settle_s)` | `(bool, message)` |
| `fk(q)` / `ik(xyz_quat, q_seed)` | `(data, bool, message)` |
| `request_stop()` / `clear_stop()` / `enable()` / `disable()` | `(bool, message)` |
| `close()` | — |

## 3. Node interfaces

`nodes/litearm_node.py` (`LiteArmNode`, rospy):

### Publishers

| Topic | Type | Contents |
|---|---|---|
| `/joint_states` | `sensor_msgs/JointState` | `q` / `dq` / `tau` at `loop_hz` |
| `/litearm/tcp_pose` | `geometry_msgs/PoseStamped` | TCP pose in `base_link` |
| `/tf` | `tf2_msgs/TFMessage` | `base_link → tool0` |

### Subscribers

| Topic | Type | Action |
|---|---|---|
| `/litearm/cmd_joint` | `sensor_msgs/JointState` | `movej(position, speed=cmd_speed)` |
| `/litearm/stop` | `std_msgs/Empty` | emergency `request_stop()` |

**Services** (custom `srv/*.srv`, all reply `success` + `message`)

| Service | Request | Response |
|---|---|---|
| `/litearm/movej` | `float64[] q_target, float64 speed, float64 settle_s` | `bool success, string message` |
| `/litearm/movel` | `geometry_msgs/Pose pose, float64 speed, float64 settle_s` | `bool success, string message` |
| `/litearm/fk` | `float64[] q` | `geometry_msgs/Pose pose, bool success, string message` |
| `/litearm/ik` | `geometry_msgs/Pose pose, float64[] q_seed` | `float64[] q, bool success, string message` |
| `/litearm/get_state` | *(empty)* | `float64[] q/dq/tau, string state, bool fault, string message` |
| `/litearm/request_stop`, `/litearm/clear_stop`, `/litearm/enable`, `/litearm/disable` | `std_srvs/Trigger` | `bool success, string message` |

**Parameters** (launch args + `config/litearm.yaml`): `endpoint`, `arm_id`,
`loop_hz`, `cmd_speed`, `joint_names`, `base_frame`, `tcp_frame`.

## 4. Pose convention

- litearm pose: `[position(3), rotation(3×3 row-major matrix)]`
- ROS pose: `(x, y, z, qx, qy, qz, qw)`

`xyz_quat_to_litearm_pose` / `litearm_pose_to_xyz_quat` convert both ways with
pure Python (no numpy, no ROS). Quaternions are normalized on output.

## 5. Custom services

`Movej.srv`/`Movel.srv`/`Fk.srv`/`Ik.srv`/`GetState.srv` are declared in
`CMakeLists.txt` via `add_service_files(...)` + `generate_messages(...)` and
consumed as `litearm_ros1.srv.*` at runtime. `geometry_msgs/Pose` is imported
from `geometry_msgs`; `success`/`message` on every response keeps client handling
uniform.

## 6. Notes & caveats

- `litearm-python` is **not rosdep-resolvable**; install it with pip into the
  same interpreter that runs rospy, and upgrade `protobuf>=7.35.1` if import
  fails.
- `movej`/`movel` are **blocking** RPCs — a service call returns only when the
  motion completes. The `/litearm/cmd_joint` subscriber also blocks until the
  commanded motion finishes; issue commands at a sensible rate.
- Build (`catkin_make`) must run on a machine with ROS1; the mock tests run
  anywhere.
