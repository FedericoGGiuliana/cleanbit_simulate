#!/usr/bin/env python3
from __future__ import annotations

import json
import threading
from typing import Any

import rclpy
from rclpy.node import Node
from std_msgs.msg import String


EXIT_COMMANDS = {"exit", "quit", "esci"}


class NluTerminalInterface(Node):
    def __init__(self) -> None:
        super().__init__("cleanbit_nlu_terminal")
        self.input_publisher = self.create_publisher(String, "/nlu/input_text", 10)
        self.intent_subscription = self.create_subscription(
            String,
            "/nlp_intent",
            self.intent_callback,
            10,
        )
        self._condition = threading.Condition()
        self._last_response: dict[str, Any] | None = None
        self._last_error: str | None = None

    def publish_text(self, text: str) -> None:
        with self._condition:
            self._last_response = None
            self._last_error = None
        self.input_publisher.publish(String(data=text))

    def wait_for_response(self, timeout_sec: float = 10.0) -> tuple[dict[str, Any] | None, str | None]:
        with self._condition:
            self._condition.wait_for(
                lambda: self._last_response is not None or self._last_error is not None,
                timeout=timeout_sec,
            )
            return self._last_response, self._last_error

    def intent_callback(self, msg: String) -> None:
        try:
            response = json.loads(msg.data)
            error = None
        except json.JSONDecodeError as exc:
            response = None
            error = f"JSON non valido ricevuto su /nlp_intent: {exc}"

        with self._condition:
            self._last_response = response
            self._last_error = error
            self._condition.notify_all()


def print_response(response: dict[str, Any]) -> None:
    dialogue = response.get("dialogue", {})
    message = dialogue.get("message") or "Risposta ricevuta."
    question = dialogue.get("question")

    print("\nRobot:")
    print(f"  {message}")
    if question:
        print(f"  {question}")

    print("\nJSON pubblicato:")
    print(json.dumps(response, indent=2, ensure_ascii=False))


def run_terminal(node: NluTerminalInterface) -> None:
    print("Cleanbit NLU terminal")
    print("Scrivi un comando, oppure exit/quit/esci per uscire.")

    while rclpy.ok():
        try:
            text = input("\nTu > ").strip()
        except EOFError:
            break
        except KeyboardInterrupt:
            print()
            break

        if text.lower() in EXIT_COMMANDS:
            break
        if not text:
            continue

        node.publish_text(text)
        response, error = node.wait_for_response()
        if error:
            print("\nRobot: " + error)
        elif response:
            print_response(response)
        else:
            print("\nRobot: nessuna risposta ricevuta. Verifica che nlu_node sia in esecuzione.")


def main(args=None) -> None:
    rclpy.init(args=args)
    node = NluTerminalInterface()
    spin_thread = threading.Thread(target=rclpy.spin, args=(node,), daemon=True)
    spin_thread.start()

    try:
        run_terminal(node)
    finally:
        node.destroy_node()
        if rclpy.ok():
            rclpy.shutdown()
        spin_thread.join(timeout=1.0)


if __name__ == "__main__":
    main()
