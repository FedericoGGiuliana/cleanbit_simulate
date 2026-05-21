from __future__ import annotations

from pathlib import Path
from typing import Any


class SupervisedSlotExtractor:
    def __init__(self, model_path: str | None = None, logger=None) -> None:
        self.logger = logger
        self.model_path = Path(model_path).expanduser() if model_path else self._default_model_path()
        self.nlp = None
        self.available = False
        self._load_model()

    def extract(self, text: str, internal_intent: str, area_names: list[str]) -> dict[str, Any]:
        if not self.available or self.nlp is None:
            return self._empty_slots()

        area_lookup = self._area_lookup(area_names)
        doc = self.nlp(text)
        targets: list[str] = []
        avoid: list[str] = []
        via: list[str] = []

        for ent in doc.ents:
            area = self._normalize_area(ent.text, area_lookup)
            if area is None:
                continue
            if ent.label_ == "TARGET":
                targets.append(area)
            elif ent.label_ == "AVOID":
                avoid.append(area)
            elif ent.label_ == "VIA":
                via.append(area)

        return {
            "targets": self._unique(targets),
            "constraints": {
                "avoid": self._unique(avoid),
                "via": self._unique(via),
            },
        }

    def has_slots(self, slots: dict[str, Any]) -> bool:
        constraints = slots.get("constraints", {})
        return bool(
            slots.get("targets")
            or constraints.get("avoid")
            or constraints.get("via")
        )

    def _load_model(self) -> None:
        if not self.model_path.exists():
            self._info(f"Slot filler supervisionato non trovato in {self.model_path}")
            return

        try:
            import spacy
        except ImportError as exc:
            self._warn(f"spaCy non disponibile, slot filler supervisionato disabilitato: {exc}")
            return

        try:
            self.nlp = spacy.load(self.model_path)
        except OSError as exc:
            self._warn(f"Impossibile caricare slot filler supervisionato: {exc}")
            return

        self.available = True
        self._info(f"Slot filler supervisionato caricato da {self.model_path}")

    def _default_model_path(self) -> Path:
        candidates = []
        try:
            from ament_index_python.packages import get_package_share_directory

            candidates.append(
                Path(get_package_share_directory("cleanbit_simulate"))
                / "models"
                / "slot_filler_spacy"
            )
        except Exception:
            pass

        candidates.extend(
            [
                Path(__file__).resolve().parents[3] / "models" / "slot_filler_spacy",
                Path("~/cleanbit_ws/src/cleanbit_simulate/models/slot_filler_spacy").expanduser(),
            ]
        )

        for candidate in candidates:
            if candidate.exists():
                return candidate
        return candidates[-1]

    def _area_lookup(self, area_names: list[str]) -> dict[str, str]:
        return {area.strip().lower(): area.strip().lower() for area in area_names if area.strip()}

    def _normalize_area(self, value: str, area_lookup: dict[str, str]) -> str | None:
        normalized = value.strip().lower()
        for prefix in (
            "dalla ",
            "dallo ",
            "dal ",
            "alla ",
            "allo ",
            "all'",
            "all’",
            "al ",
            "nella ",
            "nello ",
            "nel ",
            "la ",
            "lo ",
            "il ",
            "l'",
            "l’",
            "per ",
            "da ",
        ):
            if normalized.startswith(prefix):
                normalized = normalized[len(prefix):]
                break
        return area_lookup.get(normalized)

    def _empty_slots(self) -> dict[str, Any]:
        return {
            "targets": [],
            "constraints": {
                "avoid": [],
                "via": [],
            },
        }

    def _unique(self, values: list[str]) -> list[str]:
        seen = set()
        result = []
        for value in values:
            if value not in seen:
                seen.add(value)
                result.append(value)
        return result

    def _info(self, message: str) -> None:
        if self.logger:
            self.logger.info(message)

    def _warn(self, message: str) -> None:
        if self.logger:
            self.logger.warning(message)

