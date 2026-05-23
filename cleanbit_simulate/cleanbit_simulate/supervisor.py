#!/usr/bin/env python3

import subprocess
import rclpy
from rclpy.node import Node
from std_msgs.msg import String
import json

class SupervisorNode(Node):

    def __init__(self):
        super().__init__('supervisor_node')
        self.nlp_sub = self.create_subscription(
            String, '/nlp_intent', self.intent_callback, 10)
        
        self.active_process = None  # processo di lancio attivo

        self.get_logger().info('Supervisor in ascolto su /nlp_intent')

    def intent_callback(self, msg: String):
        try:
            data = json.loads(msg.data)
        except json.JSONDecodeError as e:
            self.get_logger().error(f'JSON non valido: {e}')
            return

        intent = data.get('intent', '')
        self.get_logger().info(f'Intent ricevuto: {intent}')

        # Ferma il behaviour attivo
        self.stop_current_behaviour()

        # Avvia il behaviour corretto
        if intent == 'explore':
            self.launch('cleanbit_simulate', 'mapping.launch.py')
        else:
            self.get_logger().warn(f'Intent sconosciuto: {intent}')

    def launch(self, package: str, launch_file: str):
        self.get_logger().info(f'Avvio {launch_file}...')
        self.active_process = subprocess.Popen(
            ['ros2', 'launch', package, launch_file]
        )

    def stop_current_behaviour(self):
        if self.active_process and self.active_process.poll() is None:
            self.get_logger().info('Fermo il behaviour in corso...')
            self.active_process.terminate()
            self.active_process.wait()
            self.active_process = None


def main(args=None):
    rclpy.init(args=args)
    node = SupervisorNode()
    try:
        rclpy.spin(node)
    except KeyboardInterrupt:
        pass
    finally:
        node.stop_current_behaviour()
        node.destroy_node()
        rclpy.shutdown()

if __name__ == '__main__':
    main()