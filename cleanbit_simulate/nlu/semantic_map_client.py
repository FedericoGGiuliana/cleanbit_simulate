from __future__ import annotations

import json
from pathlib import Path


FALLBACK_AREAS = [
    "cucina",
    "bagno",
    "soggiorno",
    "camera",
    "ingresso",
    "ripostiglio",
    "salone",
    "corridoio",
    "sala da pranzo",
    "zona divano",
    "camera ospiti",
]


class SemanticMapClient:
    def __init__(self, rooms_path: str | None = None, logger=None) -> None:
        self.logger = logger
        self.rooms_path = Path(rooms_path).expanduser() if rooms_path else self._default_rooms_path()
        self._area_names = self._load_area_names()

    def get_area_names(self) -> list[str]:
        return list(self._area_names)

    def _load_area_names(self) -> list[str]:
        try:
            with self.rooms_path.open("r", encoding="utf-8") as rooms_file:
                rooms = json.load(rooms_file)
            names = sorted(
                {
                    str(room.get("name", "")).strip().lower()
                    for room in rooms
                    if room.get("name")
                }
            )
            if names:
                merged = sorted(set(names).union(FALLBACK_AREAS))
                self._info(f"Aree semantiche caricate: {', '.join(merged)}")
                return merged
        except (OSError, json.JSONDecodeError, TypeError) as exc:
            self._warn(f"Uso aree fallback, impossibile leggere rooms.json: {exc}")

        return list(FALLBACK_AREAS)

    def _default_rooms_path(self) -> Path:
        candidates = []
        try:
            from ament_index_python.packages import get_package_share_directory

            candidates.append(
                Path(get_package_share_directory("cleanbit_simulate"))
                / "cleanbit_simulate"
                / "rooms.json"
            )
        except Exception:
            pass

        candidates.extend(
            [
                Path(__file__).resolve().parents[1] / "rooms.json",
                Path("~/cleanbit_ws/src/cleanbit_simulate/cleanbit_simulate/rooms.json").expanduser(),
            ]
        )

        for candidate in candidates:
            if candidate.exists():
                return candidate
        return candidates[-1]

    def _info(self, message: str) -> None:
        if self.logger:
            self.logger.info(message)

    def _warn(self, message: str) -> None:
        if self.logger:
            self.logger.warning(message)
