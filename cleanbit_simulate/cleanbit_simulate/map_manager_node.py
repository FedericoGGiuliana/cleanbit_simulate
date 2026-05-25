#!/usr/bin/env python3
import rclpy
from rclpy.node import Node
from visualization_msgs.msg import MarkerArray
from slam_toolbox.srv import SaveMap
from std_msgs.msg import String
from geometry_msgs.msg import PoseWithCovarianceStamped
from nav_msgs.msg import Odometry
import os
import json
from ament_index_python.packages import get_package_share_directory
import subprocess
import time

class MapManagerNode(Node):
    def __init__(self):
        super().__init__('map_manager_node')
        package_name = 'cleanbit_simulate'

        self.map_path = os.path.join(get_package_share_directory(package_name), 'maps', 'home_map')
        self.pose_path = os.path.join(get_package_share_directory(package_name), 'maps', 'initial_pose.json')
        self.room_editor_path = os.path.join(os.path.dirname(__file__), 'room_editor.py')

        self.map_saved = False
        self.exploration_started = False
        self.current_pose = None

        self.frontier_sub = self.create_subscription(
            MarkerArray, '/explore/frontiers', self.frontier_callback, 10)

        self.pose_sub = self.create_subscription(
            Odometry, '/odom', self.odom_callback, 10)

        self.initialpose_pub = self.create_publisher(
            PoseWithCovarianceStamped, '/initialpose', 10)

        self.last_frontier_time = None
        self.watchdog = self.create_timer(2.0, self.check_exploration_done)
        self.timeout_sec = 10.0

        self.status_pub = self.create_publisher(String, '/mapping_status', 10)
        self.get_logger().info(f'MapManager avviato. Mappa verrà salvata in: {self.map_path}')

        self._pose_timer = self.create_timer(3.0, self._publish_saved_pose_once)

    def odom_callback(self, msg: Odometry):
        self.current_pose = msg.pose.pose

    def _publish_saved_pose_once(self):
        self._pose_timer.cancel()
        if not os.path.exists(self.pose_path):
            return
        try:
            with open(self.pose_path, 'r') as f:
                pose_data = json.load(f)
            self._publish_initialpose(
                pose_data['x'], pose_data['y'], pose_data['z'],
                pose_data['qx'], pose_data['qy'], pose_data['qz'], pose_data['qw']
            )
            self.get_logger().info(f'Pose iniziale pubblicata: x={pose_data["x"]:.2f}, y={pose_data["y"]:.2f}')
        except Exception as e:
            self.get_logger().error(f'Errore lettura pose: {e}')

    def _publish_initialpose(self, x, y, z, qx, qy, qz, qw):
        msg = PoseWithCovarianceStamped()
        msg.header.frame_id = 'map'
        msg.header.stamp = self.get_clock().now().to_msg()
        msg.pose.pose.position.x = x
        msg.pose.pose.position.y = y
        msg.pose.pose.position.z = z
        msg.pose.pose.orientation.x = qx
        msg.pose.pose.orientation.y = qy
        msg.pose.pose.orientation.z = qz
        msg.pose.pose.orientation.w = qw
        msg.pose.covariance[0]  = 0.25
        msg.pose.covariance[7]  = 0.25
        msg.pose.covariance[35] = 0.07
        self.initialpose_pub.publish(msg)

    def frontier_callback(self, msg: MarkerArray):
        if len(msg.markers) > 0:
            self.exploration_started = True
            self.last_frontier_time = self.get_clock().now()

    def check_exploration_done(self):
        if self.map_saved or not self.exploration_started:
            return
        if self.last_frontier_time is None:
            return
        elapsed = (self.get_clock().now() - self.last_frontier_time).nanoseconds / 1e9
        if elapsed > self.timeout_sec:
            self.get_logger().info('Nessuna frontiera da 10s → esplorazione completata!')
            self.save_map()

    def save_map(self):
        client = self.create_client(SaveMap, '/slam_toolbox/save_map')
        if not client.wait_for_service(timeout_sec=5.0):
            self.get_logger().error('Servizio /slam_toolbox/save_map non disponibile')
            return
        os.makedirs(os.path.dirname(self.map_path), exist_ok=True)
        req = SaveMap.Request()
        req.name.data = self.map_path
        future = client.call_async(req)
        future.add_done_callback(self.save_map_done)

    def save_map_done(self, future):
        try:
            future.result()
            self.map_saved = True
            self.get_logger().info(f'Mappa salvata in {self.map_path}!')

            if self.current_pose is not None:
                pose_data = {
                    'x':  self.current_pose.position.x,
                    'y':  self.current_pose.position.y,
                    'z':  self.current_pose.position.z,
                    'qx': self.current_pose.orientation.x,
                    'qy': self.current_pose.orientation.y,
                    'qz': self.current_pose.orientation.z,
                    'qw': self.current_pose.orientation.w,
                }
                with open(self.pose_path, 'w') as f:
                    json.dump(pose_data, f)
                self.get_logger().info(f'Pose salvata: x={pose_data["x"]:.2f}, y={pose_data["y"]:.2f}')

            map_yaml = self.map_path + '.yaml'
            proc = subprocess.Popen(
                ['python3', self.room_editor_path, '--map', map_yaml],
                env={**os.environ, 'DISPLAY': ':0'},
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE
            )

            time.sleep(2)
            if proc.poll() is not None:
                out, err = proc.communicate()
                self.get_logger().error(f'Room editor crashato!')
                self.get_logger().error(f'STDOUT: {out.decode()}')
                self.get_logger().error(f'STDERR: {err.decode()}')
            else:
                self.get_logger().info('Room editor avviato correttamente!')

            msg = String()
            msg.data = 'mapping_done'
            self.status_pub.publish(msg)

        except Exception as e:
            self.get_logger().error(f'Errore nel salvataggio mappa: {e}')


def main(args=None):
    rclpy.init(args=args)
    node = MapManagerNode()
    rclpy.spin(node)
    node.destroy_node()
    rclpy.shutdown()

if __name__ == '__main__':
    main()