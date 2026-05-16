cmake_minimum_required(VERSION 3.8)
project(cleanbit_simulate)

# Trova le dipendenze
find_package(ament_cmake REQUIRED)
find_package(rclpy REQUIRED)
find_package(ament_cmake_python REQUIRED)

# Aggiungi opzioni di compilazione se usi C++ (utile se in futuro aggiungi nodi in C++)
if(CMAKE_COMPILER_IS_GNUCXX OR CMAKE_CXX_COMPILER_ID MATCHES "Clang")
  add_compile_options(-Wall -Wextra -Wpedantic)
endif()

# Installa cartelle di configurazione e modelli
install(
  DIRECTORY launch model config
  DESTINATION share/${PROJECT_NAME}
)

install(
  DIRECTORY worlds meshes
  DESTINATION share/${PROJECT_NAME}
)

# Installa script Python
install(PROGRAMS
  cleanbit_simulate/odom_to_tf.py

  DESTINATION lib/${PROJECT_NAME}
)

# Lint automatici (solo se i test sono abilitati)
if(BUILD_TESTING)
  find_package(ament_lint_auto REQUIRED)

  # Disabilita temporaneamente lint che richiedono licenza/copyright
  set(ament_cmake_cpplint_FOUND TRUE)
  set(ament_cmake_copyright_FOUND TRUE)

  ament_lint_auto_find_test_dependencies()
endif()

ament_package()

