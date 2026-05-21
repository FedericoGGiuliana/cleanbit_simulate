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
        avoid = self._extract_role_areas(normalized, mentioned, self._avoid_prefixes())
        via = self._extract_role_areas(normalized, mentioned, self._via_prefixes())
        blocked = set(avoid).union(via)

        if internal_intent in {"CLEAN_AREA", "GO_TO_AREA"}:
            targets = [area for area in mentioned if area not in blocked]
        else:
            targets = []

        return {
            "targets": self._unique(targets),
            "constraints": {
                "avoid": self._unique(avoid),
                "via": self._unique(via),
            },
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
            return self._unique([doc[start:end].text.lower() for _, start, end in matches])

        return [
            area
            for area in self.area_names
            if re.search(rf"\b{re.escape(area)}\b", normalized_text)
        ]

    def _extract_role_areas(
        self,
        normalized_text: str,
        mentioned: list[str],
        prefixes: tuple[str, ...],
    ) -> list[str]:
        found = []
        for area in mentioned:
            for prefix in prefixes:
                if re.search(prefix + self._area_pattern(area), normalized_text):
                    found.append(area)
                    break
        return self._unique(found)

    def _avoid_prefixes(self) -> tuple[str, ...]:
        return (
            r"evitando\s+",
            r"evita\s+",
            r"senza\s+passare\s+",
            r"non\s+passare\s+",
            r"non\s+attraversare\s+",
            r"lontano\s+",
            r"escludi\s+",
        )

    def _via_prefixes(self) -> tuple[str, ...]:
        return (
            r"passando\s+",
            r"passa\s+",
            r"passare\s+",
            r"attraverso\s+",
            r"attraversando\s+",
        )

    def _area_pattern(self, area: str) -> str:
        article = r"(?:(?:il|la|lo|l'|l’)\s+)?"
        preposition = r"(?:(?:dal|dalla|dallo|da|per|attraverso)\s+)?"
        return preposition + article + re.escape(area) + r"\b"

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
