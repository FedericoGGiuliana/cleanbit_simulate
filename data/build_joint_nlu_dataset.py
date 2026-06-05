#!/usr/bin/env python3
from __future__ import annotations

import json
import random
from pathlib import Path


REALISTIC_AREAS = [
    "cucina",
    "bagno",
    "camera",
    "salone",
    "soggiorno",
    "corridoio",
    "ingresso",
    "ripostiglio",
    "sala da pranzo",
    "zona divano",
    "camera ospiti",
    "lavanderia",
    "studio",
    "balcone",
    "terrazza",
    "garage",
    "officina",
    "salotto",
    "camino",
    "armeria",
]

TRAIN_ARTIFICIAL_AREAS = [
    "zona alpha",
    "zona beta",
    "area rossa",
    "area blu",
    "stanza nord",
    "stanza sud",
    "laboratorio",
    "deposito",
    "settore uno",
    "settore due",
    "sala prova",
    "area test",
    "stanza delle armi",
    "piano di sopra",
    "sala dei giochi",
    "stanza degli ospiti",
    "zona del camino",
    "area della lavatrice",
    "corridoio delle camere",
    "stanza al piano terra",
    "piano inferiore",
    "zona della porta",
    "bunker-7",
    "zona A",
    "zona B",
    "zona C",
]

UNSEEN_AREAS = [
    "gilgamesh",
    "mordor",
    "avalon",
    "narnia",
    "atlantide",
    "olimpo",
    "asgard",
    "eldorado",
]

START_MAPPING_TEXTS = [
    "mappa la casa",
    "inizia la mappatura",
    "crea una nuova mappa",
    "avvia la mappa",
    "esplora la casa",
    "scansiona l'ambiente",
    "inizia a mappare",
    "fai la mappatura della casa",
    "avvia slam",
    "costruisci la mappa",
]

RETURN_HOME_TEXTS = [
    "torna alla base",
    "torna in base",
    "torna a casa",
    "ritorna a casa",
    "ritorna alla base",
    "rientra alla base",
    "rientra in base",
    "rientra a casa",
    "vai alla base",
    "vai in base",
    "vai nella base",
    "raggiungi la base",
    "raggiungi la stazione",
    "raggiungi la stazione di ricarica",
    "torna alla stazione",
    "torna alla stazione di ricarica",
    "ritorna alla docking station",
    "vai alla docking station",
    "vai alla stazione di ricarica",
    "rientra alla docking station",
    "rientra alla stazione di ricarica",
    "torna al punto di partenza",
    "ritorna al punto iniziale",
    "torna al punto iniziale",
    "torna dove sei partito",
    "rientra al punto di partenza",
    "vai a ricaricarti",
    "vai a caricarti",
    "vai a ricaricare la batteria",
    "vai a caricare la batteria",
    "ricarica la batteria",
    "vai in carica",
    "mettiti in carica",
    "torna in carica",
    "torna a ricaricarti",
    "torna alla base di ricarica",
    "raggiungi la base di ricarica",
    "portati alla base",
    "portati alla stazione di ricarica",
]

STOP_TASK_TEXTS = [
    "fermati",
    "fermati subito",
    "stop",
    "stop tutto",
    "alt",
    "blocca tutto",
    "blocca il robot",
    "interrompi",
    "interrompi tutto",
    "annulla il task",
    "annulla il comando",
    "ferma la pulizia",
    "ferma il movimento",
    "arresta il robot",
    "smetti di muoverti",
    "termina l'operazione",
    "cancella il task corrente",
    "interrompi la navigazione",
    "blocca immediatamente l'operazione",
    "ferma quello che stai facendo",
]

UNKNOWN_TEXTS = [
    "quanto fa due più due",
    "raccontami una storia",
    "che tempo fa domani",
    "ordina una pizza",
    "riproduci una canzone",
    "chi ha scritto l'iliade",
    "fammi vedere un film",
    "calcola la radice quadrata",
    "accendi la televisione",
    "mandami un messaggio",
    "apri youtube",
    "cerca un ristorante",
    "imposta una sveglia",
    "dimmi una barzelletta",
    "traduci questa frase",
    "42",
    "!!!",
    "ripeti",
    "vai",
    "torna",
    "ciao",
    "ciao come stai",
    "buongiorno",
    "grazie",
    "come va",
    "tutto bene",
    "il cielo è blu",
    "sì",
    "si",
    "ok",
    "confermo",
    "esatto",
    "va bene",
    "procedi",
    "corretto",
    "certo",
    "fai pure",
    "no",
    "annulla",
    "non confermo",
    "sbagliato",
    "lascia stare",
    "non va bene",
    "negativo",
    "non procedere",
    "non farlo",
    "cosa stai facendo",
    "qual è il tuo stato",
    "a che punto sei",
    "dove sei ora",
    "sei occupato",
    "stai pulendo",
    "che task stai eseguendo",
    "mostrami lo stato",
    "dimmi cosa stai facendo",
    "sei in movimento",
    "che comandi capisci",
    "cosa posso chiederti",
    "mostrami i comandi disponibili",
    "aiutami",
    "dammi aiuto",
    "quali funzioni hai",
    "cosa sai fare",
    "spiegami i comandi",
    "mostra la guida",
    "come posso usarti",
]


def write_jsonl(path: Path, rows: list[dict]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", encoding="utf-8") as output:
        for row in rows:
            output.write(json.dumps(row, ensure_ascii=False) + "\n")


def make_row(text: str, intent: str, targets: list[str] | None = None, avoid: list[str] | None = None) -> dict:
    entities = []
    occupied: list[tuple[int, int]] = []
    items = [(target, "TARGET") for target in targets or []] + [(item, "AVOID") for item in avoid or []]
    for value, label in sorted(items, key=lambda item: len(item[0]), reverse=True):
        start = _find_free_span(text, value, occupied)
        end = start + len(value)
        entities.append({"start": start, "end": end, "label": label})
        occupied.append((start, end))
    entities.sort(key=lambda entity: entity["start"])
    return {
        "text": text,
        "intent": intent,
        "entities": entities,
    }


def _find_free_span(text: str, value: str, occupied: list[tuple[int, int]]) -> int:
    start = text.find(value)
    while start != -1:
        end = start + len(value)
        if not any(start < used_end and end > used_start for used_start, used_end in occupied):
            return start
        start = text.find(value, start + 1)
    raise ValueError(f"Span {value!r} non trovato in: {text!r}")


def choose_area(rng: random.Random, artificial_ratio: float = 0.3) -> str:
    if rng.random() < artificial_ratio:
        return rng.choice(TRAIN_ARTIFICIAL_AREAS)
    return rng.choice(REALISTIC_AREAS)


def choose_distinct_areas(rng: random.Random, count: int, artificial_ratio: float = 0.3) -> list[str]:
    pool = REALISTIC_AREAS + TRAIN_ARTIFICIAL_AREAS
    rng.shuffle(pool)
    selected = []
    while len(selected) < count:
        candidate = choose_area(rng, artificial_ratio)
        if candidate not in selected:
            selected.append(candidate)
    return selected


def build_area_rows(rng: random.Random) -> list[dict]:
    rows = []
    go_single_templates = [
        "vai in {target}",
        "vai a {target}",
        "raggiungi {target}",
        "raggiungi la zona {target}",
        "spostati in {target}",
        "spostati verso {target}",
        "dirigiti verso {target}",
        "muoviti verso {target}",
        "portati in {target}",
    ]
    go_avoid_templates = [
        "vai in {target} evitando {avoid1}",
        "vai in {target} evitando {avoid1} e {avoid2}",
        "vai in {target} evitando {avoid1}, {avoid2} e {avoid3}",
        "raggiungi {target} senza passare da {avoid1}",
        "raggiungi {target} senza passare da {avoid1} e {avoid2}",
        "spostati in {target} non passando da {avoid1}",
        "dirigiti verso {target} evitando {avoid1}, {avoid2}, {avoid3} e {avoid4}",
        "vai in {target} non passare da {avoid1} né da {avoid2}",
        "vai in {target} non passare da {avoid1} né da {avoid2} né da {avoid3}",
    ]
    clean_single_templates = [
        "pulisci {target}",
        "aspira {target}",
        "spolvera {target}",
        "lava {target}",
        "ripulisci {target}",
        "sistema {target}",
        "fai una pulita in {target}",
        "fai una passata al {target}",
        "dai una passata in {target}",
        "pulisci bene {target}",
    ]
    clean_avoid_templates = [
        "pulisci {target} evitando {avoid1}",
        "pulisci {target} evitando {avoid1} e {avoid2}",
        "pulisci {target} evitando {avoid1}, {avoid2} e {avoid3}",
        "aspira {target} senza passare da {avoid1}",
        "spolvera {target} evitando {avoid1} e {avoid2}",
        "lava {target} evitando {avoid1}, {avoid2}, {avoid3} e {avoid4}",
    ]
    multi_templates = [
        ("pulisci {target1} e {target2}", "CLEAN_AREA", 2, 0),
        ("pulisci {target1}, {target2} e {target3}", "CLEAN_AREA", 3, 0),
        ("aspira {target1} e {target2} evitando {avoid1}", "CLEAN_AREA", 2, 1),
        ("pulisci {target1}, {target2} e {target3} evitando {avoid1} e {avoid2}", "CLEAN_AREA", 3, 2),
        ("vai in {target1} e poi in {target2} evitando {avoid1}", "GO_TO_AREA", 2, 1),
    ]

    for _ in range(180):
        target = choose_area(rng)
        rows.append(make_row(rng.choice(go_single_templates).format(target=target), "GO_TO_AREA", [target], []))

    for _ in range(100):
        areas = choose_distinct_areas(rng, 5)
        target, avoids = areas[0], areas[1:]
        template = rng.choice(go_avoid_templates)
        text = template.format(target=target, avoid1=avoids[0], avoid2=avoids[1], avoid3=avoids[2], avoid4=avoids[3])
        rows.append(make_row(text, "GO_TO_AREA", [target], _used_avoids(template, avoids)))

    for _ in range(180):
        target = choose_area(rng)
        rows.append(make_row(rng.choice(clean_single_templates).format(target=target), "CLEAN_AREA", [target], []))

    for _ in range(100):
        areas = choose_distinct_areas(rng, 5)
        target, avoids = areas[0], areas[1:]
        template = rng.choice(clean_avoid_templates)
        text = template.format(target=target, avoid1=avoids[0], avoid2=avoids[1], avoid3=avoids[2], avoid4=avoids[3])
        rows.append(make_row(text, "CLEAN_AREA", [target], _used_avoids(template, avoids)))

    for template, intent, target_count, avoid_count in multi_templates:
        for _ in range(18):
            areas = choose_distinct_areas(rng, target_count + avoid_count)
            targets = areas[:target_count]
            avoids = areas[target_count:]
            values = {f"target{index + 1}": value for index, value in enumerate(targets)}
            values.update({f"avoid{index + 1}": value for index, value in enumerate(avoids)})
            text = template.format(**values)
            rows.append(make_row(text, intent, targets, avoids))

    return rows


def _used_avoids(template: str, avoids: list[str]) -> list[str]:
    return [
        avoids[index]
        for index in range(len(avoids))
        if f"{{avoid{index + 1}}}" in template
    ]


def repeat_text_rows(texts: list[str], intent: str, count: int) -> list[dict]:
    rows = []
    for index in range(count):
        rows.append(make_row(texts[index % len(texts)], intent, [], []))
    return rows


def build_training_rows() -> list[dict]:
    rng = random.Random(7)
    rows = build_area_rows(rng)
    rows.extend(build_generalization_focus_rows())
    rows.extend(repeat_text_rows(START_MAPPING_TEXTS, "START_MAPPING", 50))
    rows.extend(build_return_home_rows(rng))
    rows.extend(repeat_text_rows(STOP_TASK_TEXTS, "STOP_TASK", 60))
    rows.extend(repeat_text_rows(UNKNOWN_TEXTS, "UNKNOWN", 180))
    rng.shuffle(rows)
    return rows


def build_return_home_rows(rng: random.Random) -> list[dict]:
    rows = repeat_text_rows(RETURN_HOME_TEXTS, "RETURN_HOME", 120)
    return_avoid_templates = [
        "torna alla base evitando {avoid1}",
        "torna alla base evitando {avoid1} e {avoid2}",
        "vai in base evitando {avoid1}",
        "rientra alla stazione di ricarica evitando {avoid1} e {avoid2}",
        "vai a ricaricarti evitando il {avoid1}",
        "torna alla docking station evitando {avoid1}",
        "raggiungi la base di ricarica senza passare da {avoid1}",
        "torna al punto iniziale senza passare da {avoid1} e {avoid2}",
        "rientra alla base evitando {avoid1}, {avoid2} e {avoid3}",
        "vai in carica evitando {avoid1}, {avoid2} e {avoid3}",
    ]
    fixed_rows = [
        make_row("torna alla base evitando cucina", "RETURN_HOME", [], ["cucina"]),
        make_row("torna alla base evitando bagno e salone", "RETURN_HOME", [], ["bagno", "salone"]),
        make_row("vai in base evitando corridoio", "RETURN_HOME", [], ["corridoio"]),
        make_row("rientra alla stazione di ricarica evitando cucina e bagno", "RETURN_HOME", [], ["cucina", "bagno"]),
        make_row("vai a ricaricarti evitando il salone", "RETURN_HOME", [], ["salone"]),
        make_row("torna alla docking station evitando zona divano", "RETURN_HOME", [], ["zona divano"]),
        make_row("raggiungi la base di ricarica senza passare da cucina", "RETURN_HOME", [], ["cucina"]),
        make_row("torna al punto iniziale senza passare da bagno e corridoio", "RETURN_HOME", [], ["bagno", "corridoio"]),
        make_row("rientra alla base evitando cucina, salone e bagno", "RETURN_HOME", [], ["cucina", "salone", "bagno"]),
        make_row("vai in carica evitando zona A, zona B e zona C", "RETURN_HOME", [], ["zona A", "zona B", "zona C"]),
    ]
    rows.extend(fixed_rows)
    for _ in range(80):
        areas = choose_distinct_areas(rng, 3)
        template = rng.choice(return_avoid_templates)
        text = template.format(avoid1=areas[0], avoid2=areas[1], avoid3=areas[2])
        rows.append(make_row(text, "RETURN_HOME", [], _used_avoids(template, areas)))
    return rows


def build_generalization_focus_rows() -> list[dict]:
    rows = []
    single_templates = [
        ("vai in {target}", "GO_TO_AREA"),
        ("vai a {target}", "GO_TO_AREA"),
        ("raggiungi {target}", "GO_TO_AREA"),
        ("spostati in {target}", "GO_TO_AREA"),
        ("spostati verso {target}", "GO_TO_AREA"),
        ("dirigiti verso {target}", "GO_TO_AREA"),
        ("pulisci {target}", "CLEAN_AREA"),
        ("aspira {target}", "CLEAN_AREA"),
        ("spolvera {target}", "CLEAN_AREA"),
        ("lava {target}", "CLEAN_AREA"),
        ("ripulisci {target}", "CLEAN_AREA"),
        ("fai una passata al {target}", "CLEAN_AREA"),
    ]
    avoid_templates = [
        ("vai in {target} evitando {avoid}", "GO_TO_AREA"),
        ("vai in {target} senza passare da {avoid}", "GO_TO_AREA"),
        ("pulisci {target} evitando {avoid}", "CLEAN_AREA"),
        ("aspira {target} senza passare da {avoid}", "CLEAN_AREA"),
    ]
    areas = TRAIN_ARTIFICIAL_AREAS + REALISTIC_AREAS
    for target in areas:
        for template, intent in single_templates:
            rows.append(make_row(template.format(target=target), intent, [target], []))
    for index, target in enumerate(TRAIN_ARTIFICIAL_AREAS):
        avoid = TRAIN_ARTIFICIAL_AREAS[(index + 1) % len(TRAIN_ARTIFICIAL_AREAS)]
        for template, intent in avoid_templates:
            text = template.format(target=target, avoid=avoid)
            rows.append(make_row(text, intent, [target], [avoid]))
    return rows


def build_unseen_rows() -> list[dict]:
    rows = [
        make_row("vai in gilgamesh", "GO_TO_AREA", ["gilgamesh"], []),
        make_row("vai in avalon", "GO_TO_AREA", ["avalon"], []),
        make_row("pulisci mordor", "CLEAN_AREA", ["mordor"], []),
        make_row("aspira narnia", "CLEAN_AREA", ["narnia"], []),
        make_row("vai in gilgamesh evitando mordor", "GO_TO_AREA", ["gilgamesh"], ["mordor"]),
        make_row("vai in avalon evitando mordor e narnia", "GO_TO_AREA", ["avalon"], ["mordor", "narnia"]),
        make_row("pulisci narnia evitando avalon", "CLEAN_AREA", ["narnia"], ["avalon"]),
        make_row("pulisci atlantide evitando olimpo e mordor", "CLEAN_AREA", ["atlantide"], ["olimpo", "mordor"]),
        make_row("vai in cucina evitando bagno, salone e mordor", "GO_TO_AREA", ["cucina"], ["bagno", "salone", "mordor"]),
        make_row("pulisci bagno evitando cucina e salone", "CLEAN_AREA", ["bagno"], ["cucina", "salone"]),
        make_row("pulisci cucina e bagno evitando salone e corridoio", "CLEAN_AREA", ["cucina", "bagno"], ["salone", "corridoio"]),
        make_row("vai in gilgamesh senza passare da mordor e avalon", "GO_TO_AREA", ["gilgamesh"], ["mordor", "avalon"]),
        make_row("vai in cucina", "GO_TO_AREA", ["cucina"], []),
        make_row("vai in bagno", "GO_TO_AREA", ["bagno"], []),
        make_row("pulisci cucina", "CLEAN_AREA", ["cucina"], []),
        make_row("aspira salone", "CLEAN_AREA", ["salone"], []),
        make_row("pulisci sala da pranzo evitando bagno", "CLEAN_AREA", ["sala da pranzo"], ["bagno"]),
        make_row("vai in camera ospiti evitando zona divano", "GO_TO_AREA", ["camera ospiti"], ["zona divano"]),
        make_row("fermati subito", "STOP_TASK", [], []),
        make_row("stop tutto", "STOP_TASK", [], []),
        make_row("alt", "STOP_TASK", [], []),
        make_row("blocca tutto", "STOP_TASK", [], []),
        make_row("annulla il comando", "STOP_TASK", [], []),
        make_row("42", "UNKNOWN", [], []),
        make_row("!!!", "UNKNOWN", [], []),
        make_row("ripeti", "UNKNOWN", [], []),
        make_row("vai", "UNKNOWN", [], []),
        make_row("torna", "UNKNOWN", [], []),
        make_row("ciao", "UNKNOWN", [], []),
        make_row("ciao come stai", "UNKNOWN", [], []),
        make_row("buongiorno", "UNKNOWN", [], []),
        make_row("grazie", "UNKNOWN", [], []),
        make_row("come va", "UNKNOWN", [], []),
        make_row("tutto bene", "UNKNOWN", [], []),
        make_row("il cielo è blu", "UNKNOWN", [], []),
        make_row("aspira la stanza delle armi", "CLEAN_AREA", ["stanza delle armi"], []),
        make_row("fai una passata al piano di sopra", "CLEAN_AREA", ["piano di sopra"], []),
        make_row("pulisci la sala dei giochi evitando zona del camino", "CLEAN_AREA", ["sala dei giochi"], ["zona del camino"]),
        make_row("spostati verso il bunker-7", "GO_TO_AREA", ["bunker-7"], []),
        make_row("raggiungi deposito evitando zona A, zona B e zona C", "GO_TO_AREA", ["deposito"], ["zona A", "zona B", "zona C"]),
        make_row("lava il garage", "CLEAN_AREA", ["garage"], []),
        make_row("spostati in officina evitando cucina, salotto e camino", "GO_TO_AREA", ["officina"], ["cucina", "salotto", "camino"]),
        make_row("vai in cucina evitando bagno, garage e armeria", "GO_TO_AREA", ["cucina"], ["bagno", "garage", "armeria"]),
        make_row("ritorna a casa", "RETURN_HOME", [], []),
        make_row("vai in base", "RETURN_HOME", [], []),
        make_row("vai nella base", "RETURN_HOME", [], []),
        make_row("torna alla base", "RETURN_HOME", [], []),
        make_row("rientra alla stazione di ricarica", "RETURN_HOME", [], []),
        make_row("vai a ricaricarti", "RETURN_HOME", [], []),
        make_row("ricarica la batteria", "RETURN_HOME", [], []),
        make_row("vai a caricare la batteria", "RETURN_HOME", [], []),
        make_row("torna alla base evitando cucina", "RETURN_HOME", [], ["cucina"]),
        make_row("vai in base evitando bagno e salone", "RETURN_HOME", [], ["bagno", "salone"]),
        make_row("rientra alla stazione di ricarica evitando cucina e corridoio", "RETURN_HOME", [], ["cucina", "corridoio"]),
        make_row("vai a ricaricarti evitando zona divano", "RETURN_HOME", [], ["zona divano"]),
        make_row("torna al punto iniziale senza passare da cucina e bagno", "RETURN_HOME", [], ["cucina", "bagno"]),
        make_row("quanto fa due più due", "UNKNOWN", [], []),
        make_row("ciao come stai", "UNKNOWN", [], []),
        make_row("cosa sai fare", "UNKNOWN", [], []),
        make_row("sì", "UNKNOWN", [], []),
        make_row("no", "UNKNOWN", [], []),
        make_row("ok", "UNKNOWN", [], []),
        make_row("ripeti", "UNKNOWN", [], []),
    ]
    forbidden = set(UNSEEN_AREAS)
    training_text = "\n".join(row["text"] for row in build_training_rows())
    leaked = [area for area in forbidden if area in training_text]
    if leaked:
        raise RuntimeError(f"Nomi unseen presenti nel training: {leaked}")
    return rows


def main() -> None:
    root = Path(__file__).resolve().parent
    train_path = root / "joint_nlu_train.jsonl"
    test_path = root / "joint_nlu_test_unseen_entities.jsonl"
    write_jsonl(train_path, build_training_rows())
    write_jsonl(test_path, build_unseen_rows())
    print(f"Scritto dataset training: {train_path}")
    print(f"Scritto dataset test unseen: {test_path}")


if __name__ == "__main__":
    main()
