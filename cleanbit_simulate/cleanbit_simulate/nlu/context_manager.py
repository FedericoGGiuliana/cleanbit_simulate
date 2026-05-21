from __future__ import annotations

from typing import Any


class ContextManager:
    """Keeps lightweight NLU context for future dialogue turns."""

    def __init__(self) -> None:
        self.last_command: dict[str, Any] | None = None
        self.active_task: dict[str, Any] | None = None

    def update(self, command: dict[str, Any]) -> None:
        self.last_command = command
        if command.get("internal_intent") in {
            "START_MAPPING",
            "CLEAN_AREA",
            "GO_TO_AREA",
            "RETURN_HOME",
        }:
            self.active_task = command.get("task")

    def get_last_command(self) -> dict[str, Any] | None:
        return self.last_command

    def get_active_task(self) -> dict[str, Any] | None:
        return self.active_task

