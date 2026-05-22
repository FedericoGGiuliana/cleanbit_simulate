from __future__ import annotations

import re
from pathlib import Path
from typing import Any


AVOID_MARKERS = (
    "evita",
    "evitando",
    "non passare",
    "senza passare",
    "non andare",
    "non entrare",
    "senza entrare",
    "tranne",
    "escluso",
    "esclusi",
    "esclusa",
    "a parte",
    "non",
    "né",
    "manco",
)

TARGET_VERBS = (
    "pulisci",
    "spolvera",
    "sistema",
    "ripulisci",
    "vai",
    "raggiungi",
    "spostati",
    "portati",
)


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
        entities = []

        for ent in doc.ents:
            area = self._normalize_area(ent.text, area_lookup)
            if area is None:
                continue
            if ent.label_ in {"TARGET", "AVOID"}:
                entities.append((ent.start_char, ent.end_char, ent.label_, area))
        entities.extend(self._extract_explicit_avoid_list(text, area_lookup))

        targets: list[str] = []
        avoid: list[str] = []
        for _, _, label, area in self._prefer_longest_entities(entities):
            if label == "TARGET":
                targets.append(area)
            elif label == "AVOID":
                avoid.append(area)

        if not self._has_avoid_marker(text):
            targets.extend(avoid)
            avoid = []

        avoid_set = set(avoid)

        return {
            "targets": self._unique([area for area in targets if area not in avoid_set]),
            "constraints": {
                "avoid": self._unique(avoid),
            },
        }

    def has_slots(self, slots: dict[str, Any]) -> bool:
        constraints = slots.get("constraints", {})
        return bool(
            slots.get("targets")
            or constraints.get("avoid")
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

    def _extract_explicit_avoid_list(
        self,
        text: str,
        area_lookup: dict[str, str],
    ) -> list[tuple[int, int, str, str]]:
        text_lower = text.lower()
        area_spans = self._known_area_spans(text_lower, area_lookup)
        avoid_entities = []

        for marker in AVOID_MARKERS:
            for marker_match in re.finditer(rf"(?<!\w){re.escape(marker)}(?!\w)", text_lower):
                start = marker_match.end()
                end = self._next_target_verb_start(text_lower, start)
                for area_start, area_end, area in area_spans:
                    if start <= area_start < end:
                        avoid_entities.append((area_start, area_end, "AVOID", area))

        return self._prefer_longest_entities(avoid_entities)

    def _has_avoid_marker(self, text: str) -> bool:
        text_lower = text.lower()
        return any(
            re.search(rf"(?<!\w){re.escape(marker)}(?!\w)", text_lower)
            for marker in AVOID_MARKERS
        )

    def _known_area_spans(
        self,
        text_lower: str,
        area_lookup: dict[str, str],
    ) -> list[tuple[int, int, str]]:
        spans = []
        for area in sorted(area_lookup, key=len, reverse=True):
            for match in re.finditer(rf"(?<!\w){re.escape(area)}(?!\w)", text_lower):
                spans.append((match.start(), match.end(), area_lookup[area]))

        selected = []
        occupied: list[tuple[int, int]] = []
        for start, end, area in sorted(spans, key=lambda item: (item[1] - item[0], -item[0]), reverse=True):
            if any(start < used_end and end > used_start for used_start, used_end in occupied):
                continue
            selected.append((start, end, area))
            occupied.append((start, end))
        return sorted(selected, key=lambda item: item[0])

    def _next_target_verb_start(self, text_lower: str, start: int) -> int:
        next_start = len(text_lower)
        for verb in TARGET_VERBS:
            match = re.search(rf"(?<!\w){re.escape(verb)}(?!\w)", text_lower[start:])
            if match:
                next_start = min(next_start, start + match.start())
        return next_start

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
            "in ",
        ):
            if normalized.startswith(prefix):
                normalized = normalized[len(prefix):]
                break
        return area_lookup.get(normalized)

    def _prefer_longest_entities(
        self,
        entities: list[tuple[int, int, str, str]],
    ) -> list[tuple[int, int, str, str]]:
        selected: list[tuple[int, int, str, str]] = []
        occupied: list[tuple[int, int]] = []
        for entity in sorted(
            entities,
            key=lambda item: (item[1] - item[0], item[2] == "AVOID", -item[0]),
            reverse=True,
        ):
            start, end, _, _ = entity
            if any(start < used_end and end > used_start for used_start, used_end in occupied):
                continue
            selected.append(entity)
            occupied.append((start, end))
        return sorted(selected, key=lambda item: item[0])

    def _empty_slots(self) -> dict[str, Any]:
        return {
            "targets": [],
            "constraints": {
                "avoid": [],
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
