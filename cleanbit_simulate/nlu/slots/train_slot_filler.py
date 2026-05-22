#!/usr/bin/env python3
from __future__ import annotations

import argparse
import json
import random
from pathlib import Path

import spacy
from spacy.training import Example
from spacy.util import minibatch


LABELS = ("TARGET", "AVOID")


def package_root() -> Path:
    return Path(__file__).resolve().parents[3]


def load_dataset(dataset_path: Path) -> list[tuple[str, dict]]:
    examples = []
    with dataset_path.open("r", encoding="utf-8") as dataset_file:
        for line_number, line in enumerate(dataset_file, start=1):
            line = line.strip()
            if not line:
                continue
            row = json.loads(line)
            validate_row(row, line_number)
            examples.append((row["text"], {"entities": row["entities"]}))
    if not examples:
        raise RuntimeError(f"Dataset vuoto: {dataset_path}")
    return examples


def validate_row(row: dict, line_number: int) -> None:
    text = row.get("text", "")
    entities = row.get("entities", [])
    if not isinstance(text, str) or not text:
        raise ValueError(f"Riga {line_number}: campo text mancante o vuoto")
    spans: list[tuple[int, int]] = []
    for entity in entities:
        if len(entity) != 3:
            raise ValueError(f"Riga {line_number}: entità non valida: {entity}")
        start, end, label = entity
        if label not in LABELS:
            raise ValueError(f"Riga {line_number}: label non valida {label!r} in frase: {text}")
        if not isinstance(start, int) or not isinstance(end, int) or start < 0 or end > len(text) or start >= end:
            raise ValueError(f"Riga {line_number}: offset non validi {entity} in frase: {text}")
        span = text[start:end]
        if span != span.strip():
            raise ValueError(f"Riga {line_number}: span con spazi extra {span!r} in frase: {text}")
        if any(start < other_end and end > other_start for other_start, other_end in spans):
            raise ValueError(f"Riga {line_number}: entità sovrapposte in frase: {text}")
        spans.append((start, end))


def train(examples: list[tuple[str, dict]], iterations: int) -> spacy.Language:
    nlp = spacy.blank("it")
    ner = nlp.add_pipe("ner")
    for label in LABELS:
        ner.add_label(label)

    training_examples = [
        Example.from_dict(nlp.make_doc(text), annotations)
        for text, annotations in examples
    ]

    optimizer = nlp.initialize(lambda: training_examples)
    for iteration in range(iterations):
        random.shuffle(training_examples)
        losses = {}
        for batch in minibatch(training_examples, size=8):
            nlp.update(batch, sgd=optimizer, losses=losses)
        print(f"Iterazione {iteration + 1}/{iterations} - perdite: {losses}")
    return nlp


def main() -> None:
    root = package_root()
    parser = argparse.ArgumentParser()
    parser.add_argument(
        "--dataset",
        default=str(root / "data" / "slot_dataset.jsonl"),
    )
    parser.add_argument(
        "--output",
        default=str(root / "models" / "slot_filler_spacy"),
    )
    parser.add_argument("--iterations", type=int, default=80)
    args = parser.parse_args()

    dataset_path = Path(args.dataset).expanduser().resolve()
    output_path = Path(args.output).expanduser().resolve()
    examples = load_dataset(dataset_path)
    nlp = train(examples, args.iterations)

    output_path.mkdir(parents=True, exist_ok=True)
    nlp.to_disk(output_path)
    print(f"Salvato slot filler spaCy in {output_path}")


if __name__ == "__main__":
    main()
