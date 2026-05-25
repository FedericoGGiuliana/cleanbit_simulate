from __future__ import annotations

import json
from pathlib import Path
from typing import Any

import torch
from torch.utils.data import Dataset

from cleanbit_simulate.nlu.joint.labels import INTENT_TO_ID, SLOT_TO_ID


def read_jsonl(path: Path) -> list[dict[str, Any]]:
    rows = []
    with path.open("r", encoding="utf-8") as jsonl_file:
        for line_number, line in enumerate(jsonl_file, start=1):
            line = line.strip()
            if not line:
                continue
            row = json.loads(line)
            validate_row(row, line_number)
            rows.append(row)
    if not rows:
        raise RuntimeError(f"Dataset vuoto: {path}")
    return rows


def validate_row(row: dict[str, Any], line_number: int) -> None:
    text = row.get("text")
    intent = row.get("intent")
    entities = row.get("entities", [])
    if not isinstance(text, str) or not text:
        raise ValueError(f"Riga {line_number}: text mancante")
    if intent not in INTENT_TO_ID:
        raise ValueError(f"Riga {line_number}: intent non valido {intent!r}")
    spans = []
    for entity in entities:
        start = entity.get("start")
        end = entity.get("end")
        label = entity.get("label")
        if label not in {"TARGET", "AVOID"}:
            raise ValueError(f"Riga {line_number}: label non valida {label!r}")
        if not isinstance(start, int) or not isinstance(end, int) or start < 0 or end > len(text) or start >= end:
            raise ValueError(f"Riga {line_number}: offset non valido {entity!r}")
        if text[start:end] != text[start:end].strip():
            raise ValueError(f"Riga {line_number}: span con spazi extra {text[start:end]!r}")
        if any(start < other_end and end > other_start for other_start, other_end in spans):
            raise ValueError(f"Riga {line_number}: span sovrapposti")
        spans.append((start, end))


class JointNLUDataset(Dataset):
    def __init__(self, rows: list[dict[str, Any]], tokenizer, max_length: int = 32) -> None:
        self.rows = rows
        self.tokenizer = tokenizer
        self.max_length = max_length

    def __len__(self) -> int:
        return len(self.rows)

    def __getitem__(self, index: int) -> dict[str, torch.Tensor]:
        row = self.rows[index]
        encoded = self.tokenizer(
            row["text"],
            truncation=True,
            padding="max_length",
            max_length=self.max_length,
            return_offsets_mapping=True,
        )
        slot_labels = align_slot_labels(encoded["offset_mapping"], row.get("entities", []))

        return {
            "input_ids": torch.tensor(encoded["input_ids"], dtype=torch.long),
            "attention_mask": torch.tensor(encoded["attention_mask"], dtype=torch.long),
            "intent_labels": torch.tensor(INTENT_TO_ID[row["intent"]], dtype=torch.long),
            "slot_labels": torch.tensor(slot_labels, dtype=torch.long),
        }


def align_slot_labels(offsets: list[tuple[int, int]], entities: list[dict[str, Any]]) -> list[int]:
    labels = []
    active_entity_index = None
    for token_start, token_end in offsets:
        if token_start == token_end:
            labels.append(-100)
            active_entity_index = None
            continue

        entity_index = None
        entity_label = None
        for index, entity in enumerate(entities):
            if token_start >= entity["start"] and token_end <= entity["end"]:
                entity_index = index
                entity_label = entity["label"]
                break

        if entity_label is None:
            labels.append(SLOT_TO_ID["O"])
            active_entity_index = None
            continue

        prefix = "I" if entity_index == active_entity_index else "B"
        labels.append(SLOT_TO_ID[f"{prefix}-{entity_label}"])
        active_entity_index = entity_index
    return labels
