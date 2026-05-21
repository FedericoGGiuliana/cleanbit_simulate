from __future__ import annotations

from typing import Any


VALIDATION_MESSAGES = {
    "EMPTY_TEXT": "Non ho ricevuto nessun comando.",
    "LOW_CONFIDENCE": "Non ho capito bene il comando. Puoi riformularlo?",
    "UNKNOWN_INTENT": "Non ho capito cosa vuoi che faccia.",
    "MISSING_TARGET_AREA": "Quale area vuoi indicare?",
    "TARGET_EQUALS_AVOID": "Hai indicato la stessa area sia come destinazione sia come area da evitare.",
}


class CommandValidator:
    def __init__(self, confidence_threshold: float = 0.45) -> None:
        self.confidence_threshold = confidence_threshold

    def validate(
        self,
        text: str,
        internal_intent: str,
        confidence: float,
        slots: dict[str, Any],
    ) -> dict[str, Any]:
        code = self._validation_code(text, internal_intent, confidence, slots)
        if code is None:
            return {
                "valid": True,
                "code": None,
                "dialogue": {
                    "requires_clarification": False,
                    "clarification_type": None,
                    "clarification_question": None,
                },
            }

        return {
            "valid": False,
            "code": code,
            "dialogue": {
                "requires_clarification": True,
                "clarification_type": code,
                "clarification_question": VALIDATION_MESSAGES[code],
            },
        }

    def _validation_code(
        self,
        text: str,
        internal_intent: str,
        confidence: float,
        slots: dict[str, Any],
    ) -> str | None:
        if not text.strip():
            return "EMPTY_TEXT"
        if confidence < self.confidence_threshold:
            return "LOW_CONFIDENCE"
        if internal_intent == "UNKNOWN":
            return "UNKNOWN_INTENT"

        targets = set(slots.get("targets", []))
        avoid = set(slots.get("constraints", {}).get("avoid", []))

        if targets.intersection(avoid):
            return "TARGET_EQUALS_AVOID"
        if internal_intent in {"CLEAN_AREA", "GO_TO_AREA"} and not targets and avoid:
            return "TARGET_EQUALS_AVOID"
        if internal_intent in {"CLEAN_AREA", "GO_TO_AREA"} and not targets:
            return "MISSING_TARGET_AREA"
        return None
