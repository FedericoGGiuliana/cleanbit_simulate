#!/usr/bin/env python3
from __future__ import annotations

import argparse
import json
import random
from pathlib import Path

import spacy
from spacy.training import Example
from spacy.util import minibatch


LABELS = ("TARGET", "AVOID", "VIA")


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
            examples.append((row["text"], {"entities": row["entities"]}))
    if not examples:
        raise RuntimeError(f"Dataset vuoto: {dataset_path}")
    return examples


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
    parser.add_argument("--iterations", type=int, default=35)
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

