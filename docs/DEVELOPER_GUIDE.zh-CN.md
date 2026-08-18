# litearm-ros1 开发指南与 API 参考

`litearm_ros1` 是标准的 catkin（ROS1 Noetic）包，用于桥接
[litearm-python](../litearm-python) 到 ROS：机械臂以话题、TF 和服务的形式出现，
且所有桥接逻辑都与 ROS 解耦，便于在任意机器上测试。

```text
ROS topics/services ──→ litearm_node.py ──→ LiteArmBridge ──→ litearm.Arm ──→ litearm-server
```

---

## 1. 环境要求与构建

| 项目 | 要求 |
|---|---|
| ROS | Noetic（已验证） |
| Python | 3.8+，含 `rospy`、`roslib` |
| 基础 SDK | `litearm-python`（pip 安装；装进 rospy 所用的 python） |

```bash
source /opt/ros/noetic/setup.bash
cd <你的 catkin_ws>/src && git clone <本仓库> litearm_ros1
pip install litearm-python
cd <你的 catkin_ws> && catkin_make && source devel/setup.bash
```

在任意机器上运行 mock 单测（无需 ROS）：

```bash
cd litearm_ros1 && PYTHONPATH=src python3 -m pytest tests/ -q
```

## 2. 与 ROS 无关的核心

`src/litearm_ros1/bridge.py`（`LiteArmBridge`）把 `litearm.Arm` 适配成纯
dict/tuple；`pose_utils.py` 负责 litearm 位姿格式（`[position(3), rotation(3×3 row-major)]`）
与 ROS `(x, y, z, qx, qy, qz, qw)` 互转。两者都不 import `rospy`——节点
（`nodes/litearm_node.py`）是唯一的 ROS 层。

`LiteArmBridge` 主要方法（均返回 `(bool, message)` 或纯数据）：

| 方法 | 结果 |
|---|---|
| `read_joint_state()` | `{name, position, velocity, effort}` 或 `None` |
| `read_tcp_pose()` | `(x, y, z, qx, qy, qz, qw)` 或 `None` |
| `get_state()` | `{q, dq, tau, state, fault}` 或 `None` |
| `movej(q, speed, settle_s)` / `movel(xyz_quat, speed, settle_s)` | `(bool, message)` |
| `fk(q)` / `ik(xyz_quat, q_seed)` | `(data, bool, message)` |
| `request_stop()` / `clear_stop()` / `enable()` / `disable()` | `(bool, message)` |
| `close()` | — |

## 3. 节点接口

`nodes/litearm_node.py`（`LiteArmNode`，rospy）：

### 发布

| 话题 | 类型 | 内容 |
|---|---|---|
| `/joint_states` | `sensor_msgs/JointState` | `q` / `dq` / `tau`，频率 `loop_hz` |
| `/litearm/tcp_pose` | `geometry_msgs/PoseStamped` | `base_link` 系下的 TCP 位姿 |
| `/tf` | `tf2_msgs/TFMessage` | `base_link → tool0` |

### 订阅

| 话题 | 类型 | 动作 |
|---|---|---|
| `/litearm/cmd_joint` | `sensor_msgs/JointState` | `movej(position, speed=cmd_speed)` |
| `/litearm/stop` | `std_msgs/Empty` | 急停 `request_stop()` |

**服务**（自定义 `srv/*.srv`，响应均含 `success` + `message`）

| 服务 | 请求 | 响应 |
|---|---|---|
| `/litearm/movej` | `float64[] q_target, float64 speed, float64 settle_s` | `bool success, string message` |
| `/litearm/movel` | `geometry_msgs/Pose pose, float64 speed, float64 settle_s` | `bool success, string message` |
| `/litearm/fk` | `float64[] q` | `geometry_msgs/Pose pose, bool success, string message` |
| `/litearm/ik` | `geometry_msgs/Pose pose, float64[] q_seed` | `float64[] q, bool success, string message` |
| `/litearm/get_state` | *（空）* | `float64[] q/dq/tau, string state, bool fault, string message` |
| `/litearm/request_stop`、`/litearm/clear_stop`、`/litearm/enable`、`/litearm/disable` | `std_srvs/Trigger` | `bool success, string message` |

**参数**（launch 参数 + `config/litearm.yaml`）：`endpoint`、`arm_id`、
`loop_hz`、`cmd_speed`、`joint_names`、`base_frame`、`tcp_frame`。

## 4. 位姿约定

- litearm 位姿：`[position(3), rotation(3×3 row-major matrix)]`
- ROS 位姿：`(x, y, z, qx, qy, qz, qw)`

`xyz_quat_to_litearm_pose` / `litearm_pose_to_xyz_quat` 用纯 Python（无 numpy、
无 ROS）双向转换。输出四元数会归一化。

## 5. 自定义服务

`Movej.srv`/`Movel.srv`/`Fk.srv`/`Ik.srv`/`GetState.srv` 在 `CMakeLists.txt`
中通过 `add_service_files(...)` + `generate_messages(...)` 声明，运行时以
`litearm_ros1.srv.*` 使用。`geometry_msgs/Pose` 来自 `geometry_msgs`；每个响应都
带 `success`/`message`，让客户端处理保持一致。

## 6. 注意事项

- `litearm-python` **无法**用 rosdep 解析；请用 pip 装进运行 rospy 的解释器，
  若 import 报错需升级 `protobuf>=7.35.1`。
- `movej`/`movel` 是**阻塞** RPC——服务调用在运动完成时才返回。`/litearm/cmd_joint`
  订阅回调同样会阻塞到运动结束；请以合理频率下发指令。
- 构建（`catkin_make`）必须在装有 ROS1 的机器上执行；mock 测试可任意机器运行。
