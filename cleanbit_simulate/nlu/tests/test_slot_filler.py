#!/usr/bin/env python3
from __future__ import annotations

import sys
from pathlib import Path
from typing import Any


def package_root() -> Path:
    return Path(__file__).resolve().parents[3]


sys.path.insert(0, str(package_root()))

from cleanbit_simulate.nlu.slots.supervised_slot_extractor import SupervisedSlotExtractor


AREA_NAMES = [
    "cucina",
    "bagno",
    "salone",
    "soggiorno",
    "corridoio",
    "camera",
    "ripostiglio",
    "ingresso",
    "sala da pranzo",
    "zona divano",
    "camera ospiti",
]

CASES = [
    ("pulisci la cucina", ["cucina"], [], []),
    ("pulisci il bagno e l'ingresso", ["bagno", "ingresso"], [], []),
    ("pulisci la cucina evitando il bagno", ["cucina"], ["bagno"], []),
    ("pulisci la cucina passando dal salone", ["cucina"], [], ["salone"]),
    ("pulisci la cucina passando dal salone ma evita il bagno", ["cucina"], ["bagno"], ["salone"]),
    ("vai in camera passando per il corridoio", ["camera"], [], ["corridoio"]),
    ("vai nella sala da pranzo evitando il bagno", ["sala da pranzo"], ["bagno"], []),
]


def normalize_slots(slots: dict[str, Any]) -> dict[str, list[str]]:
    constraints = slots.get("constraints", {})
    return {
        "targets": slots.get("targets", []),
        "avoid": constraints.get("avoid", []),
        "via": constraints.get("via", []),
    }


def main() -> None:
    extractor = SupervisedSlotExtractor()
    if not extractor.available:
        print("FAIL: modello slot filler non disponibile. Esegui prima train_slot_filler.py")
        raise SystemExit(1)

    passed = 0
    for text, targets, avoid, via in CASES:
        predicted = normalize_slots(extractor.extract(text, "CLEAN_AREA", AREA_NAMES))
        expected = {"targets": targets, "avoid": avoid, "via": via}
        ok = predicted == expected
        if ok:
            passed += 1
        print(f"{'PASS' if ok else 'FAIL'}: {text}")
        print(f"  expected: {expected}")
        print(f"  predicted: {predicted}")

    total = len(CASES)
    accuracy = passed / total if total else 0.0
    print(f"\nAccuracy: {passed}/{total} = {accuracy:.3f}")
    raise SystemExit(0 if passed == total else 1)


if __name__ == "__main__":
    main()

