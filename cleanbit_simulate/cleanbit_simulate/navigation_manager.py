#!/usr/bin/env python3

import rclpy
from rclpy.node import Node
from rclpy.action import ActionClient
from std_msgs.msg import String
from geometry_msgs.msg import PoseStamped, PoseWithCovarianceStamped
from nav2_msgs.action import FollowWaypoints
from nav_msgs.msg import OccupancyGrid
from ament_index_python.packages import get_package_share_directory
import json
import os
import math
import yaml
import copy
from rclpy.qos import QoSProfile, DurabilityPolicy, ReliabilityPolicy


class NavigationManagerNode(Node):

    def __init__(self):
        super().__init__('navigation_manager_node')

        package_name = 'cleanbit_simulate'

        # Carica rooms.json
        rooms_path = os.path.join(
            get_package_share_directory(package_name), 'maps', 'rooms.json')
        try:
            with open(rooms_path, 'r') as f:
                rooms_list = json.load(f)
            self.rooms = {r['name'].lower(): r for r in rooms_list}
            self.get_logger().info(f'Stanze caricate: {list(self.rooms.keys())}')
        except Exception as e:
            self.get_logger().error(f'Impossibile caricare rooms.json: {e}')
            self.rooms = {}

        # Carica mappa base per generare la keepout mask
        map_yaml_path = os.path.join(
            get_package_share_directory(package_name), 'maps', 'home_map.yaml')
        self.base_map = self._load_map(map_yaml_path)

        # Subscriber
        self.goal_sub  = self.create_subscription(String, '/goal_request',  self.goal_callback,  10)
        self.avoid_sub = self.create_subscription(String, '/navigate_avoid', self.avoid_callback, 10)

        self.map_sub = self.create_subscription(
            OccupancyGrid, '/map', self.map_callback, 1)

        qos = QoSProfile(
            depth=1,
            durability=DurabilityPolicy.TRANSIENT_LOCAL,
            reliability=ReliabilityPolicy.RELIABLE
        )

        self.keepout_pub = self.create_publisher(OccupancyGrid, '/keepout_mask', qos)

        # Publisher pose iniziale per AMCL
        self.initialpose_pub = self.create_publisher(
            PoseWithCovarianceStamped, '/initialpose', 10)

        # Action client
        self.waypoint_client = ActionClient(self, FollowWaypoints, 'follow_waypoints')

        # Stato
        self.pending_avoid       = []
        self.current_goal_handle = None

        self.get_logger().info('NavigationManager pronto')

        # Pubblica la pose iniziale salvata dopo 3s (aspetta che AMCL sia attivo)
        self._pose_timer = self.create_timer(3.0, self._publish_saved_pose_once)

    # ─────────────────────────────────────────────
    # POSE INIZIALE
    # ─────────────────────────────────────────────

    def _publish_saved_pose_once(self):
        self._pose_timer.cancel()
        """Legge initial_pose.json e la manda ad AMCL una sola volta."""
        pose_path = os.path.join(
            get_package_share_directory('cleanbit_simulate'), 'maps', 'initial_pose.json')

        if not os.path.exists(pose_path):
            self.get_logger().warn('initial_pose.json non trovato, AMCL usa pose default (0,0)')
            return

        try:
            with open(pose_path, 'r') as f:
                p = json.load(f)

            msg = PoseWithCovarianceStamped()
            msg.header.frame_id = 'map'
            msg.header.stamp    = self.get_clock().now().to_msg()
            msg.pose.pose.position.x    = p['x']
            msg.pose.pose.position.y    = p['y']
            msg.pose.pose.position.z    = p['z']
            msg.pose.pose.orientation.x = p['qx']
            msg.pose.pose.orientation.y = p['qy']
            msg.pose.pose.orientation.z = p['qz']
            msg.pose.pose.orientation.w = p['qw']
            msg.pose.covariance[0]  = 0.25
            msg.pose.covariance[7]  = 0.25
            msg.pose.covariance[35] = 0.07

            self.initialpose_pub.publish(msg)
            self.get_logger().info(
                f'Pose iniziale inviata ad AMCL: x={p["x"]:.2f}, y={p["y"]:.2f}')

        except Exception as e:
            self.get_logger().error(f'Errore lettura initial_pose.json: {e}')

    # ─────────────────────────────────────────────
    # MAPPA
    # ─────────────────────────────────────────────

    def _load_map(self, yaml_path: str):
        try:
            with open(yaml_path, 'r') as f:
                meta = yaml.safe_load(f)

            pgm_path = os.path.join(os.path.dirname(yaml_path), meta['image'])
            from PIL import Image
            import numpy as np

            img  = Image.open(pgm_path).convert('L')
            data = np.array(img)
            h, w = data.shape

            grid = OccupancyGrid()
            grid.info.resolution        = meta['resolution']
            grid.info.width             = w
            grid.info.height            = h
            grid.info.origin.position.x = meta['origin'][0]
            grid.info.origin.position.y = meta['origin'][1]
            grid.info.origin.orientation.w = 1.0

            ros_data = []
            for val in data.flatten():
                if val < 50:
                    ros_data.append(100)
                elif val > 200:
                    ros_data.append(0)
                else:
                    ros_data.append(-1)
            grid.data = ros_data

            self.get_logger().info(f'Mappa base caricata: {w}x{h} px')
            return grid

        except Exception as e:
            self.get_logger().error(f'Errore caricamento mappa: {e}')
            return None

    def map_callback(self, msg: OccupancyGrid):
        if self.base_map:
            self.base_map.header = msg.header

    # ─────────────────────────────────────────────
    # KEEPOUT MASK
    # ─────────────────────────────────────────────

    def publish_keepout_mask(self, room_names: list):
        if not self.base_map:
            self.get_logger().warn('Mappa base non disponibile')
            return

        mask = copy.deepcopy(self.base_map)
        mask.header.stamp    = self.get_clock().now().to_msg()
        mask.header.frame_id = 'map'

        data = [0] * (mask.info.width * mask.info.height)

        res = mask.info.resolution
        ox  = mask.info.origin.position.x
        oy  = mask.info.origin.position.y
        w   = mask.info.width
        h   = mask.info.height

        for room_name in room_names:
            room = self.rooms.get(room_name.lower())
            if not room or 'world' not in room:
                self.get_logger().warn(f'Stanza "{room_name}" non trovata')
                continue

            world  = room['world']
            px_min = max(0, int((world['x_min'] - ox) / res))
            px_max = min(w, int((world['x_max'] - ox) / res))
            py_min = max(0, int((world['y_min'] - oy) / res))
            py_max = min(h, int((world['y_max'] - oy) / res))

            for py in range(py_min, py_max + 1):
                for px in range(px_min, px_max + 1):
                    idx = py * w + px
                    if 0 <= idx < len(data):
                        data[idx] = 100

            self.get_logger().info(f'Keepout aggiunto per: {room_name}')

        mask.data = data
        self.keepout_pub.publish(mask)

    def clear_keepout_mask(self):
        if not self.base_map:
            return

        mask = copy.deepcopy(self.base_map)
        mask.header.stamp    = self.get_clock().now().to_msg()
        mask.header.frame_id = 'map'
        mask.data = [0] * (mask.info.width * mask.info.height)
        self.keepout_pub.publish(mask)
        self.get_logger().info('Keepout mask pulita')

        from nav2_msgs.srv import ClearEntireCostmap
        client = self.create_client(
            ClearEntireCostmap, '/global_costmap/clear_entirely_global_costmap')
        if client.wait_for_service(timeout_sec=2.0):
            client.call_async(ClearEntireCostmap.Request())
            self.get_logger().info('Costmap forzata al ricalcolo')

    # ─────────────────────────────────────────────
    # CALLBACK
    # ─────────────────────────────────────────────

    def avoid_callback(self, msg: String):
        try:
            self.pending_avoid = json.loads(msg.data)
            self.get_logger().info(f'Stanze da evitare: {self.pending_avoid}')
        except json.JSONDecodeError as e:
            self.get_logger().error(f'JSON avoid non valido: {e}')

    def goal_callback(self, msg: String):
        try:
            targets = json.loads(msg.data)
        except json.JSONDecodeError as e:
            self.get_logger().error(f'JSON goal non valido: {e}')
            return

        self.get_logger().info(f'Target: {targets}, Avoid: {self.pending_avoid}')

        waypoints = []
        for room_name in targets:
            room = self.rooms.get(room_name.strip().lower())
            if not room:
                self.get_logger().error(f'Stanza "{room_name}" non trovata')
                continue
            pose = PoseStamped()
            pose.header.frame_id    = 'map'
            pose.header.stamp       = self.get_clock().now().to_msg()
            pose.pose.position.x    = room['world']['center_x']
            pose.pose.position.y    = room['world']['center_y']
            pose.pose.orientation.w = 1.0
            waypoints.append(pose)

        if not waypoints:
            self.get_logger().error('Nessun waypoint valido')
            return

        if self.pending_avoid:
            self.publish_keepout_mask(self.pending_avoid)

        self.follow_waypoints(waypoints)

    # ─────────────────────────────────────────────
    # NAVIGAZIONE
    # ─────────────────────────────────────────────

    def follow_waypoints(self, waypoints: list):
        if not self.waypoint_client.wait_for_server(timeout_sec=3.0):
            self.get_logger().error('Action server follow_waypoints non disponibile')
            return

        goal       = FollowWaypoints.Goal()
        goal.poses = waypoints

        self.get_logger().info(f'Invio {len(waypoints)} waypoint a Nav2...')
        future = self.waypoint_client.send_goal_async(
            goal, feedback_callback=self.feedback_callback)
        future.add_done_callback(self.goal_response_callback)

    def goal_response_callback(self, future):
        self.current_goal_handle = future.result()
        if not self.current_goal_handle.accepted:
            self.get_logger().warn('Waypoints rifiutati da Nav2')
            self.clear_keepout_mask()
            self.pending_avoid = []
            return
        self.get_logger().info('Waypoints accettati, navigando...')
        result_future = self.current_goal_handle.get_result_async()
        result_future.add_done_callback(self.result_callback)

    def result_callback(self, future):
        result = future.result().result
        missed = result.missed_waypoints
        if missed:
            self.get_logger().warn(f'Waypoints mancati: {list(missed)}')
        else:
            self.get_logger().info('Tutti i waypoint raggiunti!')

        self.clear_keepout_mask()
        self.pending_avoid       = []
        self.current_goal_handle = None

    def feedback_callback(self, feedback_msg):
        idx = feedback_msg.feedback.current_waypoint
        self.get_logger().info(
            f'Navigando verso waypoint {idx + 1}',
            throttle_duration_sec=2.0)


def main(args=None):
    rclpy.init(args=args)
    node = NavigationManagerNode()
    try:
        rclpy.spin(node)
    except KeyboardInterrupt:
        pass
    finally:
        node.clear_keepout_mask()
        node.destroy_node()
        rclpy.shutdown()


if __name__ == '__main__':
    main()