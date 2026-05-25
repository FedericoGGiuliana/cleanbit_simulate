from __future__ import annotations

import re
from pathlib import Path
from typing import Any

import torch

from cleanbit_simulate.nlu.command_schema import build_command
from cleanbit_simulate.nlu.joint.joint_nlu_model import BERTINO_MODEL_NAME, JointNLUModel
from cleanbit_simulate.nlu.joint.labels import ID_TO_INTENT, ID_TO_SLOT, INTENT_LABELS, INTENT_TO_ACTION, SLOT_LABELS


class JointNLUInference:
    def __init__(self, model_path: str | None = None, max_length: int = 32, logger=None) -> None:
        self.logger = logger
        self.model_path = Path(model_path).expanduser() if model_path else self._default_model_path()
        self.max_length = max_length
        self.available = False
        self.tokenizer = None
        self.model = None
        self.device = torch.device("cuda" if torch.cuda.is_available() else "cpu")
        self._load()

    def parse(self, text: str) -> dict[str, Any]:
        if not self.available or self.model is None or self.tokenizer is None:
            raise RuntimeError("Joint NLU non disponibile")

        encoded = self.tokenizer(
            text,
            truncation=True,
            padding="max_length",
            max_length=self.max_length,
            return_offsets_mapping=True,
            return_tensors="pt",
        )
        offsets = encoded.pop("offset_mapping")[0].tolist()
        encoded = {key: value.to(self.device) for key, value in encoded.items()}

        self.model.eval()
        with torch.no_grad():
            outputs = self.model(**encoded)
            intent_probs = torch.softmax(outputs["intent_logits"][0], dim=-1)
            intent_id = int(torch.argmax(intent_probs).item())
            confidence = float(intent_probs[intent_id].item())
            slot_probs = torch.softmax(outputs["slot_logits"][0], dim=-1).cpu()
            slot_ids = torch.argmax(slot_probs, dim=-1).tolist()

        intent = ID_TO_INTENT[intent_id]
        targets, avoid = self._decode_slots(text, offsets, slot_ids)
        if intent in {"CLEAN_AREA", "GO_TO_AREA"} and not targets:
            targets = self._recover_missing_target(text, offsets, slot_probs)
        requires_clarification = self._requires_clarification(intent, targets)
        action = None if requires_clarification else INTENT_TO_ACTION[intent]
        slots = {
            "targets": targets,
            "constraints": {
                "avoid": avoid,
            },
        }
        command_json = build_command(
            internal_intent=intent,
            confidence=confidence,
            original_text=text,
            slots=slots,
            requires_clarification=requires_clarification,
        )

        return {
            "intent": intent,
            "confidence": round(confidence, 3),
            "action": action,
            "targets": [] if requires_clarification else targets,
            "avoid": [] if requires_clarification else avoid,
            "requires_clarification": requires_clarification,
            "json": command_json,
        }

    def _load(self) -> None:
        model_file = self.model_path / "joint_nlu_model.pt"
        labels_file = self.model_path / "labels.json"
        if not model_file.exists() or not labels_file.exists():
            self._info(f"Joint NLU BERTino non trovato in {self.model_path}")
            return

        try:
            from transformers import AutoTokenizer
        except ImportError as exc:
            self._warn(f"transformers non disponibile, Joint NLU disabilitato: {exc}")
            return

        try:
            checkpoint = torch.load(model_file, map_location=self.device)
            self.tokenizer = AutoTokenizer.from_pretrained(self.model_path, use_fast=True)
            self.max_length = int(checkpoint.get("max_length", self.max_length))
            encoder_path = self.model_path / "encoder"
            self.model = JointNLUModel(
                len(INTENT_LABELS),
                len(SLOT_LABELS),
                model_name=str(encoder_path) if encoder_path.exists() else BERTINO_MODEL_NAME,
            )
            self.model.load_state_dict(checkpoint["model_state_dict"])
            self.model.to(self.device)
        except Exception as exc:
            self._warn(f"Impossibile caricare Joint NLU BERTino: {exc}")
            return

        self.available = True
        self._info(f"Joint NLU BERTino caricato da {self.model_path}")

    def _decode_slots(self, text: str, offsets: list[list[int]], slot_ids: list[int]) -> tuple[list[str], list[str]]:
        spans = []
        active_label = None
        active_start = None
        active_end = None

        for offset, slot_id in zip(offsets, slot_ids):
            token_start, token_end = offset
            if token_start == token_end:
                continue

            label = ID_TO_SLOT.get(int(slot_id), "O")
            if label == "O":
                if active_label is not None:
                    spans.append((active_start, active_end, active_label))
                active_label = None
                active_start = None
                active_end = None
                continue

            prefix, entity_label = label.split("-", 1)
            if prefix == "B" or active_label != entity_label:
                if active_label is not None:
                    spans.append((active_start, active_end, active_label))
                active_label = entity_label
                active_start = token_start
                active_end = token_end
            else:
                active_end = token_end

        if active_label is not None:
            spans.append((active_start, active_end, active_label))

        targets = []
        avoid = []
        for start, end, label in spans:
            start, end = self._expand_to_word_boundaries(text, start, end)
            value = self._normalize_span(text[start:end])
            if not value:
                continue
            if label == "TARGET":
                targets.append(value)
            elif label == "AVOID":
                avoid.append(value)

        avoid = self._unique(avoid)
        avoid_set = set(avoid)
        targets = self._unique([target for target in targets if target not in avoid_set])
        return targets, avoid

    def _recover_missing_target(
        self,
        text: str,
        offsets: list[list[int]],
        slot_probs: torch.Tensor,
        threshold: float = 0.2,
    ) -> list[str]:
        target_ids = [1, 2]
        best_index = None
        best_score = 0.0
        for index, (start, end) in enumerate(offsets):
            if start == end:
                continue
            score = float(slot_probs[index, target_ids].max().item())
            if score > best_score:
                best_score = score
                best_index = index

        if best_index is None or best_score < threshold:
            return []

        start, end = offsets[best_index]
        start, end = self._expand_to_word_boundaries(text, start, end)
        value = self._normalize_span(text[start:end])
        return [value] if value else []

    def _expand_to_word_boundaries(self, text: str, start: int, end: int) -> tuple[int, int]:
        while start > 0 and self._is_entity_char(text[start - 1]):
            start -= 1
        while end < len(text) and self._is_entity_char(text[end]):
            end += 1
        return start, end

    def _is_entity_char(self, value: str) -> bool:
        return not value.isspace() and value not in {",", ".", ";", ":", "!", "?"}

    def _requires_clarification(self, intent: str, targets: list[str]) -> bool:
        if intent == "UNKNOWN":
            return True
        if intent in {"CLEAN_AREA", "GO_TO_AREA"} and not targets:
            return True
        return False

    def _normalize_span(self, value: str) -> str:
        normalized = re.sub(r"\s+", " ", value).strip().lower()
        return normalized

    def _unique(self, values: list[str]) -> list[str]:
        seen = set()
        result = []
        for value in values:
            if value not in seen:
                seen.add(value)
                result.append(value)
        return result

    def _default_model_path(self) -> Path:
        candidates = []
        try:
            from ament_index_python.packages import get_package_share_directory

            candidates.append(Path(get_package_share_directory("cleanbit_simulate")) / "models" / "joint_nlu_bertino")
        except Exception:
            pass
        candidates.extend(
            [
                Path(__file__).resolve().parents[3] / "models" / "joint_nlu_bertino",
                Path("~/cleanbit_ws/src/cleanbit_simulate/models/joint_nlu_bertino").expanduser(),
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
