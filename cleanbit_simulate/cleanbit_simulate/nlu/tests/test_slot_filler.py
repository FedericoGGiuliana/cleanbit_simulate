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
    ("pulisci la cucina evitando il bagno", ["cucina"], ["bagno"]),
    ("pulisci il bagno e l'ingresso, ma evita la cucina", ["bagno", "ingresso"], ["cucina"]),
    ("vai in cucina ma evita il soggiorno e il bagno", ["cucina"], ["soggiorno", "bagno"]),
    ("vai in cucina, evita il soggiorno e il bagno", ["cucina"], ["soggiorno", "bagno"]),
    ("vai in cucina, non andare nel soggiorno e manco in bagno", ["cucina"], ["soggiorno", "bagno"]),
    ("non andare in soggiorno ma pulisci la cucina", ["cucina"], ["soggiorno"]),
    ("pulisci la cucina senza passare dal bagno", ["cucina"], ["bagno"]),
    ("pulisci cucina e bagno ma non entrare in salone", ["cucina", "bagno"], ["salone"]),
    ("spolvera la cucina", ["cucina"], []),
    ("spolvera il bagno", ["bagno"], []),
    ("spolvera il soggiorno", ["soggiorno"], []),
    ("spolvera la camera", ["camera"], []),
    ("sistema la cucina", ["cucina"], []),
    ("sistema il soggiorno", ["soggiorno"], []),
    ("sistema il bagno", ["bagno"], []),
    ("dai una passata in cucina", ["cucina"], []),
    ("dai una passata in bagno", ["bagno"], []),
    ("fai una passata in soggiorno", ["soggiorno"], []),
    ("fai una pulita in camera", ["camera"], []),
    ("ripulisci il bagno", ["bagno"], []),
    ("ripulisci cucina e soggiorno", ["cucina", "soggiorno"], []),
    ("dai una sistemata alla cucina", ["cucina"], []),
    ("dai una sistemata al salone", ["salone"], []),
    ("passa in bagno", ["bagno"], []),
    ("passa in cucina", ["cucina"], []),
    ("pulisci bene il soggiorno", ["soggiorno"], []),
    ("spolvera la cucina evitando il bagno", ["cucina"], ["bagno"]),
    ("sistema il soggiorno ma evita il bagno", ["soggiorno"], ["bagno"]),
    ("dai una passata in cucina ma non andare in salone", ["cucina"], ["salone"]),
    ("fai una pulita in bagno evitando la cucina", ["bagno"], ["cucina"]),
    ("ripulisci la camera senza passare dal soggiorno", ["camera"], ["soggiorno"]),
    ("vai in cucina, evita il soggiorno, il bagno", ["cucina"], ["soggiorno", "bagno"]),
    ("vai in cucina però evita il soggiorno e il bagno", ["cucina"], ["soggiorno", "bagno"]),
    ("vai in cucina, non passare da soggiorno né in bagno", ["cucina"], ["soggiorno", "bagno"]),
    ("pulisci cucina e bagno", ["cucina", "bagno"], []),
    ("pulisci cucina, bagno e soggiorno", ["cucina", "bagno", "soggiorno"], []),
    ("pulisci cucina e bagno ma evita soggiorno e camera", ["cucina", "bagno"], ["soggiorno", "camera"]),
    ("evita il bagno e pulisci la cucina", ["cucina"], ["bagno"]),
    ("non entrare in bagno, pulisci la cucina", ["cucina"], ["bagno"]),
    ("non passare dal salone e pulisci il bagno", ["bagno"], ["salone"]),
    ("pulisci tutto tranne il bagno", [], ["bagno"]),
    ("pulisci la casa tranne il bagno", [], ["bagno"]),
    ("pulisci cucina escluso bagno", ["cucina"], ["bagno"]),
    ("pulisci cucina a parte bagno", ["cucina"], ["bagno"]),
    ("vai in cucina, non in bagno", ["cucina"], ["bagno"]),
    ("raggiungi il soggiorno, ma non il bagno", ["soggiorno"], ["bagno"]),
    ("spolvera cucina e soggiorno, ma non bagno", ["cucina", "soggiorno"], ["bagno"]),
    ("dai una sistemata alla camera senza entrare in bagno", ["camera"], ["bagno"]),
    ("fai una pulita in salone, manco in cucina", ["salone"], ["cucina"]),
    ("vai in cucina né bagno né salone", ["cucina"], ["bagno", "salone"]),
    ("pulisci bagno però evita cucina, salone e corridoio", ["bagno"], ["cucina", "salone", "corridoio"]),
    ("sistema il soggiorno, non andare in bagno e non entrare in cucina", ["soggiorno"], ["bagno", "cucina"]),
    ("ripulisci camera ospiti evitando zona divano", ["camera ospiti"], ["zona divano"]),
    ("pulisci sala da pranzo senza passare dal corridoio", ["sala da pranzo"], ["corridoio"]),
    ("spolvera cucina, bagno, salone", ["cucina", "bagno", "salone"], []),
    ("sistema camera e ripostiglio", ["camera", "ripostiglio"], []),
    ("dai una passata in ingresso e corridoio", ["ingresso", "corridoio"], []),
    ("fai una pulita in sala da pranzo e zona divano", ["sala da pranzo", "zona divano"], []),
    ("ripulisci camera ospiti e bagno ma evita salone", ["camera ospiti", "bagno"], ["salone"]),
    ("evita cucina e bagno, vai in salone", ["salone"], ["cucina", "bagno"]),
    ("non andare in corridoio né in bagno, raggiungi la camera", ["camera"], ["corridoio", "bagno"]),
    ("a parte il bagno pulisci la cucina", ["cucina"], ["bagno"]),
    ("escluso il salone pulisci soggiorno e cucina", ["soggiorno", "cucina"], ["salone"]),
    ("tranne camera e bagno, pulisci il soggiorno", ["soggiorno"], ["camera", "bagno"]),
    ("pulisci il ripostiglio, però evita cucina e corridoio", ["ripostiglio"], ["cucina", "corridoio"]),
    ("vai al salone, evita camera ospiti e zona divano", ["salone"], ["camera ospiti", "zona divano"]),
    ("pulisci bagno, evitando cucina e salone, e pulisci soggiorno anche", ["bagno", "soggiorno"], ["cucina", "salone"]),
    ("pulisci cucina ma evita bagno e poi sistema soggiorno", ["cucina", "soggiorno"], ["bagno"]),
    ("pulisci sala da pranzo e zona divano ma evita corridoio", ["sala da pranzo", "zona divano"], ["corridoio"]),
    ("ripulisci bagno, cucina, salone e corridoio", ["bagno", "cucina", "salone", "corridoio"], []),
    ("raggiungi camera evitando salone, cucina e bagno", ["camera"], ["salone", "cucina", "bagno"]),
    ("spolvera camera evitando salone e ripulisci ingresso", ["camera", "ingresso"], ["salone"]),
    ("pulisci bagno e cucina, evita salone, poi pulisci camera", ["bagno", "cucina", "camera"], ["salone"]),
    ("vai in cucina evitando bagno e poi raggiungi soggiorno", ["cucina", "soggiorno"], ["bagno"]),
]


def normalize_slots(slots: dict[str, Any]) -> dict[str, list[str]]:
    constraints = slots.get("constraints", {})
    return {
        "targets": slots.get("targets", []),
        "avoid": constraints.get("avoid", []),
    }


def main() -> None:
    extractor = SupervisedSlotExtractor()
    if not extractor.available:
        print("FAIL: modello slot filler non disponibile. Esegui prima train_slot_filler.py")
        raise SystemExit(1)

    passed = 0
    for text, targets, avoid in CASES:
        predicted = normalize_slots(extractor.extract(text, "CLEAN_AREA", AREA_NAMES))
        expected = {"targets": targets, "avoid": avoid}
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
