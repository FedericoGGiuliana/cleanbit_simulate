#!/usr/bin/env python3
from __future__ import annotations

import argparse
import json
import random
import sys
from pathlib import Path

import torch
from torch.optim import AdamW
from torch.utils.data import DataLoader


def package_root() -> Path:
    return Path(__file__).resolve().parents[3]


sys.path.insert(0, str(package_root()))

from cleanbit_simulate.nlu.joint.dataset_utils import JointNLUDataset, read_jsonl
from cleanbit_simulate.nlu.joint.joint_nlu_model import BERTINO_MODEL_NAME, JointNLUModel
from cleanbit_simulate.nlu.joint.labels import INTENT_LABELS, SLOT_LABELS


def split_rows(rows: list[dict], validation_ratio: float = 0.1) -> tuple[list[dict], list[dict]]:
    rows = list(rows)
    random.Random(42).shuffle(rows)
    validation_size = max(1, int(len(rows) * validation_ratio))
    return rows[validation_size:], rows[:validation_size]


def evaluate(model: JointNLUModel, loader: DataLoader, device: torch.device) -> float:
    model.eval()
    total_loss = 0.0
    total_batches = 0
    with torch.no_grad():
        for batch in loader:
            batch = {key: value.to(device) for key, value in batch.items()}
            outputs = model(**batch)
            total_loss += float(outputs["loss"].item())
            total_batches += 1
    return total_loss / max(total_batches, 1)


def main() -> None:
    root = package_root()
    parser = argparse.ArgumentParser()
    parser.add_argument("--dataset", default=str(root / "data" / "joint_nlu_train.jsonl"))
    parser.add_argument("--output", default=str(root / "models" / "joint_nlu_bertino"))
    parser.add_argument("--epochs", type=int, default=10)
    parser.add_argument("--max-length", type=int, default=32)
    parser.add_argument("--batch-size", type=int, default=16)
    parser.add_argument("--learning-rate", type=float, default=3e-5)
    parser.add_argument("--warmup-ratio", type=float, default=0.1)
    args = parser.parse_args()

    from transformers import AutoTokenizer, get_linear_schedule_with_warmup

    dataset_path = Path(args.dataset).expanduser().resolve()
    output_path = Path(args.output).expanduser().resolve()
    rows = read_jsonl(dataset_path)
    train_rows, validation_rows = split_rows(rows)

    tokenizer = AutoTokenizer.from_pretrained(BERTINO_MODEL_NAME, use_fast=True)
    train_dataset = JointNLUDataset(train_rows, tokenizer, max_length=args.max_length)
    validation_dataset = JointNLUDataset(validation_rows, tokenizer, max_length=args.max_length)
    train_loader = DataLoader(train_dataset, batch_size=args.batch_size, shuffle=True)
    validation_loader = DataLoader(validation_dataset, batch_size=args.batch_size)

    device = torch.device("cuda" if torch.cuda.is_available() else "cpu")
    model = JointNLUModel(len(INTENT_LABELS), len(SLOT_LABELS)).to(device)
    optimizer = AdamW(model.parameters(), lr=args.learning_rate)
    total_steps = len(train_loader) * args.epochs
    warmup_steps = int(total_steps * args.warmup_ratio)
    scheduler = get_linear_schedule_with_warmup(optimizer, warmup_steps, total_steps)

    best_validation_loss = float("inf")
    output_path.mkdir(parents=True, exist_ok=True)

    for epoch in range(args.epochs):
        model.train()
        total_loss = 0.0
        for batch in train_loader:
            batch = {key: value.to(device) for key, value in batch.items()}
            optimizer.zero_grad()
            outputs = model(**batch)
            loss = outputs["loss"]
            loss.backward()
            torch.nn.utils.clip_grad_norm_(model.parameters(), max_norm=1.0)
            optimizer.step()
            scheduler.step()
            total_loss += float(loss.item())

        train_loss = total_loss / max(len(train_loader), 1)
        validation_loss = evaluate(model, validation_loader, device)
        print(
            f"Epoch {epoch + 1}/{args.epochs} - "
            f"train_loss={train_loss:.4f} validation_loss={validation_loss:.4f}"
        )

        if validation_loss < best_validation_loss:
            best_validation_loss = validation_loss
            model.encoder.save_pretrained(output_path / "encoder")
            tokenizer.save_pretrained(output_path)
            torch.save(
                {
                    "model_state_dict": model.state_dict(),
                    "model_name": BERTINO_MODEL_NAME,
                    "max_length": args.max_length,
                },
                output_path / "joint_nlu_model.pt",
            )
            with (output_path / "labels.json").open("w", encoding="utf-8") as labels_file:
                json.dump(
                    {
                        "intent_labels": INTENT_LABELS,
                        "slot_labels": SLOT_LABELS,
                    },
                    labels_file,
                    ensure_ascii=False,
                    indent=2,
                )
            print(f"Salvato best model in {output_path}")


if __name__ == "__main__":
    main()
