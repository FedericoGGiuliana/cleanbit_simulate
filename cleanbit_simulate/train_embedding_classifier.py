#!/usr/bin/env python3
from __future__ import annotations

import argparse
import csv
from pathlib import Path

from joblib import dump
from sentence_transformers import SentenceTransformer
from sklearn.linear_model import LogisticRegression


MODEL_NAME = "paraphrase-multilingual-MiniLM-L12-v2"


def default_package_root() -> Path:
    return Path(__file__).resolve().parents[1]


def load_dataset(dataset_path: Path) -> tuple[list[str], list[str]]:
    texts: list[str] = []
    labels: list[str] = []
    with dataset_path.open("r", encoding="utf-8", newline="") as dataset_file:
        reader = csv.DictReader(dataset_file)
        for row in reader:
            text = row["text"].strip()
            intent = row["intent"].strip()
            if text and intent:
                texts.append(text)
                labels.append(intent)
    return texts, labels


def main() -> None:
    package_root = default_package_root()
    parser = argparse.ArgumentParser()
    parser.add_argument(
        "--dataset",
        default=str(package_root / "data" / "commands_dataset.csv"),
    )
    parser.add_argument(
        "--output",
        default=str(package_root / "models" / "intent_classifier.joblib"),
    )
    args = parser.parse_args()

    dataset_path = Path(args.dataset).expanduser().resolve()
    output_path = Path(args.output).expanduser().resolve()
    texts, labels = load_dataset(dataset_path)
    if not texts:
        raise RuntimeError(f"Dataset vuoto: {dataset_path}")

    embedding_model = SentenceTransformer(MODEL_NAME)
    embeddings = embedding_model.encode(texts, show_progress_bar=True)
    classifier = LogisticRegression(max_iter=1000)
    classifier.fit(embeddings, labels)

    output_path.parent.mkdir(parents=True, exist_ok=True)
    dump(
        {
            "classifier": classifier,
            "labels": list(classifier.classes_),
            "embedding_model": MODEL_NAME,
        },
        output_path,
    )
    print(f"Salvato classificatore intent in {output_path}")


if __name__ == "__main__":
    main()

