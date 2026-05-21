#!/usr/bin/env python3

import math
import json
import os
import rclpy

from rclpy.node import Node
from rclpy.action import ActionClient
from nav2_msgs.action import NavigateToPose
from geometry_msgs.msg import PoseStamped


class CleaningController(Node):
    def __init__(self):
        super().__init__('cleaning_controller')

        self.nav_client = ActionClient(
            self,
            NavigateToPose,
            '/navigate_to_pose'
        )

        self.wall_offset = 0.30
        self.lane_spacing = 0.35

        self.goals = []
        self.current_goal_index = 0

        self.rooms = self.load_rooms_from_json()

        self.get_logger().info(f"Caricate {len(self.rooms)} stanze dal JSON.")
        self.get_logger().info("Aspetto Nav2 action server...")

        self.nav_client.wait_for_server()

        self.get_logger().info("Nav2 pronto. Genero percorso di pulizia.")

        self.generate_cleaning_path()
        self.send_next_goal()

    def load_rooms_from_json(self):
        json_path = os.path.expanduser(
            '~/ros_ws/spazz_ws_clone/src/cleanbit_simulate/cleanbit_simulate/room.json'
        )

        with open(json_path, "r") as file:
            data = json.load(file)

        rooms = []

        for room in data[:6]:
            name = room["name"]
            world = room["world"]

            x_min = world["x_min"]
            y_min = world["y_min"]
            x_max = world["x_max"]
            y_max = world["y_max"]

            room_points = [
                (x_min, y_min),
                (x_max, y_min),
                (x_max, y_max),
                (x_min, y_max),
            ]

            rooms.append({
                "name": name,
                "points": room_points,
                "center": (
                    world["center_x"],
                    world["center_y"]
                )
            })

        return rooms

    def generate_cleaning_path(self):
        for room in self.rooms:
            room_name = room["name"]
            room_points = room["points"]

            self.get_logger().info(f"Genero path per stanza: {room_name}")

            x_min = min(p[0] for p in room_points)
            x_max = max(p[0] for p in room_points)
            y_min = min(p[1] for p in room_points)
            y_max = max(p[1] for p in room_points)

            x_min += self.wall_offset
            x_max -= self.wall_offset
            y_min += self.wall_offset
            y_max -= self.wall_offset

            if x_min >= x_max or y_min >= y_max:
                self.get_logger().warn(
                    f"Stanza {room_name} troppo piccola dopo wall_offset. Saltata."
                )
                continue

            perimeter = [
                (x_min, y_min),
                (x_max, y_min),
                (x_max, y_max),
                (x_min, y_max),
                (x_min, y_min),
            ]

            for i in range(len(perimeter) - 1):
                x, y = perimeter[i]
                x_next, y_next = perimeter[i + 1]
                yaw = math.atan2(y_next - y, x_next - x)
                self.goals.append((x, y, yaw))

            y = y_min
            direction = 1

            while y <= y_max:
                if direction == 1:
                    x_start = x_min
                    x_end = x_max
                    yaw = 0.0
                else:
                    x_start = x_max
                    x_end = x_min
                    yaw = math.pi

                self.goals.append((x_start, y, yaw))
                self.goals.append((x_end, y, yaw))

                y += self.lane_spacing
                direction *= -1

        self.get_logger().info(
            f"Generati {len(self.goals)} goal totali."
        )

    def create_pose_stamped(self, x, y, yaw):
        pose = PoseStamped()

        pose.header.frame_id = 'map'
        pose.header.stamp = self.get_clock().now().to_msg()

        pose.pose.position.x = float(x)
        pose.pose.position.y = float(y)
        pose.pose.position.z = 0.0

        pose.pose.orientation.z = math.sin(yaw / 2.0)
        pose.pose.orientation.w = math.cos(yaw / 2.0)

        return pose

    def send_next_goal(self):
        if self.current_goal_index >= len(self.goals):
            self.get_logger().info("Pulizia completata.")
            return

        x, y, yaw = self.goals[self.current_goal_index]

        goal_msg = NavigateToPose.Goal()
        goal_msg.pose = self.create_pose_stamped(x, y, yaw)

        self.get_logger().info(
            f"Mando goal {self.current_goal_index + 1}/{len(self.goals)}: "
            f"x={x:.2f}, y={y:.2f}, yaw={yaw:.2f}"
        )

        future = self.nav_client.send_goal_async(goal_msg)
        future.add_done_callback(self.goal_response_callback)

    def goal_response_callback(self, future):
        goal_handle = future.result()

        if not goal_handle.accepted:
            self.get_logger().warn("Goal rifiutato da Nav2. Passo al prossimo.")
            self.current_goal_index += 1
            self.send_next_goal()
            return

        self.get_logger().info("Goal accettato da Nav2.")

        result_future = goal_handle.get_result_async()
        result_future.add_done_callback(self.result_callback)

    def result_callback(self, future):
        self.get_logger().info(
            f"Goal {self.current_goal_index + 1} completato."
        )

        self.current_goal_index += 1
        self.send_next_goal()


def main(args=None):
    rclpy.init(args=args)

    node = CleaningController()

    try:
        rclpy.spin(node)
    except KeyboardInterrupt:
        pass

    node.destroy_node()
    rclpy.shutdown()


if __name__ == '__main__':
    main()