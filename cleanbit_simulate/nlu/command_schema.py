from __future__ import annotations

from typing import Any


SCHEMA_SOURCE = "cleanbit_nlu"
SCHEMA_VERSION = "1.0"

INTERNAL_INTENTS = (
    "START_MAPPING",
    "CLEAN_AREA",
    "GO_TO_AREA",
    "RETURN_HOME",
    "STATUS_REQUEST",
    "HELP_REQUEST",
    "CONFIRM",
    "DENY",
    "UNKNOWN",
)

INTENT_TO_ACTION = {
    "START_MAPPING": "map",
    "CLEAN_AREA": "clean",
    "GO_TO_AREA": "navigate",
    "RETURN_HOME": "return_home",
    "STATUS_REQUEST": "status",
    "HELP_REQUEST": "help",
    "CONFIRM": "confirm",
    "DENY": "deny",
    "UNKNOWN": None,
}


def build_command(
    internal_intent: str,
    confidence: float,
    original_text: str,
    slots: dict[str, Any] | None = None,
    requires_clarification: bool = False,
) -> dict[str, Any]:
    slots = slots or {}
    constraints = slots.get("constraints", {})
    confidence = round(float(confidence), 3)

    if requires_clarification or internal_intent == "UNKNOWN":
        return _clarification_command(internal_intent, confidence, original_text)

    return {
        "source": SCHEMA_SOURCE,
        "version": SCHEMA_VERSION,
        "original_text": original_text,
        "intent": {
            "name": internal_intent,
            "confidence": confidence,
            "requires_clarification": False,
        },
        "command": {
            "action": INTENT_TO_ACTION.get(internal_intent),
            "targets": slots.get("targets", []),
            "constraints": {
                "avoid": constraints.get("avoid", []),
                "via": constraints.get("via", []),
            },
        },
        "dialogue": _dialogue_for(internal_intent),
    }


def _clarification_command(
    internal_intent: str,
    confidence: float,
    original_text: str,
) -> dict[str, Any]:
    return {
        "source": SCHEMA_SOURCE,
        "version": SCHEMA_VERSION,
        "original_text": original_text,
        "intent": {
            "name": internal_intent,
            "confidence": confidence,
            "requires_clarification": True,
        },
        "command": {
            "action": None,
            "targets": [],
            "constraints": {
                "avoid": [],
                "via": [],
            },
        },
        "dialogue": {
            "state": "NEEDS_CLARIFICATION",
            "message": "Non ho capito bene il comando.",
            "question": "Puoi riformulare?",
            "expected_replies": [],
        },
    }


def _dialogue_for(internal_intent: str) -> dict[str, Any]:
    if internal_intent == "CONFIRM":
        return {
            "state": "USER_CONFIRMATION",
            "message": "Risposta affermativa ricevuta.",
            "question": None,
            "expected_replies": [],
        }
    if internal_intent == "DENY":
        return {
            "state": "USER_DENIAL",
            "message": "Risposta negativa ricevuta.",
            "question": None,
            "expected_replies": [],
        }
    return {
        "state": "COMMAND_READY",
        "message": "Comando interpretato correttamente.",
        "question": None,
        "expected_replies": [],
    }
