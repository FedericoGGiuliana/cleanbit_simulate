from __future__ import annotations

from typing import Any


INTERNAL_INTENTS = (
    "START_MAPPING",
    "CLEAN_AREA",
    "GO_TO_AREA",
    "RETURN_HOME",
    "PAUSE_TASK",
    "RESUME_TASK",
    "STOP_TASK",
    "MODIFY_TASK",
    "QUERY_AREA",
    "STATUS_REQUEST",
    "HELP_REQUEST",
    "UNKNOWN",
)

INTENT_TO_ACTION = {
    "START_MAPPING": "map",
    "CLEAN_AREA": "clean",
    "GO_TO_AREA": "navigate",
    "RETURN_HOME": "return_home",
    "PAUSE_TASK": "pause",
    "RESUME_TASK": "resume",
    "STOP_TASK": "stop",
    "MODIFY_TASK": "modify_active_task",
    "QUERY_AREA": "query_area",
    "STATUS_REQUEST": "status_request",
    "HELP_REQUEST": "help_request",
    "UNKNOWN": "unknown",
}

SUPERVISOR_INTENT_ALIASES = {
    "START_MAPPING": "explore",
}


def external_intent_for(internal_intent: str) -> str:
    return SUPERVISOR_INTENT_ALIASES.get(internal_intent, internal_intent)


def empty_dialogue() -> dict[str, Any]:
    return {
        "requires_clarification": False,
        "clarification_type": None,
        "clarification_question": None,
    }


def build_command(
    internal_intent: str,
    confidence: float,
    original_text: str,
    slots: dict[str, Any] | None = None,
    dialogue: dict[str, Any] | None = None,
) -> dict[str, Any]:
    slots = slots or {}
    constraints = slots.get("constraints", {})
    action = INTENT_TO_ACTION.get(internal_intent, "unknown")

    return {
        "intent": external_intent_for(internal_intent),
        "internal_intent": internal_intent,
        "confidence": round(float(confidence), 3),
        "original_text": original_text,
        "task": {
            "action": action,
            "targets": slots.get("targets", []),
            "constraints": {
                "avoid": constraints.get("avoid", []),
                "via": constraints.get("via", []),
            },
            "operation": slots.get("operation"),
        },
        "dialogue": dialogue or empty_dialogue(),
    }

