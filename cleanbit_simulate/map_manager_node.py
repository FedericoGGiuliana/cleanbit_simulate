#!/usr/bin/env python3
import rclpy
from rclpy.node import Node
from visualization_msgs.msg import MarkerArray
from slam_toolbox.srv import SaveMap
from std_msgs.msg import Bool, String
import os
from ament_index_python.packages import get_package_share_directory
import subprocess
import time
from std_srvs.srv import SetBool

class MapManagerNode(Node):
    def __init__(self):
        super().__init__('map_manager_node')
        package_name = 'cleanbit_simulate'

        self.map_path = os.path.join(get_package_share_directory(package_name), 'maps', 'home_map')
        self.room_editor_path = os.path.join(
            os.path.dirname(__file__),
            'room_editor.py'
        )

        self.map_saved = False
        self.exploration_started = False

        self.frontier_sub = self.create_subscription(
            MarkerArray, '/explore/frontiers', self.frontier_callback, 10)
        self.explore_resume_sub = self.create_subscription(
            Bool, '/explore/resume', self.explore_resume_callback, 10)

        self.last_frontier_time = None
        self.watchdog = self.create_timer(2.0, self.check_exploration_done)
        self.timeout_sec = 10.0

        self.status_pub = self.create_publisher(String, '/mapping_status', 10)
        self.get_logger().info(f'MapManager avviato. Mappa verrà salvata in: {self.map_path}')

    def explore_resume_callback(self, msg: Bool): # Controlla da /explore/resume se l'esplorazione è in pausa
        if not msg.data:
            self.get_logger().info('Esplorazione fermata manualmente — reset stato')
            self.exploration_started = False
            self.last_frontier_time  = None
            self.map_saved           = False
            self.saving              = False

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

            map_yaml = self.map_path + '.yaml'
            self.get_logger().info(f'room_editor_path: {self.room_editor_path}')
            self.get_logger().info(f'room_editor esiste: {os.path.exists(self.room_editor_path)}')
            self.get_logger().info(f'map yaml esiste:   {os.path.exists(map_yaml)}')
            self.get_logger().info(f'DISPLAY: {os.environ.get("DISPLAY", "NON TROVATO")}')

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