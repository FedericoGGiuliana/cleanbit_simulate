#!/usr/bin/env python3
"""
CleaningController — integrato con opennav_coverage (Fields2Cover)

Ascolta /clean_request dal supervisor, estrae i poligoni delle stanze
dal JSON, e li manda all'action server opennav_coverage.
Pubblica su /clean_done quando la pulizia è completata.
"""

import json
import os
import rclpy

from rclpy.node import Node
from rclpy.action import ActionClient
from rclpy.callback_groups import ReentrantCallbackGroup

from std_msgs.msg import String
from geometry_msgs.msg import Polygon, Point32

# Action di opennav_coverage
# Se non ancora installato: ros-humble-opennav-coverage
from opennav_coverage_msgs.action import NavigateCompleteCoverage


class CleaningController(Node):

    def __init__(self):
        super().__init__('cleaning_controller')

        self.callback_group = ReentrantCallbackGroup()

        # --- Subscriber: riceve targets dal supervisor ---
        self.clean_sub = self.create_subscription(
            String,
            '/clean_request',
            self.clean_request_callback,
            10,
            callback_group=self.callback_group
        )

        # --- Subscriber: stanze da evitare ---
        self.avoid_sub = self.create_subscription(
            String,
            '/clean_avoid',
            self.avoid_callback,
            10,
            callback_group=self.callback_group
        )

        # --- Publisher: notifica supervisor al termine ---
        self.done_pub = self.create_publisher(String, '/clean_done', 10)

        # --- Action client verso opennav_coverage ---
        self.coverage_client = ActionClient(
            self,
            NavigateCompleteCoverage,
            'navigate_complete_coverage',
            callback_group=self.callback_group
        )

        # Offset dal muro e larghezza del robot (= lane spacing)
        self.declare_parameter('wall_offset', 0.30)
        self.declare_parameter('robot_width', 0.35)  # larghezza spazzola

        self.wall_offset  = self.get_parameter('wall_offset').value
        self.robot_width  = self.get_parameter('robot_width').value

        self.rooms_data   = self.load_rooms_from_json()
        self.avoid_rooms  = []

        # Coda di stanze da pulire (processate in sequenza)
        self.queue        = []
        self.is_cleaning  = False

        self.get_logger().info(
            f'CleaningController pronto. {len(self.rooms_data)} stanze caricate.'
        )

    # ------------------------------------------------------------------ #
    #  CARICAMENTO JSON (stesso path del codice precedente)               #
    # ------------------------------------------------------------------ #

    def load_rooms_from_json(self) -> dict:
        """Restituisce un dict {nome_stanza: room_dict} dal JSON."""
        json_path = self._find_json()
        self.get_logger().info(f'Carico rooms da: {json_path}')

        with open(json_path, 'r') as f:
            data = json.load(f)

        rooms = {}
        for room in data:
            name  = room['name']
            world = room['world']
            rooms[name] = {
                'name': name,
                'x_min': world['x_min'],
                'y_min': world['y_min'],
                'x_max': world['x_max'],
                'y_max': world['y_max'],
            }
        return rooms

    def _find_json(self) -> str:
        current_dir = os.path.dirname(os.path.abspath(__file__))
        while current_dir != '/':
            for candidate in [
                os.path.join(current_dir, 'src', 'cleanbit_simulate', 'maps', 'rooms.json'),
                os.path.join(current_dir, 'maps', 'rooms.json'),
            ]:
                if os.path.exists(candidate):
                    return candidate
            current_dir = os.path.dirname(current_dir)

        # Fallback: ament
        try:
            from ament_index_python.packages import get_package_share_directory
            return os.path.join(
                get_package_share_directory('cleanbit_simulate'),
                'maps', 'rooms.json'
            )
        except Exception:
            raise FileNotFoundError('rooms.json non trovato.')

    # ------------------------------------------------------------------ #
    #  CALLBACK SUBSCRIBER                                                 #
    # ------------------------------------------------------------------ #

    def avoid_callback(self, msg: String):
        try:
            self.avoid_rooms = json.loads(msg.data)
            self.get_logger().info(f'Stanze da evitare: {self.avoid_rooms}')
        except json.JSONDecodeError:
            self.get_logger().error('JSON non valido su /clean_avoid')

    def clean_request_callback(self, msg: String):
        try:
            targets = json.loads(msg.data)   # es. ["cucina", "salotto"]
        except json.JSONDecodeError:
            self.get_logger().error('JSON non valido su /clean_request')
            return

        self.get_logger().info(f'Richiesta pulizia: {targets}')

        # Filtra stanze riconosciute ed escludi avoid
        self.queue = [
            name for name in targets
            if name in self.rooms_data and name not in self.avoid_rooms
        ]

        not_found = [n for n in targets if n not in self.rooms_data]
        if not_found:
            self.get_logger().warn(f'Stanze non trovate nel JSON: {not_found}')

        if not self.queue:
            self.get_logger().warn('Nessuna stanza valida da pulire.')
            return

        if self.is_cleaning:
            self.get_logger().warn(
                'Pulizia già in corso. La nuova coda sovrascrive quella precedente.'
            )
            # opennav_coverage non supporta cancel nativo qui,
            # ma puoi estendere con cancel_goal_async se necessario.

        self.is_cleaning = True
        self._clean_next()

    # ------------------------------------------------------------------ #
    #  LOGICA DI PULIZIA SEQUENZIALE                                       #
    # ------------------------------------------------------------------ #

    def _clean_next(self):
        """Preleva la prossima stanza dalla coda e avvia la copertura."""
        if not self.queue:
            self.get_logger().info('✅ Tutte le stanze pulite.')
            self.is_cleaning = False
            done_msg = String()
            done_msg.data = json.dumps({'status': 'done'})
            self.done_pub.publish(done_msg)
            return

        room_name = self.queue.pop(0)
        room      = self.rooms_data[room_name]

        self.get_logger().info(f'▶ Pulizia stanza: {room_name}')

        polygon = self._room_to_polygon(room)
        self._send_coverage_goal(room_name, polygon)

    def _room_to_polygon(self, room: dict) -> Polygon:
        """
        Converte il bounding box della stanza in un Polygon ROS,
        applicando il wall_offset verso l'interno.
        """
        offset = self.wall_offset
        x_min  = room['x_min'] + offset
        x_max  = room['x_max'] - offset
        y_min  = room['y_min'] + offset
        y_max  = room['y_max'] - offset

        poly = Polygon()
        poly.points = [
            Point32(x=float(x_min), y=float(y_min), z=0.0),
            Point32(x=float(x_max), y=float(y_min), z=0.0),
            Point32(x=float(x_max), y=float(y_max), z=0.0),
            Point32(x=float(x_min), y=float(y_max), z=0.0),
        ]
        return poly

    def _send_coverage_goal(self, room_name: str, polygon: Polygon):
        """Manda il goal a opennav_coverage e registra i callback."""

        if not self.coverage_client.wait_for_server(timeout_sec=60.0):
            self.get_logger().error(
                'Action server navigate_complete_coverage non disponibile!'
            )
            self.is_cleaning = False
            return

        goal = NavigateCompleteCoverage.Goal()

        # --- Poligono dell'area da coprire ---
        goal.frame_id  = 'map'
        goal.polygons  = [polygon]

        # --- Parametri Fields2Cover ---
        # Larghezza swath = larghezza robot (corrisponde al tuo lane_spacing)
        goal.coverage_server_params.swath_type          = 'length'   # ottimizza lunghezza
        goal.coverage_server_params.route_type          = 'boustrophedon'
        goal.coverage_server_params.robot_width         = self.robot_width
        goal.coverage_server_params.operation_width     = self.robot_width
        goal.coverage_server_params.headland_width      = self.wall_offset
        goal.coverage_server_params.overlap             = 0.05        # 5 cm overlap

        # Controller Nav2 da usare per seguire il path generato
        goal.navigator_params.goal_checker_id           = 'general_goal_checker'
        goal.navigator_params.controller_id             = 'FollowPath'

        send_future = self.coverage_client.send_goal_async(
            goal,
            feedback_callback=lambda fb: self._feedback_callback(fb, room_name)
        )
        send_future.add_done_callback(
            lambda f: self._goal_response_callback(f, room_name)
        )

    # ------------------------------------------------------------------ #
    #  CALLBACK ACTION                                                     #
    # ------------------------------------------------------------------ #

    def _feedback_callback(self, feedback_msg, room_name: str):
        fb = feedback_msg.feedback
        self.get_logger().info(
            f'[{room_name}] copertura: {fb.covered_area_percent:.1f}%  '
            f'distanza percorsa: {fb.distance_traveled:.2f}m',
            throttle_duration_sec=5.0   # stampa max ogni 5s
        )

    def _goal_response_callback(self, future, room_name: str):
        goal_handle = future.result()
        if not goal_handle.accepted:
            self.get_logger().warn(
                f'Goal per [{room_name}] rifiutato da opennav_coverage.'
            )
            self._clean_next()   # prova la stanza successiva
            return

        self.get_logger().info(f'Goal [{room_name}] accettato.')
        result_future = goal_handle.get_result_async()
        result_future.add_done_callback(
            lambda f: self._result_callback(f, room_name)
        )

    def _result_callback(self, future, room_name: str):
        result = future.result().result
        status = future.result().status

        if status == 4:   # SUCCEEDED
            self.get_logger().info(f'✅ [{room_name}] pulita.')
        else:
            self.get_logger().warn(
                f'⚠️  [{room_name}] terminata con status={status}. '
                f'Passo alla prossima stanza.'
            )

        self._clean_next()


# ------------------------------------------------------------------ #
#  MAIN                                                               #
# ------------------------------------------------------------------ #

def main(args=None):
    rclpy.init(args=args)
    node = CleaningController()
    try:
        rclpy.spin(node)
    except KeyboardInterrupt:
        pass
    finally:
        node.destroy_node()
        rclpy.shutdown()


if __name__ == '__main__':
    main()