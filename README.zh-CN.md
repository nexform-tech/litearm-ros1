# litearm-ros1

[ROS1](http://wiki.ros.org/noetic) 桥接包，用于 LiteArm 机械臂。封装
[litearm-python](../litearm-python)，让机械臂以标准 ROS 话题、坐标变换和服务
出现：关节状态、TCP 位姿 + TF、关节指令，以及 `movej`/`movel`/`fk`/`ik` 服务。

## 特性

- 📡 **发布** —— `/joint_states`、`/litearm/tcp_pose`、TF `base_link → tool0`
- 🎮 **订阅** —— `/litearm/cmd_joint`（JointState → movej）、`/litearm/stop`（急停）
- 🛠️ **服务** —— `/litearm/movej`、`/litearm/movel`、`/litearm/fk`、`/litearm/ik`、
  `/litearm/get_state` + std_srvs Trigger（`request_stop`/`clear_stop`/`enable`/`disable`）
- 🧪 **与 ROS 无关的核心** —— `bridge.py` + `pose_utils.py` 不含 `rospy` import，
  可在任意机器上单测

> 📖 完整开发指南与 API 参考：[docs/DEVELOPER_GUIDE.md](docs/DEVELOPER_GUIDE.md)
> · English: [README.md](README.md)

## 环境要求

- ROS **Noetic**（已验证）+ 标准 catkin 工具链
- Python 3.8+（含 `rospy`/`roslib`）
- [litearm-python](https://pypi.org/project/litearm-python)（pip 安装；**无法**用 rosdep 解析）

## 构建

```bash
source /opt/ros/noetic/setup.bash
mkdir -p ~/catkin_ws/src && cd ~/catkin_ws/src
git clone <本仓库> litearm_ros1
# 把基础 SDK 装进 rospy 所用的 python：
pip install litearm-python        # 或：pip install -e /path/to/litearm-python
cd ~/catkin_ws && catkin_make
source ~/catkin_ws/devel/setup.bash
```

> `catkin_make` 会自动执行 `catkin_python_setup()`，因此 Python 包
> `litearm_ros1` 与生成的消息都会自动安装。

## 启动

```bash
roslaunch litearm_ros1 litearm.launch \
  endpoint:=tcp/192.168.31.237:7447   # litearm-server 的地址
```

查看机械臂状态：

```bash
rostopic echo /joint_states
rostopic echo /litearm/tcp_pose
```

下发运动：

```bash
# 通过订阅话题
rostopic pub -1 /litearm/cmd_joint sensor_msgs/JointState \
  '{name: [joint0..joint6], position: [0.1, 0.1, 0.1, 0.1, 0.1, 0.1, 0.1]}'
# 或通过服务
rosservice call /litearm/movej '{q_target: [0.1, 0.1, 0.1, 0.1, 0.1, 0.1, 0.1], speed: 0.3, settle_s: 0.5}'
```

## 包结构

```text
litearm_ros1/
├── CMakeLists.txt          catkin + message_generation
├── package.xml             catkin 包清单
├── setup.py                catkin_python_setup（安装 litearm_ros1 python 包）
├── src/litearm_ros1/
│   ├── bridge.py           ROS 无关桥接逻辑（无 rospy import）
│   └── pose_utils.py       纯 Python 的 litearm ⇄ ROS 位姿转换
├── nodes/litearm_node.py   rospy 桥接节点
├── srv/                    自定义服务：Movej, Movel, Fk, Ik, GetState
├── launch/litearm.launch
├── config/litearm.yaml
└── tests/                  mock 单元测试（无需 ROS）
```
