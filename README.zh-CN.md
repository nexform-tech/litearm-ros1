# litearm-ros1

面向 **LiteArm** 机械臂的 [ROS1](http://wiki.ros.org/noetic) 桥接包。封装
[litearm-python](https://pypi.org/project/litearm-python)，让机械臂以标准 ROS
话题、坐标变换和服务出现：关节状态、TCP 位姿 + TF、关节指令，以及
`movej`/`movel`/`fk`/`ik` 服务。

```text
ROS 话题 / 服务 ──→ litearm_node.py ──→ LiteArmBridge ──→ litearm.Arm ──→ litearm-server
```

> 📖 完整开发指南与 API 参考：[docs/DEVELOPER_GUIDE.md](docs/DEVELOPER_GUIDE.md)
> · English: [README.md](README.md)

---

## 目录

- [概述与架构](#概述与架构)
- [环境要求](#环境要求)
- [安装与构建](#安装与构建)
- [启动](#启动)
- [节点接口](#节点接口)
- [使用示例](#使用示例)
- [TF 与可视化](#tf-与可视化)
- [常见问题排查](#常见问题排查)
- [包结构](#包结构)
- [文档与许可证](#文档与许可证)

---

## 概述与架构

`litearm-ros1` 是一个标准 **catkin** 包。单个节点 `litearm_node.py` 通过 Zenoh
endpoint 连接运行中的 **litearm-server**，在 ROS 与机械臂之间双向中继数据：

| 方向 | ROS 侧 | 机械臂侧 |
|---|---|---|
| 出（状态） | `/joint_states`、`/litearm/tcp_pose`、`/tf` | `Arm.get_state()`、`Arm.get_tcp_pose()` |
| 入（指令） | `/litearm/cmd_joint`、`/litearm/stop` | `Arm.movej()`、`Arm.request_stop()` |
| 入（服务） | `/litearm/movej`、`/litearm/movel`、`/litearm/fk`、`/litearm/ik`、`/litearm/get_state`、`/litearm/request_stop`、`/litearm/clear_stop`、`/litearm/enable`、`/litearm/disable` | `Arm.*` RPC |

桥接逻辑位于 `src/litearm_ros1/bridge.py` + `pose_utils.py`，**不含 `rospy`
import** —— 只操作纯 dict/tuple，与 ROS2 桥接共享，且可在任意机器上无 ROS 单测。

## 环境要求

| 项目 | 要求 |
|---|---|
| ROS | **Noetic**（已验证）+ 标准 catkin 工具链 |
| Python | 3.8+，含 `rospy` / `roslib` |
| 基础 SDK | `litearm-python`（pip 安装；**无法**用 rosdep 解析） |
| 运行时 | 可达的 **litearm-server**（Zenoh endpoint，例如 `tcp/192.168.31.237:7447`） |

> `litearm-python` 通过 Zenoh 与 litearm-server 通信；服务器持有真实硬件或仿真。
> 启动前请确认其已运行。

## 安装与构建

```bash
source /opt/ros/noetic/setup.bash
mkdir -p ~/catkin_ws/src && cd ~/catkin_ws/src
git clone git@github.com:nexform-tech/litearm-ros1.git litearm_ros1

# 把基础 SDK 装进 rospy 所用的 python（见下方说明）：
pip install litearm-python        # 或：pip install -e /path/to/litearm-python

cd ~/catkin_ws && catkin_make
source ~/catkin_ws/devel/setup.bash
```

- `catkin_make` 会自动执行 `catkin_python_setup()`，因此 Python 包
  `litearm_ros1` 与生成的消息/服务类会安装进 devel 空间，无需额外操作。
- **装进正确的解释器。** 节点要 `import litearm`，所以 `litearm-python` 必须能被
  运行 rospy 的同一个 python 导入。标准 Noetic 下通常是系统 python：
  `sudo python3 -m pip install litearm-python`（若默认 `pip` 属于 conda/venv，
  里面可能没有 rospy）。
- 若节点 import 报 protobuf 错误，请在 ROS python 环境升级
  `protobuf>=7.35.1`。

在任意机器上运行 mock 单测（无需 ROS）：

```bash
cd litearm_ros1 && PYTHONPATH=src python3 -m pytest tests/ -q
```

## 启动

```bash
roslaunch litearm_ros1 litearm.launch \
  endpoint:=tcp/192.168.31.237:7447   # litearm-server 的地址
```

launch 文件支持的参数如下（默认值来自 `config/litearm.yaml`，会以私有节点参数
合入）：

| 参数 | 默认值 | 含义 |
|---|---|---|
| `endpoint` | `tcp/192.168.31.237:7447` | litearm-server 的 Zenoh endpoint |
| `arm_id` | `armA` | 服务器上注册的机械臂 id |
| `loop_hz` | `50.0` | 状态发布频率（Hz） |
| `cmd_speed` | `0.5` | 默认关节运动速度（0..1） |

所有参数也可在 `config/litearm.yaml` 中覆盖，或以 `~param` 方式传入（见
[参数](#参数)）。

## 节点接口

### 发布

| 话题 | 类型 | 内容 |
|---|---|---|
| `/joint_states` | `sensor_msgs/JointState` | `q` / `dq` / `tau`，以 `loop_hz` 发布 |
| `/litearm/tcp_pose` | `geometry_msgs/PoseStamped` | `base_frame` 系下的 TCP 位姿 |
| `/tf` | `tf2_msgs/TFMessage` | `base_frame → tcp_frame` 变换 |

### 订阅

| 话题 | 类型 | 动作 |
|---|---|---|
| `/litearm/cmd_joint` | `sensor_msgs/JointState` | `movej(position, speed=cmd_speed)` |
| `/litearm/stop` | `std_msgs/Empty` | 急停：`request_stop()` |

### 服务

自定义服务（`srv/*.srv`）。每个响应都含 `success` + `message`。

| 服务 | 请求 | 响应 |
|---|---|---|
| `/litearm/movej` | `float64[] q_target, float64 speed, float64 settle_s` | `bool success, string message` |
| `/litearm/movel` | `geometry_msgs/Pose pose, float64 speed, float64 settle_s` | `bool success, string message` |
| `/litearm/fk` | `float64[] q` | `geometry_msgs/Pose pose, bool success, string message` |
| `/litearm/ik` | `geometry_msgs/Pose pose, float64[] q_seed` | `float64[] q, bool success, string message` |
| `/litearm/get_state` | *（空）* | `float64[] q/dq/tau, string state, bool fault, string message` |
| `/litearm/request_stop` | `std_srvs/Trigger` | `bool success, string message` |
| `/litearm/clear_stop` | `std_srvs/Trigger` | `bool success, string message` |
| `/litearm/enable` | `std_srvs/Trigger` | `bool success, string message` |
| `/litearm/disable` | `std_srvs/Trigger` | `bool success, string message` |

### 参数

全部为私有节点参数（`~name`），默认值如下：

| 参数 | 默认值 | 含义 |
|---|---|---|
| `endpoint` | `tcp/192.168.31.237:7447` | litearm-server 的 Zenoh endpoint |
| `arm_id` | `armA` | 服务器上注册的机械臂 id |
| `loop_hz` | `50.0` | 状态发布频率（Hz） |
| `cmd_speed` | `0.5` | `/litearm/cmd_joint` 使用的默认关节速度（0..1） |
| `joint_names` | `joint0 … joint6` | `/joint_states` 中的关节名 |
| `base_frame` | `base_link` | 机械臂基座坐标系 |
| `tcp_frame` | `tool0` | 工具中心点坐标系 |

## 使用示例

### 查看机械臂状态

```bash
rostopic echo /joint_states
rostopic echo /litearm/tcp_pose
rosrun tf tf_echo base_link tool0     # 实时查看两坐标系间的 TF
```

### 通过话题下发关节空间运动

```bash
rostopic pub -1 /litearm/cmd_joint sensor_msgs/JointState \
  '{name: [joint0, joint1, joint2, joint3, joint4, joint5, joint6], \
    position: [0.1, 0.1, 0.1, 0.1, 0.1, 0.1, 0.1]}'
```

`position` 会以节点的 `cmd_speed` 传给 `movej()`。

### 通过服务下发关节空间运动

```bash
rosservice call /litearm/movej \
  '{q_target: [0.1, 0.1, 0.1, 0.1, 0.1, 0.1, 0.1], speed: 0.3, settle_s: 0.5}'
```

`q_target` 是 7 个关节位置，`speed` 是归一化速度（`0..1`），`settle_s` 是运动
到位后的停留时间。

### 运动到笛卡尔位姿

```bash
rosservice call /litearm/movel \
  '{pose: {position: {x: 0.25, y: 0.0, z: 0.35}, \
    orientation: {x: 0.0, y: 0.0, z: 0.0, w: 1.0}}, speed: 0.3, settle_s: 0.5}'
```

位姿为 `base_frame` 系下的 `geometry_msgs/Pose`，姿态用四元数 `(x, y, z, w)`。

### 正解 / 逆解

```bash
# FK：关节 → TCP 位姿
rosservice call /litearm/fk '{q: [0.0, 0.0, 0.0, 0.0, 0.0, 0.0, 0.0]}'

# IK：TCP 位姿 → 关节（q_seed 可选，用于帮助选出解）
rosservice call /litearm/ik \
  '{pose: {position: {x: 0.25, y: 0.0, z: 0.35}, \
    orientation: {x: 0.0, y: 0.0, z: 0.0, w: 1.0}}, \
    q_seed: [0.0, 0.0, 0.0, 0.0, 0.0, 0.0, 0.0]}'
```

### 读取完整状态

```bash
rosservice call /litearm/get_state
# → q, dq, tau 数组、state 字符串、fault 布尔、message
```

### 急停与恢复

```bash
# 立即停止（话题）：
rostopic pub -1 /litearm/stop std_msgs/Empty '{}'
# 或通过服务：
rosservice call /litearm/request_stop

# 确认安全后清除急停：
rosservice call /litearm/clear_stop
```

### 使能 / 失能

```bash
rosservice call /litearm/enable
rosservice call /litearm/disable
```

## TF 与可视化

节点每次状态更新都会广播 `base_link → tool0` 变换，任何 TF 消费者都可以跟踪
机械臂。可视化：

```bash
rosrun rviz rviz
# Add → TF，将 Fixed Frame 设为 base_link
```

> 本包不含 URDF 或 MoveIt 配置——它提供实时 TF `base_link → tool0` 与
> `/litearm/tcp_pose` 话题，足以可视化机械臂位姿。若你另有 LiteArm 的 URDF，
> 请用 `base_frame` / `tcp_frame` 对齐其基座/工具坐标系名。

## 常见问题排查

| 现象 | 可能原因 / 解决 |
|---|---|
| `ModuleNotFoundError: No module named 'litearm'` | `litearm-python` 装进了与 rospy 不同的 python。执行 `sudo python3 -m pip install litearm-python`。 |
| import 报 protobuf 相关错误 | 升级 ROS python：`python3 -m pip install 'protobuf>=7.35.1'`。 |
| `/joint_states` 无数据 | litearm-server 不可达。检查 `endpoint`（`tcp/<主机>:<端口>`）、服务器是否在运行、`arm_id` 是否匹配已注册机械臂。 |
| `movej` 返回 `success: True` 但机械臂不动 | 用 `/litearm/get_state` 查看状态；机械臂可能被失能或处于急停态——调用 `/litearm/enable` / `/litearm/clear_stop`。 |
| 指令像被卡住 / 排队 | `movej`/`movel` 是**阻塞** RPC——节点（以及发布 `/litearm/cmd_joint`）会阻塞到运动结束。请以合理频率下发指令。 |
| `catkin_make` 报缺消息包 | 确认 `message_generation`、`geometry_msgs`、`sensor_msgs`、`std_msgs`、`std_srvs`、`tf` 已安装（桌面完整版 ROS1 通常自带）。 |

## 包结构

```text
litearm_ros1/
├── CMakeLists.txt          catkin + message_generation
├── package.xml             catkin 包清单
├── setup.py                catkin_python_setup（安装 python 包）
├── src/litearm_ros1/
│   ├── bridge.py           ROS 无关桥接逻辑（无 rospy import）
│   └── pose_utils.py       纯 Python 的 litearm ⇄ ROS 位姿转换
├── nodes/litearm_node.py   rospy 桥接节点
├── srv/                    自定义服务：Movej, Movel, Fk, Ik, GetState
├── launch/litearm.launch
├── config/litearm.yaml
└── tests/                  mock 单元测试（无需 ROS）
```

## 文档与许可证

- 开发指南与 API 参考（接口细节、位姿约定、核心内部实现）：
  [docs/DEVELOPER_GUIDE.md](docs/DEVELOPER_GUIDE.md)
- English: [README.md](README.md)
- 许可证：见 `package.xml`（`Proprietary`）。
