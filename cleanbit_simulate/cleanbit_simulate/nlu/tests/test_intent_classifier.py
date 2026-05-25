#!/usr/bin/env python3
from __future__ import annotations

import sys
from pathlib import Path


def package_root() -> Path:
    return Path(__file__).resolve().parents[3]


sys.path.insert(0, str(package_root()))

from cleanbit_simulate.nlu.intent.embedding_intent_classifier import EmbeddingIntentClassifier


CASES = [
    ("spolvera la cucina", "CLEAN_AREA"),
    ("sistema il soggiorno", "CLEAN_AREA"),
    ("dai una passata in bagno", "CLEAN_AREA"),
    ("fai una pulita in camera", "CLEAN_AREA"),
    ("ripulisci il salone", "CLEAN_AREA"),
    ("dai una sistemata alla cucina", "CLEAN_AREA"),
    ("pulisci cucina e bagno", "CLEAN_AREA"),
    ("pulisci bene il soggiorno", "CLEAN_AREA"),
    ("passa in cucina", "CLEAN_AREA"),
    ("vai in cucina", "GO_TO_AREA"),
    ("raggiungi il bagno", "GO_TO_AREA"),
    ("portati in soggiorno", "GO_TO_AREA"),
    ("spostati in camera", "GO_TO_AREA"),
    ("portami in salone", "GO_TO_AREA"),
    ("mappa la casa", "START_MAPPING"),
    ("inizia la mappatura", "START_MAPPING"),
    ("esplora l'ambiente", "START_MAPPING"),
    ("crea la mappa", "START_MAPPING"),
    ("torna alla base", "RETURN_HOME"),
    ("rientra alla base", "RETURN_HOME"),
    ("torna al punto iniziale", "RETURN_HOME"),
    ("cosa stai facendo", "STATUS_REQUEST"),
    ("a che punto sei", "STATUS_REQUEST"),
    ("che comandi capisci", "HELP_REQUEST"),
    ("aiuto", "HELP_REQUEST"),
    ("quanto fa due più due", "UNKNOWN"),
    ("raccontami una barzelletta", "UNKNOWN"),
    ("che tempo fa oggi", "UNKNOWN"),
]


def main() -> None:
    classifier = EmbeddingIntentClassifier()
    passed = 0
    for text, expected in CASES:
        predicted, confidence = classifier.classify(text)
        ok = predicted == expected
        if ok:
            passed += 1
        print(f"{'PASS' if ok else 'FAIL'}: {text}")
        print(f"  expected: {expected}")
        print(f"  predicted: {predicted} ({confidence:.3f})")

    total = len(CASES)
    accuracy = passed / total if total else 0.0
    print(f"\nAccuracy: {passed}/{total} = {accuracy:.3f}")
    raise SystemExit(0 if passed == total else 1)


if __name__ == "__main__":
    main()
