#!/usr/bin/env python3
from __future__ import annotations

import json

import rclpy
from rclpy.node import Node
from std_msgs.msg import String

from cleanbit_simulate.nlu.command_schema import build_command
from cleanbit_simulate.nlu.command_validator import CommandValidator
from cleanbit_simulate.nlu.joint.inference import JointNLUInference


class NluNode(Node):
    def __init__(self) -> None:
        super().__init__("cleanbit_nlu_node")
        self.intent_publisher = self.create_publisher(String, "/nlp_intent", 10)
        self.input_subscription = self.create_subscription(
            String,
            "/nlu/input_text",
            self.input_callback,
            10,
        )

        self.joint_nlu = JointNLUInference(logger=self.get_logger())
        if not self.joint_nlu.available:
            raise RuntimeError("Joint NLU BERTino non disponibile: impossibile avviare nlu_node")

        self.validator = CommandValidator()
        self.get_logger().info("Cleanbit NLU in ascolto su /nlu/input_text")

    def input_callback(self, msg: String) -> None:
        text = msg.data
        self.get_logger().info(f"Input NLU: {text}")

        parsed = self.joint_nlu.parse(text)
        internal_intent = parsed["intent"]
        confidence = parsed["confidence"]
        slots = {
            "targets": parsed["targets"],
            "constraints": {
                "avoid": parsed["avoid"],
            },
        }
        validation = self.validator.validate(text, internal_intent, confidence, slots)
        command = build_command(
            internal_intent=internal_intent,
            confidence=confidence,
            original_text=text,
            slots=slots,
            requires_clarification=not validation["valid"],
        )

        output = json.dumps(command, ensure_ascii=False)
        self.intent_publisher.publish(String(data=output))
        self.get_logger().info(f"Output NLU joint: {output}")


def main(args=None) -> None:
    rclpy.init(args=args)
    node = NluNode()
    try:
        rclpy.spin(node)
    except KeyboardInterrupt:
        pass
    finally:
        node.destroy_node()
        if rclpy.ok():
            rclpy.shutdown()


if __name__ == "__main__":
    main()
