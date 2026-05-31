#!/usr/bin/env python3
import subprocess
import rclpy
from rclpy.node import Node
from std_msgs.msg import String
import json
import time


class SupervisorNode(Node):

    def __init__(self):
        super().__init__('supervisor_node')

        self.nlp_sub = self.create_subscription(
            String, '/nlp_intent', self.intent_callback, 10)

        # Publisher navigazione
        self.navigate_request_pub = self.create_publisher(String, '/goal_request',   10)
        self.navigate_avoid_pub   = self.create_publisher(String, '/navigate_avoid', 10)

        # Publisher cleaning
        self.clean_request_pub    = self.create_publisher(String, '/clean_request',  10)
        self.clean_avoid_pub      = self.create_publisher(String, '/clean_avoid',    10)

        self.active_process = None
        self.current_behaviour = None

        self.get_logger().info('Supervisor in ascolto su /nlp_intent')

    def intent_callback(self, msg: String):
        try:
            data = json.loads(msg.data)
        except json.JSONDecodeError as e:
            self.get_logger().error(f'JSON non valido: {e}')
            return

        # Legge intent e command dal formato NLU
        intent_block = data.get('intent', {})
        intent       = intent_block.get('name', '')
        confidence   = intent_block.get('confidence', 0.0)
        requires_clarification = intent_block.get('requires_clarification', False)
        command      = data.get('command', {})
        targets      = command.get('targets', [])
        avoid        = command.get('constraints', {}).get('avoid', [])

        self.get_logger().info(f'Intent: {intent} (confidence: {confidence:.2f})')

        # Ignora se richiede chiarimento
        if requires_clarification:
            dialogue = data.get('dialogue', {})
            question = dialogue.get('question', '')
            self.get_logger().warn(f'Chiarimento richiesto: {question}')
            return

        if intent == 'START_MAPPING':
            self.stop_current_behaviour()
            self.launch('cleanbit_simulate', 'mapping.launch.py')

        elif intent == 'GO_TO_AREA':
            if not targets:
                self.get_logger().warn('GO_TO_AREA senza targets, ignoro')
                return

            # Controlla se la mappa esiste
            from ament_index_python.packages import get_package_share_directory
            import os
            maps_dir  = os.path.join(get_package_share_directory('cleanbit_simulate'), 'maps')
            map_yaml  = os.path.join(maps_dir, 'home_map.yaml')
            map_pgm   = os.path.join(maps_dir, 'home_map.pgm')

            if not os.path.exists(map_yaml) or not os.path.exists(map_pgm):
                self.get_logger().error('Mappa non trovata — esegui prima il mapping!')
                return

            # Lancia navigation se non è già attiva
            if self.active_process is None or self.active_process.poll() is not None:
                self._launch_navigation()
                time.sleep(5.0)
            elif self.current_behaviour != 'navigation' and self.current_behaviour != 'return_home':
                self.stop_current_behaviour()
                self._launch_navigation()
                time.sleep(5.0)

            self._publish(self.navigate_avoid_pub, avoid)
            time.sleep(0.2)
            self._publish(self.navigate_request_pub, targets)

        elif intent == 'RETURN_HOME':

            # Controlla se la mappa esiste
            from ament_index_python.packages import get_package_share_directory
            import os
            maps_dir  = os.path.join(get_package_share_directory('cleanbit_simulate'), 'maps')
            map_yaml  = os.path.join(maps_dir, 'home_map.yaml')
            map_pgm   = os.path.join(maps_dir, 'home_map.pgm')

            if not os.path.exists(map_yaml) or not os.path.exists(map_pgm):
                self.get_logger().error('Mappa non trovata — esegui prima il mapping!')
                return

            # Lancia return_home se non è già attiva
            if self.active_process is None or self.active_process.poll() is not None:
                self._launch_navigation()
                time.sleep(5.0)
            elif self.current_behaviour != 'navigation' and self.current_behaviour != 'return_home':
                self.stop_current_behaviour()
                self._launch_navigation()
                time.sleep(5.0)

            self._publish(self.navigate_avoid_pub, avoid)
            time.sleep(0.2)
            self._publish(self.navigate_request_pub, ['home'])

        else:
            self.get_logger().warn(f'Intent sconosciuto: {intent}')
    
    def _launch_navigation(self):
        from ament_index_python.packages import get_package_share_directory
        import os
        map_path = os.path.join(
            get_package_share_directory('cleanbit_simulate'), 'maps', 'home_map.yaml')
        self.get_logger().info(f'Avvio navigazione con mappa: {map_path}')
        self.active_process = subprocess.Popen([
            'ros2', 'launch', 'cleanbit_simulate', 'navigation.launch.py',
            f'map_file:={map_path}'
        ])
        self.current_behaviour = 'navigation'

    def _publish(self, publisher, data: list):
        """Pubblica una lista come JSON string, solo se non vuota."""
        if data:
            msg = String()
            msg.data = json.dumps(data)
            publisher.publish(msg)

    def launch(self, package: str, launch_file: str):
        self.get_logger().info(f'Avvio {launch_file}...')
        self.active_process = subprocess.Popen(
            ['ros2', 'launch', package, launch_file]
        )
        self.current_behaviour = 'mapping' if 'mapping' in launch_file else 'navigation'

    def stop_current_behaviour(self):
        if self.active_process and self.active_process.poll() is None:
            self.get_logger().info('Fermo il behaviour in corso...')
            self.active_process.terminate()
            self.active_process.wait()
            self.active_process = None
            self.current_behaviour = None

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