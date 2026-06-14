#!/usr/bin/env python3

from __future__ import annotations

import json
import sys
import threading
from typing import Any

import rclpy
from rclpy.node import Node
from std_msgs.msg import String

from PyQt5.QtCore import Qt, pyqtSignal, QObject
from PyQt5.QtGui import QFont, QColor, QPalette
from PyQt5.QtWidgets import (
    QApplication,
    QFrame,
    QGridLayout,
    QHBoxLayout,
    QLabel,
    QLineEdit,
    QMainWindow,
    QPushButton,
    QSizePolicy,
    QTextEdit,
    QVBoxLayout,
    QWidget,
)


class GuiSignals(QObject):
    nlu_response = pyqtSignal(dict)
    robot_behaviour = pyqtSignal(str)
    error = pyqtSignal(str)


class CleanbitPyQtNode(Node):
    def __init__(self, signals: GuiSignals) -> None:
        super().__init__("cleanbit_pyqt_gui_interface")

        self.signals = signals

        self.input_publisher = self.create_publisher(
            String,
            "/nlu/input_text",
            10,
        )

        self.intent_subscription = self.create_subscription(
            String,
            "/nlp_intent",
            self.intent_callback,
            10,
        )

        self.behaviour_subscription = self.create_subscription(
            String,
            "/current_behaviour",
            self.behaviour_callback,
            10,
        )

        self.get_logger().info(
            "CleanBit PyQt GUI collegata a /nlu/input_text e /nlp_intent"
        )
    def behaviour_callback(self, msg: String) -> None:
        self.signals.robot_behaviour.emit(msg.data)
    def publish_command(self, text: str) -> None:
        msg = String()
        msg.data = text
        self.input_publisher.publish(msg)
        self.get_logger().info(f"Comando inviato alla NLU: {text}")

    def intent_callback(self, msg: String) -> None:
        try:
            data = json.loads(msg.data)
            self.signals.nlu_response.emit(data)
        except json.JSONDecodeError as exc:
            self.signals.error.emit(f"JSON non valido ricevuto: {exc}")


class Card(QFrame):
    def __init__(self, title: str) -> None:
        super().__init__()

        self.setObjectName("card")
        self.setFrameShape(QFrame.StyledPanel)

        self.layout = QVBoxLayout()
        self.layout.setContentsMargins(16, 14, 16, 16)
        self.layout.setSpacing(10)
        self.setLayout(self.layout)

        self.title_label = QLabel(title)
        self.title_label.setObjectName("cardTitle")
        self.layout.addWidget(self.title_label)


class CleanbitPyQtWindow(QMainWindow):
    def __init__(self) -> None:
        super().__init__()

        self.node: CleanbitPyQtNode | None = None
        self.last_sent_command: str | None = None

        self.signals = GuiSignals()
        self.signals.nlu_response.connect(self.update_nlu_response)
        self.signals.robot_behaviour.connect(self.update_robot_behaviour)
        self.signals.error.connect(self.show_error)

        self.setWindowTitle("CleanBit Control Panel")
        self.resize(1200, 780)
        self.setMinimumSize(980, 640)

        self._build_ui()
        self._apply_style()

    def set_node(self, node: CleanbitPyQtNode) -> None:
        self.node = node

    def _build_ui(self) -> None:
        central = QWidget()
        self.setCentralWidget(central)

        root_layout = QVBoxLayout()
        root_layout.setContentsMargins(18, 18, 18, 18)
        root_layout.setSpacing(14)
        central.setLayout(root_layout)

        title = QLabel("CleanBit Control Panel")
        title.setObjectName("mainTitle")
        title.setAlignment(Qt.AlignCenter)
        root_layout.addWidget(title)

        content_layout = QGridLayout()
        content_layout.setSpacing(14)
        content_layout.setColumnStretch(0, 3)
        content_layout.setColumnStretch(1, 2)
        content_layout.setRowStretch(0, 3)
        content_layout.setRowStretch(1, 2)
        root_layout.addLayout(content_layout, stretch=1)

        # Sinistra sopra: risultato NLU
        nlu_card = Card("Risultato NLU")
        self.nlu_card = nlu_card
        content_layout.addWidget(nlu_card, 0, 0)

        self.response_message = QLabel("In attesa di un comando...")
        self.response_message.setObjectName("responseMessage")
        self.response_message.setWordWrap(True)
        nlu_card.layout.addWidget(self.response_message)

        badges_layout = QHBoxLayout()
        badges_layout.setSpacing(8)

        self.intent_badge = QLabel("INTENT: -")
        self.action_badge = QLabel("ACTION: -")

        self._set_badge(self.intent_badge, "INTENT: -", "#64748b")
        self._set_badge(self.action_badge, "ACTION: -", "#64748b")

        badges_layout.addWidget(self.intent_badge)
        badges_layout.addWidget(self.action_badge)
        badges_layout.addStretch()

        nlu_card.layout.addLayout(badges_layout)

        self.confidence_label = QLabel("Confidence: -")
        self.targets_label = QLabel("Targets: -")
        self.avoid_label = QLabel("Avoid: -")

        for label in (
            self.confidence_label,
            self.targets_label,
            self.avoid_label,
        ):
            label.setObjectName("infoLabel")
            label.setWordWrap(True)
            nlu_card.layout.addWidget(label)

        nlu_card.layout.addStretch()

        # Sinistra sotto: stato robot placeholder
        robot_card = Card("Stato robot")
        content_layout.addWidget(robot_card, 1, 0)

        self.robot_status_label = QLabel(
            "Stato robot: non disponibile\nIn attesa del supervisor..."
        )
        self.robot_status_label.setObjectName("robotStatus")
        self.robot_status_label.setWordWrap(True)
        robot_card.layout.addWidget(self.robot_status_label)

        robot_card.layout.addStretch()

        # Destra sopra: JSON
        json_card = Card("JSON")
        content_layout.addWidget(json_card, 0, 1)

        self.json_output = QTextEdit()
        self.json_output.setReadOnly(True)
        self.json_output.setObjectName("jsonBox")
        self.json_output.setFont(QFont("Courier New", 10))
        self.json_output.setPlaceholderText("Qui comparirà il JSON prodotto dall'NLU.")
        json_card.layout.addWidget(self.json_output)

        # Destra sotto: storico
        history_card = Card("Storico comandi")
        content_layout.addWidget(history_card, 1, 1)

        history_header = QHBoxLayout()
        history_header.setSpacing(8)

        clear_history_button = QPushButton("Pulisci storico")
        clear_history_button.setObjectName("secondaryButton")
        clear_history_button.clicked.connect(self.clear_history)

        history_header.addStretch()
        history_header.addWidget(clear_history_button)

        history_card.layout.addLayout(history_header)

        self.history_output = QTextEdit()
        self.history_output.setReadOnly(True)
        self.history_output.setObjectName("historyBox")
        self.history_output.setPlaceholderText("Qui comparirà lo storico dei comandi inviati.")
        history_card.layout.addWidget(self.history_output)

        # Barra input in basso
        bottom_bar = QHBoxLayout()
        bottom_bar.setSpacing(10)
        root_layout.addLayout(bottom_bar)

        self.command_entry = QLineEdit()
        self.command_entry.setObjectName("commandEntry")
        self.command_entry.setPlaceholderText("Scrivi un comando per CleanBit...")
        self.command_entry.returnPressed.connect(self.send_command)
        self.command_entry.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Fixed)
        bottom_bar.addWidget(self.command_entry, stretch=1)

        self.stop_button = QPushButton("Stop")
        self.stop_button.setObjectName("dangerButton")
        self.stop_button.clicked.connect(lambda: self.send_quick_command("stop"))
        bottom_bar.addWidget(self.stop_button)

        self.map_button = QPushButton("Mappa casa")
        self.map_button.setObjectName("primaryButton")
        self.map_button.clicked.connect(lambda: self.send_quick_command("mappa la casa"))
        bottom_bar.addWidget(self.map_button)

        self.return_button = QPushButton("Torna base")
        self.return_button.setObjectName("warningButton")
        self.return_button.clicked.connect(lambda: self.send_quick_command("torna alla base"))
        bottom_bar.addWidget(self.return_button)

        self.help_button = QPushButton("Aiuto")
        self.help_button.setObjectName("secondaryButton")
        self.help_button.clicked.connect(lambda: self.send_quick_command("aiuto"))
        bottom_bar.addWidget(self.help_button)

    def _apply_style(self) -> None:
        self.setStyleSheet(
            """
            QMainWindow {
                background-color: #f4f6f8;
            }

            QLabel#mainTitle {
                font-size: 26px;
                font-weight: 700;
                color: #1f2933;
                padding: 4px;
            }

            QFrame#card {
                background-color: white;
                border: 1px solid #d9e2ec;
                border-radius: 14px;
            }

            QLabel#cardTitle {
                font-size: 15px;
                font-weight: 700;
                color: #243b53;
                padding-bottom: 4px;
            }

            QLabel#responseMessage {
                background-color: #eef5ff;
                border: 1px solid #cfe3ff;
                border-radius: 10px;
                padding: 12px;
                font-size: 14px;
                color: #102a43;
            }

            QLabel#infoLabel {
                font-size: 13px;
                color: #334e68;
                padding: 3px 0;
            }

            QLabel#robotStatus {
                background-color: #f8fafc;
                border: 1px solid #cbd5e1;
                border-radius: 12px;
                padding: 18px;
                font-size: 15px;
                font-weight: 700;
                color: #1e293b;
            }

            QLabel#hintLabel {
                font-size: 12px;
                color: #627d98;
                padding-top: 6px;
            }

            QTextEdit#jsonBox, QTextEdit#historyBox {
                background-color: #f8fafc;
                border: 1px solid #d9e2ec;
                border-radius: 10px;
                padding: 10px;
                font-size: 12px;
                color: #243b53;
            }

            QLineEdit#commandEntry {
                background-color: white;
                border: 2px solid #bcccdc;
                border-radius: 16px;
                padding: 12px 16px;
                font-size: 14px;
                color: #102a43;
            }

            QLineEdit#commandEntry:focus {
                border: 2px solid #3b82f6;
            }

            QPushButton {
                border: none;
                border-radius: 14px;
                padding: 12px 18px;
                font-size: 13px;
                font-weight: 700;
            }

            QPushButton#primaryButton {
                background-color: #2563eb;
                color: white;
            }

            QPushButton#primaryButton:hover {
                background-color: #1d4ed8;
            }

            QPushButton#dangerButton {
                background-color: #dc2626;
                color: white;
            }

            QPushButton#dangerButton:hover {
                background-color: #b91c1c;
            }
            QPushButton#warningButton {
                background-color: #f97316;
                color: white;
            }

            QPushButton#warningButton:hover {
                background-color: #ea580c;
            }

            QPushButton#secondaryButton {
                background-color: #64748b;
                color: white;
            }

            QPushButton#secondaryButton:hover {
                background-color: #475569;
            }
            """
        )
    def _action_color(self, action: str | None) -> tuple[str, str, str]:
        """
        Ritorna:
        - background card
        - bordo card
        - colore badge
        """
        colors = {
            "clean": ("#ecfdf5", "#a7f3d0", "#059669"),
            "map": ("#eff6ff", "#bfdbfe", "#2563eb"),
            "navigate": ("#f5f3ff", "#ddd6fe", "#7c3aed"),
            "return_home": ("#fff7ed", "#fed7aa", "#ea580c"),
            "stop": ("#fef2f2", "#fecaca", "#dc2626"),
            "status": ("#f8fafc", "#cbd5e1", "#475569"),
            "help": ("#fefce8", "#fde68a", "#ca8a04"),
            "confirm": ("#ecfdf5", "#a7f3d0", "#059669"),
            "deny": ("#fef2f2", "#fecaca", "#dc2626"),
            None: ("#fff7ed", "#fed7aa", "#ea580c"),
            "-": ("#f8fafc", "#cbd5e1", "#475569"),
        }

        return colors.get(action, ("#f8fafc", "#cbd5e1", "#475569"))


    def _set_badge(self, label: QLabel, text: str, color: str) -> None:
        label.setText(text)
        label.setStyleSheet(
            f"""
            QLabel {{
                background-color: {color};
                color: white;
                border-radius: 10px;
                padding: 6px 10px;
                font-size: 13px;
                font-weight: 700;
            }}
            """
        )


    def clear_history(self) -> None:
        self.history_output.clear()

    def send_command(self) -> None:
        text = self.command_entry.text().strip()

        if not text:
            self.show_error("Inserisci un comando prima di inviare.")
            return

        if self.node is None:
            self.show_error("Nodo ROS non inizializzato.")
            return

        self.last_sent_command = text
        self.response_message.setText("Comando inviato alla NLU. Attendo risposta...")

        self.node.publish_command(text)

        self.command_entry.clear()
        self.command_entry.setFocus()

    def send_quick_command(self, text: str) -> None:
        self.command_entry.setText(text)
        self.send_command()

    def update_robot_behaviour(self, behaviour: str) -> None:
        behaviour = behaviour.strip() if behaviour else "unknown"

        behaviour_map = {
            "idle": ("IDLE", "Robot in attesa di comandi"),
            "mapping": ("MAPPING", "Mappatura della casa in corso"),
            "map": ("MAPPING", "Mappatura della casa in corso"),
            "navigation": ("NAVIGAZIONE", "Il robot sta raggiungendo una destinazione"),
            "navigating": ("NAVIGAZIONE", "Il robot sta raggiungendo una destinazione"),
            "cleaning": ("PULIZIA", "Pulizia dell'area selezionata in corso"),
            "clean": ("PULIZIA", "Pulizia dell'area selezionata in corso"),
            "return_home": ("RITORNO ALLA BASE", "Il robot sta tornando alla base"),
            "return": ("RITORNO ALLA BASE", "Il robot sta tornando alla base"),
            "stop": ("STOP", "Comando di arresto ricevuto"),
            "stopped": ("FERMO", "Robot fermo"),
            "unknown": ("STATO SCONOSCIUTO", "In attesa di aggiornamenti dal supervisor"),
        }

        title, description = behaviour_map.get(
            behaviour,
            (behaviour.upper(), ""),
        )

        if description:
            self.robot_status_label.setText(f"{title}\n{description}")
        else:
            self.robot_status_label.setText(title)

    def update_nlu_response(self, data: dict[str, Any]) -> None:
        intent = data.get("intent", {})
        command = data.get("command", {})
        dialogue = data.get("dialogue", {})

        intent_name = intent.get("name", "-")
        confidence = intent.get("confidence", "-")
        requires_clarification = intent.get("requires_clarification", False)

        action = command.get("action", "-")
        targets = command.get("targets", [])
        constraints = command.get("constraints", {})
        avoid = constraints.get("avoid", [])

        message = dialogue.get("message", "Risposta ricevuta.")
        question = dialogue.get("question")

        status_text = message
        if question:
            status_text += f"\n{question}"

        if requires_clarification:
            status_text += "\n\n⚠ Il comando richiede chiarimento."

        card_bg, card_border, badge_color = self._action_color(action)

        self.nlu_card.setStyleSheet(
            f"""
            QFrame#card {{
                background-color: {card_bg};
                border: 1px solid {card_border};
                border-radius: 14px;
            }}
            """
        )

        self.response_message.setText(status_text)

        self._set_badge(self.intent_badge, f"INTENT: {intent_name}", badge_color)
        self._set_badge(self.action_badge, f"ACTION: {action}", badge_color)

        self.confidence_label.setText(f"Confidence: {confidence}")
        self.targets_label.setText(f"Targets: {', '.join(targets) if targets else '-'}")
        self.avoid_label.setText(f"Avoid: {', '.join(avoid) if avoid else '-'}")
        pretty_json = json.dumps(data, indent=2, ensure_ascii=False)
        self.json_output.setPlainText(pretty_json)

        self._add_to_history(data)

    def _add_to_history(self, data: dict[str, Any]) -> None:
        intent = data.get("intent", {})
        command = data.get("command", {})
        constraints = command.get("constraints", {})

        text = data.get("original_text") or self.last_sent_command or "-"
        intent_name = intent.get("name", "-")
        action = command.get("action", "-")
        targets = command.get("targets", [])
        avoid = constraints.get("avoid", [])

        target_text = ", ".join(targets) if targets else "-"
        avoid_text = ", ".join(avoid) if avoid else "-"

        row = (
            f"Comando: {text}\n"
            f"↳ Intent: {intent_name} | Action: {action}\n"
            f"↳ Targets: {target_text} | Avoid: {avoid_text}\n"
            f"{'-' * 60}\n"
        )

        current_text = self.history_output.toPlainText()
        self.history_output.setPlainText(row + current_text)

    def show_error(self, message: str) -> None:
        self.response_message.setText(f"Errore: {message}")


def main(args=None) -> None:
    rclpy.init(args=args)

    app = QApplication(sys.argv)

    window = CleanbitPyQtWindow()
    node = CleanbitPyQtNode(window.signals)
    window.set_node(node)

    spin_thread = threading.Thread(
        target=rclpy.spin,
        args=(node,),
        daemon=True,
    )
    spin_thread.start()

    window.show()

    try:
        exit_code = app.exec_()
    finally:
        node.destroy_node()
        if rclpy.ok():
            rclpy.shutdown()
        spin_thread.join(timeout=1.0)

    raise SystemExit(exit_code)


if __name__ == "__main__":
    main()