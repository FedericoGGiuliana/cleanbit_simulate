#!/usr/bin/env python3

from __future__ import annotations

import json
import threading
import tkinter as tk
from tkinter import ttk, scrolledtext
from typing import Any

import rclpy
from rclpy.node import Node
from std_msgs.msg import String


class CleanbitGuiNode(Node):
    def __init__(self, app: "CleanbitGui") -> None:
        super().__init__("cleanbit_gui_interface")

        self.app = app

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

        self.get_logger().info(
            "Cleanbit GUI collegata a /nlu/input_text e /nlp_intent"
        )

    def publish_command(self, text: str) -> None:
        msg = String()
        msg.data = text
        self.input_publisher.publish(msg)
        self.get_logger().info(f"Comando inviato alla NLU: {text}")

    def intent_callback(self, msg: String) -> None:
        try:
            data = json.loads(msg.data)
            self.app.show_nlu_response(data)
        except json.JSONDecodeError as exc:
            self.app.show_error(f"JSON non valido ricevuto: {exc}")


class CleanbitGui:
    def __init__(self) -> None:
        self.root = tk.Tk()
        self.root.title("CleanBit NLU Interface")
        self.root.geometry("1050x760")
        self.root.minsize(900, 650)

        self.node: CleanbitGuiNode | None = None
        self.last_sent_command: str | None = None

        self._setup_style()
        self._build_layout()

    def set_node(self, node: CleanbitGuiNode) -> None:
        self.node = node

    def _setup_style(self) -> None:
        style = ttk.Style()
        style.theme_use("clam")

        style.configure(
            "Title.TLabel",
            font=("Arial", 22, "bold"),
            padding=8,
        )

        style.configure(
            "Section.TLabelframe.Label",
            font=("Arial", 12, "bold"),
        )

        style.configure(
            "Info.TLabel",
            font=("Arial", 11),
            padding=4,
        )

        style.configure(
            "Status.TLabel",
            font=("Arial", 11, "bold"),
            padding=6,
        )

        style.configure(
            "Send.TButton",
            font=("Arial", 11, "bold"),
            padding=8,
        )

    def _build_layout(self) -> None:
        main_container = ttk.Frame(self.root, padding=16)
        main_container.pack(fill="both", expand=True)

        title = ttk.Label(
            main_container,
            text="CleanBit Control Panel",
            style="Title.TLabel",
        )
        title.pack(anchor="center", pady=(0, 12))

        # Layout principale: zona contenuti sopra + barra comandi sotto
        content_frame = ttk.Frame(main_container)
        content_frame.pack(fill="both", expand=True)

        bottom_frame = ttk.Frame(main_container)
        bottom_frame.pack(fill="x", pady=(12, 0))

        # Colonne principali
        left_column = ttk.Frame(content_frame)
        left_column.pack(side="left", fill="both", expand=True, padx=(0, 8))

        right_column = ttk.Frame(content_frame, width=340)
        right_column.pack(side="right", fill="both", padx=(8, 0))
        right_column.pack_propagate(False)

        # =========================
        # SINISTRA SOPRA: RISULTATO NLU
        # =========================
        response_frame = ttk.LabelFrame(
            left_column,
            text="Risultato NLU",
            padding=12,
            style="Section.TLabelframe",
        )
        response_frame.pack(fill="both", expand=True, pady=(0, 8))

        self.status_label = ttk.Label(
            response_frame,
            text="In attesa di un comando...",
            style="Status.TLabel",
            wraplength=600,
            justify="left",
        )
        self.status_label.pack(fill="x", pady=(0, 12))

        self.intent_label = ttk.Label(response_frame, text="Intent: -", style="Info.TLabel")
        self.intent_label.pack(fill="x")

        self.confidence_label = ttk.Label(response_frame, text="Confidence: -", style="Info.TLabel")
        self.confidence_label.pack(fill="x")

        self.action_label = ttk.Label(response_frame, text="Action: -", style="Info.TLabel")
        self.action_label.pack(fill="x")

        self.targets_label = ttk.Label(response_frame, text="Targets: -", style="Info.TLabel")
        self.targets_label.pack(fill="x")

        self.avoid_label = ttk.Label(response_frame, text="Avoid: -", style="Info.TLabel")
        self.avoid_label.pack(fill="x")

        # =========================
        # SINISTRA SOTTO: STATO / SISTEMA
        # =========================
        robot_state_frame = ttk.LabelFrame(
            left_column,
            text="Stato attuale",
            padding=12,
            style="Section.TLabelframe",
        )
        robot_state_frame.pack(fill="both", expand=True, pady=(8, 0))

        self.robot_status_label = ttk.Label(
            robot_state_frame,
            text="Stato robot: non disponibile\nIn attesa del supervisor...",
            style="Status.TLabel",
            wraplength=600,
            justify="left",
        )
        self.robot_status_label.pack(fill="x", pady=(0, 8))

        # =========================
        # DESTRA SOPRA: JSON
        # =========================
        json_frame = ttk.LabelFrame(
            right_column,
            text="JSON",
            padding=12,
            style="Section.TLabelframe",
        )
        json_frame.pack(fill="both", expand=True, pady=(0, 8))

        self.json_output = scrolledtext.ScrolledText(
            json_frame,
            font=("Courier", 9),
            wrap=tk.WORD,
            height=16,
        )
        self.json_output.pack(fill="both", expand=True)
        self.json_output.configure(state="disabled")

        # =========================
        # DESTRA SOTTO: STORICO
        # =========================
        history_frame = ttk.LabelFrame(
            right_column,
            text="Storico comandi",
            padding=12,
            style="Section.TLabelframe",
        )
        history_frame.pack(fill="both", expand=True, pady=(8, 0))

        self.history_output = scrolledtext.ScrolledText(
            history_frame,
            font=("Arial", 10),
            wrap=tk.WORD,
            height=12,
        )
        self.history_output.pack(fill="both", expand=True)
        self.history_output.configure(state="disabled")

        # =========================
        # BARRA COMANDO IN BASSO
        # =========================
        input_area = ttk.Frame(bottom_frame)
        input_area.pack(side="left", fill="x", expand=True, padx=(0, 10))

        self.command_entry = ttk.Entry(
            input_area,
            font=("Arial", 13),
        )
        self.command_entry.pack(fill="x", ipady=6)

        self.command_entry.bind("<Return>", lambda event: self.send_command())
        self.command_entry.bind("<KP_Enter>", lambda event: self.send_command())
        self.root.bind("<Return>", lambda event: self.send_command())
        self.root.bind("<KP_Enter>", lambda event: self.send_command())

        quick_buttons_frame = ttk.Frame(bottom_frame)
        quick_buttons_frame.pack(side="right")

        stop_button = ttk.Button(
            quick_buttons_frame,
            text="Stop",
            command=lambda: self.send_quick_command("stop"),
        )
        stop_button.pack(side="left", padx=(0, 6))

        map_button = ttk.Button(
            quick_buttons_frame,
            text="Mappa casa",
            command=lambda: self.send_quick_command("mappa la casa"),
        )
        map_button.pack(side="left")

    def send_quick_command(self, text: str) -> None:
        self.command_entry.delete(0, tk.END)
        self.command_entry.insert(0, text)
        self.send_command()

    def send_command(self) -> None:
        text = self.command_entry.get().strip()

        if not text:
            self.show_error("Inserisci un comando prima di inviare.")
            return

        if self.node is None:
            self.show_error("Nodo ROS non inizializzato.")
            return

        self.last_sent_command = text
        self.status_label.config(text="Comando inviato alla NLU. Attendo risposta...")

        self.node.publish_command(text)

        self.command_entry.delete(0, tk.END)
        self.command_entry.focus_set()

    def show_nlu_response(self, data: dict[str, Any]) -> None:
        self.root.after(0, lambda: self._update_response(data))

    def _update_response(self, data: dict[str, Any]) -> None:
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

        self.status_label.config(text=status_text)
        self.intent_label.config(text=f"Intent: {intent_name}")
        self.confidence_label.config(text=f"Confidence: {confidence}")
        self.action_label.config(text=f"Action: {action}")
        self.targets_label.config(text=f"Targets: {', '.join(targets) if targets else '-'}")
        self.avoid_label.config(text=f"Avoid: {', '.join(avoid) if avoid else '-'}")

        self._update_json(data)
        self._add_to_history(data)

    def _update_json(self, data: dict[str, Any]) -> None:
        pretty_json = json.dumps(data, indent=2, ensure_ascii=False)

        self.json_output.configure(state="normal")
        self.json_output.delete("1.0", tk.END)
        self.json_output.insert(tk.END, pretty_json)
        self.json_output.configure(state="disabled")

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
            f"{'-' * 70}\n"
        )

        self.history_output.configure(state="normal")
        self.history_output.insert("1.0", row)
        self.history_output.configure(state="disabled")

    def show_error(self, message: str) -> None:
        self.root.after(0, lambda: self._show_error(message))

    def _show_error(self, message: str) -> None:
        self.status_label.config(text=f"Errore: {message}")

    def run(self) -> None:
        self.command_entry.focus_set()
        self.root.mainloop()


def main(args=None) -> None:
    rclpy.init(args=args)

    app = CleanbitGui()
    node = CleanbitGuiNode(app)
    app.set_node(node)

    spin_thread = threading.Thread(
        target=rclpy.spin,
        args=(node,),
        daemon=True,
    )
    spin_thread.start()

    try:
        app.run()
    finally:
        node.destroy_node()
        if rclpy.ok():
            rclpy.shutdown()
        spin_thread.join(timeout=1.0)


if __name__ == "__main__":
    main()