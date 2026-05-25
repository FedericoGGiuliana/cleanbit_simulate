#!/usr/bin/env python3
from __future__ import annotations

import sys
from pathlib import Path


def package_root() -> Path:
    return Path(__file__).resolve().parents[3]


sys.path.insert(0, str(package_root()))

from cleanbit_simulate.nlu.joint.dataset_utils import read_jsonl
from cleanbit_simulate.nlu.joint.inference import JointNLUInference
from cleanbit_simulate.nlu.joint.labels import INTENT_TO_ACTION


def normalize_expected(row: dict) -> tuple[str, list[str], list[str]]:
    targets = []
    avoid = []
    for entity in row.get("entities", []):
        value = row["text"][entity["start"]:entity["end"]].lower()
        if entity["label"] == "TARGET":
            targets.append(value)
        elif entity["label"] == "AVOID":
            avoid.append(value)
    return row["intent"], unique(targets), unique(avoid)


def unique(values: list[str]) -> list[str]:
    seen = set()
    result = []
    for value in values:
        if value not in seen:
            seen.add(value)
            result.append(value)
    return result


def main() -> None:
    root = package_root()
    dataset_path = root / "data" / "joint_nlu_test_unseen_entities.jsonl"
    rows = read_jsonl(dataset_path)
    parser = JointNLUInference()
    if not parser.available:
        print("FAIL: modello joint NLU non disponibile. Esegui prima train_joint_nlu.py")
        raise SystemExit(1)

    intent_ok = 0
    targets_ok = 0
    avoid_ok = 0
    frame_ok = 0
    action_ok = 0

    for row in rows:
        expected_intent, expected_targets, expected_avoid = normalize_expected(row)
        predicted = parser.parse(row["text"])
        predicted_intent = predicted["intent"]
        predicted_targets = predicted["targets"]
        predicted_avoid = predicted["avoid"]
        expected_action = None if expected_intent == "UNKNOWN" else INTENT_TO_ACTION[expected_intent]
        predicted_action = predicted["action"]

        intent_match = predicted_intent == expected_intent
        targets_match = predicted_targets == expected_targets
        avoid_match = predicted_avoid == expected_avoid
        action_match = predicted_action == expected_action
        full_match = intent_match and action_match and targets_match and avoid_match

        intent_ok += int(intent_match)
        action_ok += int(action_match)
        targets_ok += int(targets_match)
        avoid_ok += int(avoid_match)
        frame_ok += int(full_match)

        print(f"{'PASS' if full_match else 'FAIL'}: {row['text']}")
        print(
            f"  expected intent={expected_intent} action={expected_action} "
            f"targets={expected_targets} avoid={expected_avoid}"
        )
        print(
            f"  predicted intent={predicted_intent} action={predicted_action} "
            f"confidence={predicted['confidence']:.3f} "
            f"targets={predicted_targets} avoid={predicted_avoid}"
        )

    total = len(rows)
    print(f"\nIntent accuracy: {intent_ok}/{total} = {intent_ok / total:.3f}")
    print(f"Action accuracy: {action_ok}/{total} = {action_ok / total:.3f}")
    print(f"Targets exact match: {targets_ok}/{total} = {targets_ok / total:.3f}")
    print(f"Avoid exact match: {avoid_ok}/{total} = {avoid_ok / total:.3f}")
    print(f"Full frame accuracy: {frame_ok}/{total} = {frame_ok / total:.3f}")
    raise SystemExit(0 if frame_ok == total else 1)


if __name__ == "__main__":
    main()
