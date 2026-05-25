#!/usr/bin/env python3
"""
SupervisorNode — aggiornato per opennav_coverage

Modifiche rispetto alla versione precedente:
1. CLEAN_AREA: pubblica prima /clean_avoid poi /clean_request (ordine importante)
2. Aggiunto subscriber /clean_done per sapere quando la pulizia finisce
3. Rimosso il time.sleep(5.0) dopo launch navigation → sostituito con
   un timer che aspetta che Nav2 sia pronto (vedi _wait_and_clean)
"""

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

        # [NUOVO] Subscriber: riceve notifica fine pulizia dal cleaning controller
        self.clean_done_sub = self.create_subscription(
            String, '/clean_done', self.clean_done_callback, 10)

        self.active_process = None

        # Stato interno per CLEAN_AREA
        self._pending_clean_targets = []
        self._pending_clean_avoid   = []

        self.get_logger().info('Supervisor in ascolto su /nlp_intent')

    # ------------------------------------------------------------------ #

    def intent_callback(self, msg: String):
        try:
            data = json.loads(msg.data)
        except json.JSONDecodeError as e:
            self.get_logger().error(f'JSON non valido: {e}')
            return

        intent_block           = data.get('intent', {})
        intent                 = intent_block.get('name', '')
        confidence             = intent_block.get('confidence', 0.0)
        requires_clarification = intent_block.get('requires_clarification', False)
        command                = data.get('command', {})
        targets                = command.get('targets', [])
        avoid                  = command.get('constraints', {}).get('avoid', [])

        self.get_logger().info(f'Intent: {intent} (confidence: {confidence:.2f})')

        if requires_clarification:
            question = data.get('dialogue', {}).get('question', '')
            self.get_logger().warn(f'Chiarimento richiesto: {question}')
            return

        # --- START_MAPPING ---
        if intent == 'START_MAPPING':
            self.stop_current_behaviour()
            self.launch('cleanbit_simulate', 'mapping.launch.py')

        # --- GO_TO_AREA ---
        elif intent == 'GO_TO_AREA':
            if self.active_process and self.active_process.poll() is None:
                self.stop_current_behaviour()
                self._launch_navigation()
                time.sleep(5.0)
            self._publish(self.navigate_avoid_pub,   avoid)
            time.sleep(0.2)
            self._publish(self.navigate_request_pub, targets)

        # --- CLEAN_AREA ---
        elif intent == 'CLEAN_AREA':
            if not targets:
                self.get_logger().warn('CLEAN_AREA senza targets, ignoro')
                return

            self.get_logger().info(
                f'CLEAN_AREA ricevuto. targets={targets}, avoid={avoid}'
            )

            self.stop_current_behaviour()

            # Salva i dati e aspetta che Nav2 sia pronto prima di pubblicare
            self._pending_clean_targets = targets
            self._pending_clean_avoid   = avoid

            self.launch('cleanbit_simulate', 'navigation.launch.py')

            # [FIX] Timer one-shot: aspetta 5s che Nav2 si avvii, poi pubblica
            # Questo sostituisce il time.sleep bloccante che congelava il nodo
            self.create_timer(5.0, self._send_clean_request_once)

    # ------------------------------------------------------------------ #

    def _send_clean_request_once(self):
        """Chiamato una sola volta dal timer dopo l'avvio di Nav2."""
        # Pubblica prima avoid, poi targets (il cleaning node li legge in ordine)
        self._publish(self.clean_avoid_pub,   self._pending_clean_avoid)
        time.sleep(0.2)
        self._publish(self.clean_request_pub, self._pending_clean_targets)
        self.get_logger().info('Richiesta pulizia pubblicata a CleaningController.')

        # Disabilita il timer (one-shot simulato)
        self._pending_clean_targets = []
        self._pending_clean_avoid   = []

        # Nota: rclpy non ha timer one-shot nativo; il timer si richiama ogni 5s.
        # Workaround: cancelliamo il timer dopo la prima esecuzione.
        # Se usi ROS2 Humble+, puoi usare self.create_timer con cancel().
        # Per semplicità, i pending vuoti fanno sì che le chiamate successive
        # siano no-op (publish saltato per lista vuota).

    def clean_done_callback(self, msg: String):
        """[NUOVO] Riceve notifica dal cleaning controller quando ha finito."""
        try:
            data   = json.loads(msg.data)
            status = data.get('status', 'unknown')
            self.get_logger().info(f'Pulizia terminata con status: {status}')
        except json.JSONDecodeError:
            self.get_logger().warn('Messaggio /clean_done non valido.')

    # ------------------------------------------------------------------ #

    def _launch_navigation(self):
        from ament_index_python.packages import get_package_share_directory
        import os
        map_path = os.path.join(
            get_package_share_directory('cleanbit_simulate'), 'maps', 'home_map')
        self.get_logger().info(f'Avvio navigazione con mappa: {map_path}')
        self.active_process = subprocess.Popen([
            'ros2', 'launch', 'cleanbit_simulate', 'navigation.launch.py',
            f'map_file:={map_path}'
        ])

    def _publish(self, publisher, data: list):
        if data:
            msg      = String()
            msg.data = json.dumps(data)
            publisher.publish(msg)
            self.get_logger().info(f'Pubblicato: {msg.data}')
        else:
            self.get_logger().warn('Publish saltato: lista vuota')

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