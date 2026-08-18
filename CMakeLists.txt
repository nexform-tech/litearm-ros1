cmake_minimum_required(VERSION 3.0.2)
project(litearm_ros1)

# catkin_python_setup() installs the src/litearm_ros1 module into the
# devel space so the node can `import litearm_ros1`.
catkin_python_setup()

find_package(catkin REQUIRED COMPONENTS
  message_generation
  geometry_msgs
  sensor_msgs
  std_msgs
  std_srvs
  tf
)

# Custom services
add_service_files(FILES
  Movej.srv
  Movel.srv
  Fk.srv
  Ik.srv
  GetState.srv
)

generate_messages(DEPENDENCIES
  geometry_msgs
  sensor_msgs
  std_msgs
  std_srvs
)

catkin_package(
  CATKIN_DEPENDS geometry_msgs sensor_msgs std_msgs std_srvs message_runtime tf
)

# Node entry point
catkin_install_python(PROGRAMS
  nodes/litearm_node.py
  DESTINATION ${CATKIN_PACKAGE_BIN_DESTINATION}
)

# Launch + config files
install(DIRECTORY launch config
  DESTINATION ${CATKIN_PACKAGE_SHARE_DESTINATION}
)
