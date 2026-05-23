from __future__ import annotations

import re
from typing import Any


class SpacySlotExtractor:
    def __init__(self, area_names: list[str], logger=None) -> None:
        self.logger = logger
        self.area_names = sorted({area.lower() for area in area_names}, key=len, reverse=True)
        self.nlp = None
        self.area_matcher = None
        self._load_spacy()

    def extract(self, text: str, internal_intent: str) -> dict[str, Any]:
        normalized = text.lower()
        mentioned = self._extract_area_mentions(normalized)
        avoid = self._areas_near_patterns(
            normalized,
            mentioned,
            (
                r"evita(?:ndo)?\s+(?:il |la |lo |l')?",
                r"non\s+passare\s+da(?:l|lla|llo)?\s+",
                r"non\s+attraversare\s+(?:il |la |lo |l')?",
            ),
        )
        via = self._areas_near_patterns(
            normalized,
            mentioned,
            (
                r"passando\s+da(?:l|lla|llo)?\s+",
                r"attraverso\s+(?:il |la |lo |l')?",
            ),
        )
        operation = self._extract_operation(normalized)

        if operation == "ADD_AVOID_AREA":
            avoid = sorted(set(avoid).union(mentioned))
            targets: list[str] = []
        elif operation == "REMOVE_AVOID_AREA":
            avoid = mentioned
            targets = []
        elif operation in {"ADD_TARGET_AREA", "REMOVE_TARGET_AREA"}:
            targets = mentioned
        elif internal_intent in {"CLEAN_AREA", "GO_TO_AREA", "QUERY_AREA", "MODIFY_TASK"}:
            targets = [area for area in mentioned if area not in set(avoid).union(via)]
        else:
            targets = []

        return {
            "targets": self._unique(targets),
            "constraints": {
                "avoid": self._unique(avoid),
                "via": self._unique(via),
            },
            "operation": operation,
        }

    def _load_spacy(self) -> None:
        try:
            import spacy
            from spacy.matcher import PhraseMatcher
        except ImportError as exc:
            self._warn(f"spaCy non disponibile, uso fallback slot: {exc}")
            return

        try:
            self.nlp = spacy.load("it_core_news_sm")
        except OSError:
            self._warn("Modello spaCy it_core_news_sm non disponibile, uso spacy.blank('it')")
            self.nlp = spacy.blank("it")

        self.area_matcher = PhraseMatcher(self.nlp.vocab, attr="LOWER")
        patterns = [self.nlp.make_doc(area) for area in self.area_names]
        self.area_matcher.add("AREA", patterns)

    def _extract_area_mentions(self, normalized_text: str) -> list[str]:
        if self.nlp is not None and self.area_matcher is not None:
            doc = self.nlp(normalized_text)
            matches = self.area_matcher(doc)
            areas = [doc[start:end].text.lower() for _, start, end in matches]
            return self._unique(areas)

        areas = []
        for area in self.area_names:
            if re.search(rf"\b{re.escape(area)}\b", normalized_text):
                areas.append(area)
        return self._unique(areas)

    def _areas_near_patterns(
        self,
        normalized_text: str,
        mentioned: list[str],
        prefixes: tuple[str, ...],
    ) -> list[str]:
        found = []
        for area in mentioned:
            for prefix in prefixes:
                if re.search(prefix + re.escape(area) + r"\b", normalized_text):
                    found.append(area)
        return self._unique(found)

    def _extract_operation(self, normalized_text: str) -> str | None:
        if re.search(r"\bpulisci\s+anche\b|\baggiungi\b", normalized_text):
            return "ADD_TARGET_AREA"
        if re.search(r"\bevita\s+anche\b", normalized_text):
            return "ADD_AVOID_AREA"
        if re.search(r"\brimuovi\b.*\b(?:evitare|evita|aree da evitare)\b", normalized_text):
            return "REMOVE_AVOID_AREA"
        if re.search(r"\bnon\s+evitare\s+pi[uù]\b", normalized_text):
            return "REMOVE_AVOID_AREA"
        if re.search(r"\btogli\b|\brimuovi\b", normalized_text):
            return "REMOVE_TARGET_AREA"
        return None

    def _unique(self, values: list[str]) -> list[str]:
        seen = set()
        result = []
        for value in values:
            if value not in seen:
                seen.add(value)
                result.append(value)
        return result

    def _warn(self, message: str) -> None:
        if self.logger:
            self.logger.warning(message)
