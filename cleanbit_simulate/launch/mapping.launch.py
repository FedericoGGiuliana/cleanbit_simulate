import os
import xacro
from ament_index_python.packages import get_package_share_directory

from launch import LaunchDescription
from launch.actions import IncludeLaunchDescription, DeclareLaunchArgument
from launch.substitutions import LaunchConfiguration
from launch.launch_description_sources import PythonLaunchDescriptionSource
from launch_ros.actions import Node
from launch.actions import ExecuteProcess



def generate_launch_description():
    # Define the robot's name and package name
    package_name = "cleanbit_simulate"

    slam_params_path = os.path.join(
        get_package_share_directory(package_name),
        'config',
        'mapper_params_online_async.yaml'
    )

    twist_mux_params_path = os.path.join(
        get_package_share_directory(package_name),
        'config',
        'twist_mux.yaml'
    )

    nav2_params_path = os.path.join(
        get_package_share_directory(package_name),
        'config',
        'nav2_params.yaml'
    )

    explore_params = os.path.join(
        get_package_share_directory(package_name),
        'config',
        'explore_params.yaml'
    )


    slam_toolbox_launch = IncludeLaunchDescription(
        PythonLaunchDescriptionSource(
            os.path.join(
                get_package_share_directory('slam_toolbox'),
                'launch',
                'online_async_launch.py'
            )
        ),
        launch_arguments={
            'slam_params_file': slam_params_path,
            'use_sim_time': 'true'
        }.items()
    )


    twist_mux_process = Node(
        package="twist_mux",
        executable="twist_mux",
        name="twist_mux",
        output="screen",
        parameters=[twist_mux_params_path],
        remappings=[("cmd_vel_out", "cmd_vel")]
    )

    nav2_launch = IncludeLaunchDescription(
        PythonLaunchDescriptionSource(
            os.path.join(
                get_package_share_directory('nav2_bringup'),
                'launch',
                'navigation_launch.py'
            )
        ),
        launch_arguments={
            'params_file': nav2_params_path,
            'use_sim_time': 'true'
        }.items()
    )

    explore_node = Node(
        package='explore_lite',
        executable='explore',
        name='explore_lite',
        output='screen',
        parameters=[explore_params]
    )

    map_manager_node = Node(
        package=package_name,
        executable='map_manager_node.py',
        name='map_manager_node',
        output='screen'
    )


    return LaunchDescription([
        slam_toolbox_launch,
        nav2_launch,
        twist_mux_process,
        explore_node,
        map_manager_node
    ])