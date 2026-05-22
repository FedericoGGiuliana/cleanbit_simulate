cmake_minimum_required(VERSION 3.8)
project(cleanbit_simulate)

find_package(ament_cmake REQUIRED)
find_package(rclpy REQUIRED)
find_package(ament_cmake_python REQUIRED)

ament_python_install_package(${PROJECT_NAME})

if(CMAKE_COMPILER_IS_GNUCXX OR CMAKE_CXX_COMPILER_ID MATCHES "Clang")
  add_compile_options(-Wall -Wextra -Wpedantic)
endif()

install(
  DIRECTORY launch model config worlds meshes data models cleanbit_simulate maps
  DESTINATION share/${PROJECT_NAME}
)

install(PROGRAMS
  cleanbit_simulate/odom_to_tf.py
  cleanbit_simulate/supervisor.py
  cleanbit_simulate/map_manager_node.py
  cleanbit_simulate/room_editor.py
  DESTINATION lib/${PROJECT_NAME}
)

if(EXISTS "${CMAKE_CURRENT_SOURCE_DIR}/scripts/nlu_node")
  install(PROGRAMS
    scripts/nlu_node
    DESTINATION lib/${PROJECT_NAME}
  )
endif()

if(EXISTS "${CMAKE_CURRENT_SOURCE_DIR}/scripts/nlu_terminal")
  install(PROGRAMS
    scripts/nlu_terminal
    DESTINATION lib/${PROJECT_NAME}
  )
endif()

if(BUILD_TESTING)
  find_package(ament_lint_auto REQUIRED)

  set(ament_cmake_cpplint_FOUND TRUE)
  set(ament_cmake_copyright_FOUND TRUE)

  ament_lint_auto_find_test_dependencies()
endif()

ament_package()
