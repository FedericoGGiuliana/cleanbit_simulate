import os
from ament_index_python.packages import get_package_share_directory
from launch import LaunchDescription
from launch.actions import DeclareLaunchArgument
from launch.substitutions import LaunchConfiguration
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

    # --- Localizzazione ---
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

    # --- Nav2 core nodes ---
    controller_server = Node(
        package='nav2_controller',
        executable='controller_server',
        name='controller_server',
        output='screen',
        parameters=[nav2_params_path, {'use_sim_time': True}]
    )

    smoother_server = Node(
        package='nav2_smoother',
        executable='smoother_server',
        name='smoother_server',
        output='screen',
        parameters=[nav2_params_path, {'use_sim_time': True}]
    )

    planner_server = Node(
        package='nav2_planner',
        executable='planner_server',
        name='planner_server',
        output='screen',
        parameters=[nav2_params_path, {'use_sim_time': True}]
    )

    behavior_server = Node(
        package='nav2_behaviors',
        executable='behavior_server',
        name='behavior_server',
        output='screen',
        parameters=[nav2_params_path, {'use_sim_time': True}]
    )

    bt_navigator = Node(
        package='nav2_bt_navigator',
        executable='bt_navigator',
        name='bt_navigator',
        output='screen',
        parameters=[nav2_params_path, {'use_sim_time': True}]
    )

    waypoint_follower = Node(
        package='nav2_waypoint_follower',
        executable='waypoint_follower',
        name='waypoint_follower',
        output='screen',
        parameters=[nav2_params_path, {'use_sim_time': True}]
    )

    velocity_smoother = Node(
        package='nav2_velocity_smoother',
        executable='velocity_smoother',
        name='velocity_smoother',
        output='screen',
        parameters=[nav2_params_path, {'use_sim_time': True}]
    )

    coverage_server = Node(
        package='opennav_coverage',
        executable='opennav_coverage',
        name='coverage_server',
        output='screen',
        parameters=[{
            'use_sim_time': True,
            'robot_width': 0.35,
            'operation_width': 0.35,
            'headland_width': 0.30,
        }]
    )

    # Un solo lifecycle manager per tutti i nodi Nav2 + coverage
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
                'velocity_smoother',
                'coverage_server',
            ]
        }]
    )

    # --- Altri nodi ---
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

    cleaning_controller_node = Node(
        package='cleanbit_simulate',
        executable='cleaning_controller',
        name='cleaning_controller',
        output='screen',
        parameters=[{
            'use_sim_time': True,
            'wall_offset': 0.30,
            'robot_width': 0.35,
        }]
    )

    return LaunchDescription([
        map_arg,
        map_server,
        amcl,
        costmap_filter_info_server,
        lifecycle_manager_localization,
        controller_server,
        smoother_server,
        planner_server,
        behavior_server,
        bt_navigator,
        waypoint_follower,
        velocity_smoother,
        coverage_server,
        lifecycle_manager_navigation,
        twist_mux,
        navigation_manager,
        cleaning_controller_node,
    ])