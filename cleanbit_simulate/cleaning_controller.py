#!/usr/bin/env python3

import rclpy
from rclpy.node import Node
from rclpy.action import ActionClient
from std_msgs.msg import String, Bool
from geometry_msgs.msg import PoseStamped
from nav_msgs.msg import OccupancyGrid
from nav2_msgs.action import FollowWaypoints, NavigateToPose
from nav2_msgs.srv import ClearEntireCostmap
from ament_index_python.packages import get_package_share_directory
from rclpy.qos import QoSProfile, DurabilityPolicy, ReliabilityPolicy
import json
import os
import math
import yaml
import copy


class CleaningControllerNode(Node):

    def __init__(self):
        super().__init__('cleaning_controller_node')

        package_name = 'cleanbit_simulate'
        self.package_name = package_name

        self.rooms_path = os.path.join(
            get_package_share_directory(package_name), 'maps', 'rooms.json')
        self._load_rooms()

        map_yaml_path = os.path.join(
            get_package_share_directory(package_name), 'maps', 'home_map.yaml')
        self.base_map = self._load_map(map_yaml_path)

        # Parametri percorso
        self.wall_offset  = 0.20
        self.lane_spacing = 0.30

        # Subscriber
        self.clean_sub = self.create_subscription(String, '/clean_request', self.clean_callback, 10)
        self.avoid_sub = self.create_subscription(String, '/clean_avoid',   self.avoid_callback, 10)
        self.map_sub   = self.create_subscription(OccupancyGrid, '/map', self.map_callback, 1)
        self.stop_sub  = self.create_subscription(Bool, '/emergency_stop', self.stop_callback, 10)

        # Keepout publisher
        qos = QoSProfile(
            depth=1,
            durability=DurabilityPolicy.TRANSIENT_LOCAL,
            reliability=ReliabilityPolicy.RELIABLE
        )
        self.keepout_pub      = self.create_publisher(OccupancyGrid, '/keepout_mask', qos)
        self.unknown_room_pub = self.create_publisher(String, '/unknown_room', 10)

        # Action clients
        self.nav_client      = ActionClient(self, NavigateToPose, 'navigate_to_pose')
        self.waypoint_client = ActionClient(self, FollowWaypoints, 'follow_waypoints')

        # Stato
        self.pending_avoid   = []
        self.current_handle  = None
        self.pending_targets = []   # stanze ancora da pulire dopo il goto iniziale

        self.get_logger().info('CleaningController pronto, in ascolto su /clean_request')

    # ─────────────────────────────────────────────
    # ROOMS
    # ─────────────────────────────────────────────

    def _load_rooms(self):
        try:
            with open(self.rooms_path, 'r') as f:
                rooms_list = json.load(f)
            self.rooms = {r['name'].lower(): r for r in rooms_list}
            self.get_logger().info(f'Stanze caricate: {list(self.rooms.keys())}')
        except Exception as e:
            self.get_logger().error(f'Impossibile caricare rooms.json: {e}')
            self.rooms = {}

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
            grid.info.resolution           = meta['resolution']
            grid.info.width                = w
            grid.info.height               = h
            grid.info.origin.position.x    = meta['origin'][0]
            grid.info.origin.position.y    = meta['origin'][1]
            grid.info.origin.orientation.w = 1.0
            ros_data = []
            for val in data.flatten():
                if val < 50:    ros_data.append(100)
                elif val > 200: ros_data.append(0)
                else:           ros_data.append(-1)
            grid.data = ros_data
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
        client = self.create_client(
            ClearEntireCostmap, '/global_costmap/clear_entirely_global_costmap')
        if client.wait_for_service(timeout_sec=2.0):
            client.call_async(ClearEntireCostmap.Request())
        self.get_logger().info('Keepout mask pulita')

    # ─────────────────────────────────────────────
    # CALLBACK
    # ─────────────────────────────────────────────

    def avoid_callback(self, msg: String):
        try:
            self.pending_avoid = json.loads(msg.data)
            self.get_logger().info(f'Stanze da evitare: {self.pending_avoid}')
        except json.JSONDecodeError as e:
            self.get_logger().error(f'JSON avoid non valido: {e}')

    def clean_callback(self, msg: String):
        self._load_rooms()
        try:
            targets = json.loads(msg.data)
        except json.JSONDecodeError as e:
            self.get_logger().error(f'JSON clean_request non valido: {e}')
            return

        self.get_logger().info(f'Pulizia richiesta per: {targets}')

        # Controlla stanze sconosciute
        unknown = [t for t in targets if t.strip().lower() not in self.rooms]
        if unknown:
            self.get_logger().warn(f'Stanze sconosciute: {unknown}')
            unknown_msg = String()
            unknown_msg.data = json.dumps(unknown)
            self.unknown_room_pub.publish(unknown_msg)
            return

        # Keepout per avoid
        if self.pending_avoid:
            self.publish_keepout_mask(self.pending_avoid)

        # Salva tutte le stanze da pulire
        self.pending_targets = [t.strip().lower() for t in targets]

        # Prima vai al centro della prima stanza
        self._goto_room_center(self.pending_targets[0])

    # ─────────────────────────────────────────────
    # GOTO CENTRO STANZA
    # ─────────────────────────────────────────────

    def _goto_room_center(self, room_name: str):
        room  = self.rooms[room_name]
        world = room['world']

        self.get_logger().info(f'Vado al centro di "{room_name}" prima di pulire...')

        if not self.nav_client.wait_for_server(timeout_sec=3.0):
            self.get_logger().error('Action server navigate_to_pose non disponibile')
            self.clear_keepout_mask()
            return

        goal = NavigateToPose.Goal()
        goal.pose = PoseStamped()
        goal.pose.header.frame_id    = 'map'
        goal.pose.header.stamp       = self.get_clock().now().to_msg()
        goal.pose.pose.position.x    = world['center_x']
        goal.pose.pose.position.y    = world['center_y']
        goal.pose.pose.orientation.w = 1.0

        future = self.nav_client.send_goal_async(goal)
        future.add_done_callback(self._goto_response_callback)

    def _goto_response_callback(self, future):
        handle = future.result()
        if not handle.accepted:
            self.get_logger().warn('Goto centro stanza rifiutato, avvio pulizia direttamente')
            self._start_cleaning()
            return
        self.get_logger().info('Raggiungimento centro stanza accettato...')
        result_future = handle.get_result_async()
        result_future.add_done_callback(self._goto_result_callback)

    def _goto_result_callback(self, future):
        self.get_logger().info('Centro stanza raggiunto, avvio pulizia!')
        self._start_cleaning()

    # ─────────────────────────────────────────────
    # PULIZIA
    # ─────────────────────────────────────────────

    def _start_cleaning(self):
        all_waypoints = []
        for room_name in self.pending_targets:
            room      = self.rooms[room_name]
            waypoints = self._generate_boustrophedon(room)
            all_waypoints.extend(waypoints)
            self.get_logger().info(
                f'Stanza "{room_name}": {len(waypoints)} waypoint generati')

        if not all_waypoints:
            self.get_logger().error('Nessun waypoint generato')
            self.clear_keepout_mask()
            return

        self.get_logger().info(f'Totale waypoint: {len(all_waypoints)}')
        self.follow_waypoints(all_waypoints)

    def _generate_boustrophedon(self, room: dict) -> list:
        world = room['world']
        x_min = world['x_min'] + self.wall_offset
        x_max = world['x_max'] - self.wall_offset
        y_min = world['y_min'] + self.wall_offset
        y_max = world['y_max'] - self.wall_offset

        if x_min >= x_max or y_min >= y_max:
            self.get_logger().warn(f'Stanza "{room["name"]}" troppo piccola, saltata')
            return []

        waypoints = []

        # Perimetro
        perimeter = [
            (x_min, y_min), (x_max, y_min),
            (x_max, y_max), (x_min, y_max), (x_min, y_min)
        ]
        for i in range(len(perimeter) - 1):
            x, y = perimeter[i]
            xn, yn = perimeter[i + 1]
            yaw = math.atan2(yn - y, xn - x)
            waypoints.append(self._make_pose(x, y, yaw))

        # Corsie boustrophedon
        y = y_min
        direction = 1
        while y <= y_max:
            if direction == 1:
                x_start, x_end, yaw = x_min, x_max, 0.0
            else:
                x_start, x_end, yaw = x_max, x_min, math.pi
            waypoints.append(self._make_pose(x_start, y, yaw))
            waypoints.append(self._make_pose(x_end,   y, yaw))
            y += self.lane_spacing
            direction *= -1

        return waypoints

    def _make_pose(self, x: float, y: float, yaw: float) -> PoseStamped:
        pose = PoseStamped()
        pose.header.frame_id    = 'map'
        pose.header.stamp       = self.get_clock().now().to_msg()
        pose.pose.position.x    = float(x)
        pose.pose.position.y    = float(y)
        pose.pose.orientation.z = math.sin(yaw / 2.0)
        pose.pose.orientation.w = math.cos(yaw / 2.0)
        return pose

    def follow_waypoints(self, waypoints: list):
        if not self.waypoint_client.wait_for_server(timeout_sec=3.0):
            self.get_logger().error('Action server follow_waypoints non disponibile')
            self.clear_keepout_mask()
            return

        goal       = FollowWaypoints.Goal()
        goal.poses = waypoints

        self.get_logger().info(f'Avvio pulizia con {len(waypoints)} waypoint...')
        future = self.waypoint_client.send_goal_async(
            goal, feedback_callback=self.feedback_callback)
        future.add_done_callback(self.goal_response_callback)

    def goal_response_callback(self, future):
        self.current_handle = future.result()
        if not self.current_handle.accepted:
            self.get_logger().warn('Waypoints rifiutati da Nav2')
            self.clear_keepout_mask()
            self.pending_avoid = []
            return
        self.get_logger().info('Pulizia avviata!')
        result_future = self.current_handle.get_result_async()
        result_future.add_done_callback(self.result_callback)

    def result_callback(self, future):
        result = future.result().result
        missed = result.missed_waypoints
        if missed:
            self.get_logger().warn(f'Waypoint mancati: {list(missed)}')
        else:
            self.get_logger().info('Pulizia completata!')
        self.clear_keepout_mask()
        self.pending_avoid   = []
        self.pending_targets = []
        self.current_handle  = None

    def feedback_callback(self, feedback_msg):
        idx = feedback_msg.feedback.current_waypoint
        self.get_logger().info(
            f'Waypoint {idx + 1} raggiunto',
            throttle_duration_sec=3.0)

    # ─────────────────────────────────────────────
    # EMERGENCY STOP
    # ─────────────────────────────────────────────

    def stop_callback(self, msg: Bool):
        if not msg.data:
            return
        self.get_logger().warn('Emergency stop ricevuto!')
        if self.current_handle:
            self.current_handle.cancel_goal_async()
            self.current_handle = None
        self.pending_targets = []
        self.clear_keepout_mask()
        self.pending_avoid = []


def main(args=None):
    rclpy.init(args=args)
    node = CleaningControllerNode()
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