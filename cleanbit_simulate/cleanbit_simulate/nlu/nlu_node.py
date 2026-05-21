#!/usr/bin/env python3
from __future__ import annotations

import json

import rclpy
from rclpy.node import Node
from std_msgs.msg import String

from .command_schema import build_command
from .command_validator import CommandValidator
from .context_manager import ContextManager
from .embedding_intent_classifier import EmbeddingIntentClassifier
from .semantic_map_client import SemanticMapClient
from .spacy_slot_extractor import SpacySlotExtractor


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

        semantic_map = SemanticMapClient(logger=self.get_logger())
        self.classifier = EmbeddingIntentClassifier(logger=self.get_logger())
        self.slot_extractor = SpacySlotExtractor(
            semantic_map.get_area_names(),
            logger=self.get_logger(),
        )
        self.validator = CommandValidator()
        self.context_manager = ContextManager()
        self.get_logger().info("Cleanbit NLU in ascolto su /nlu/input_text")

    def input_callback(self, msg: String) -> None:
        text = msg.data
        self.get_logger().info(f"Input NLU: {text}")

        internal_intent, confidence = self.classifier.classify(text)
        slots = self.slot_extractor.extract(text, internal_intent)
        validation = self.validator.validate(text, internal_intent, confidence, slots)
        command = build_command(
            internal_intent=internal_intent,
            confidence=confidence,
            original_text=text,
            slots=slots,
            dialogue=validation["dialogue"],
        )
        self.context_manager.update(command)

        output = json.dumps(command, ensure_ascii=False)
        self.intent_publisher.publish(String(data=output))
        self.get_logger().info(f"Output NLU: {output}")


def main(args=None) -> None:
    rclpy.init(args=args)
    node = NluNode()
    try:
        rclpy.spin(node)
    except KeyboardInterrupt:
        pass
    finally:
        node.destroy_node()
        rclpy.shutdown()


if __name__ == "__main__":
    main()
