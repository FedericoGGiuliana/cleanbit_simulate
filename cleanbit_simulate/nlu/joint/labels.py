from __future__ import annotations


INTENT_LABELS = [
    "START_MAPPING",
    "CLEAN_AREA",
    "GO_TO_AREA",
    "RETURN_HOME",
    "STOP_TASK",
    "UNKNOWN",
]

SLOT_LABELS = [
    "O",
    "B-TARGET",
    "I-TARGET",
    "B-AVOID",
    "I-AVOID",
]

INTENT_TO_ACTION = {
    "START_MAPPING": "map",
    "CLEAN_AREA": "clean",
    "GO_TO_AREA": "navigate",
    "RETURN_HOME": "return_home",
    "STOP_TASK": "stop",
    "UNKNOWN": None,
}

INTENT_TO_ID = {label: index for index, label in enumerate(INTENT_LABELS)}
ID_TO_INTENT = {index: label for label, index in INTENT_TO_ID.items()}
SLOT_TO_ID = {label: index for index, label in enumerate(SLOT_LABELS)}
ID_TO_SLOT = {index: label for label, index in SLOT_TO_ID.items()}
