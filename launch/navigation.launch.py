import os
from ament_index_python.packages import get_package_share_directory
from launch import LaunchDescription
from launch.actions import IncludeLaunchDescription, DeclareLaunchArgument
from launch.substitutions import LaunchConfiguration
from launch.launch_description_sources import PythonLaunchDescriptionSource
from launch_ros.actions import Node


def generate_launch_description():
    package_name = 'cleanbit_simulate'

    nav2_params_path = os.path.join(
        get_package_share_directory(package_name), 'config', 'nav2_params.yaml')

    twist_mux_params_path = os.path.join(
        get_package_share_directory(package_name), 'config', 'twist_mux.yaml')

    default_map_path = os.path.join(
        get_package_share_directory(package_name), 'maps', 'home_map.yaml')

    map_arg = DeclareLaunchArgument(
        'map_file',
        default_value=default_map_path,
        description='Path al file .yaml della mappa'
    )

    map_server = Node(
        package='nav2_map_server',
        executable='map_server',
        name='map_server',
        output='screen',
        parameters=[{
            'use_sim_time': True,
            'yaml_filename': LaunchConfiguration('map_file')
        }]
    )

    amcl = Node(
        package='nav2_amcl',
        executable='amcl',
        name='amcl',
        output='screen',
        parameters=[nav2_params_path, {'use_sim_time': True}]
    )


    # Fornisce metadati del filtro alla costmap
    costmap_filter_info_server = Node(
        package='nav2_map_server',
        executable='costmap_filter_info_server',
        name='costmap_filter_info_server',
        output='screen',
        parameters=[{
            'use_sim_time': True,
            'type': 0,
            'filter_info_topic': '/costmap_filter_info',
            'mask_topic': '/keepout_mask',
            'base': 0.0,
            'multiplier': 1.0,
            'frame_id': 'map'
        }]
    )

    lifecycle_manager_localization = Node(
        package='nav2_lifecycle_manager',
        executable='lifecycle_manager',
        name='lifecycle_manager_localization',
        output='screen',
        parameters=[{
            'use_sim_time': True,
            'autostart': True,
            'node_names': ['map_server', 'amcl', 'costmap_filter_info_server']
        }]
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
            'use_sim_time': 'true',
            'autostart': 'false',
            'slam': 'False'
        }.items()
    )

    lifecycle_manager_navigation = Node(
        package='nav2_lifecycle_manager',
        executable='lifecycle_manager',
        name='lifecycle_manager_navigation',
        output='screen',
        parameters=[{
            'use_sim_time': True,
            'autostart': True,
            'node_names': [
                'controller_server',
                'smoother_server',
                'planner_server',
                'behavior_server',
                'bt_navigator',
                'waypoint_follower',
                'velocity_smoother'
            ]
        }]
    )

    twist_mux = Node(
        package='twist_mux',
        executable='twist_mux',
        name='twist_mux',
        output='screen',
        parameters=[twist_mux_params_path],
        remappings=[('cmd_vel_out', 'cmd_vel')]
    )

    navigation_manager = Node(
        package='cleanbit_simulate',
        executable='navigation_manager.py',
        name='navigation_manager_node',
        output='screen',
        parameters=[{'use_sim_time': True}]
    )

    return LaunchDescription([
        map_arg,
        map_server,
        amcl,
        costmap_filter_info_server,
        lifecycle_manager_localization,
        nav2_launch,
        lifecycle_manager_navigation,
        twist_mux,
        navigation_manager,
    ])