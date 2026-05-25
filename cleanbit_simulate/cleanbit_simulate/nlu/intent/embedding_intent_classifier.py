from __future__ import annotations

from pathlib import Path

from ..command_schema import INTERNAL_INTENTS


MODEL_NAME = "paraphrase-multilingual-MiniLM-L12-v2"


class EmbeddingIntentClassifier:
    def __init__(self, model_path: str | None = None, logger=None) -> None:
        self.logger = logger
        self.model_path = Path(model_path) if model_path else self._default_model_path()
        self.embedding_model = None
        self.classifier = None
        self.labels: list[str] | None = None
        self._load()

    def classify(self, text: str) -> tuple[str, float]:
        if not text.strip():
            return "UNKNOWN", 0.0

        if self.embedding_model is not None and self.classifier is not None:
            embedding = self.embedding_model.encode([text])
            if hasattr(self.classifier, "predict_proba"):
                probabilities = self.classifier.predict_proba(embedding)[0]
                best_index = int(probabilities.argmax())
                label = self._label_for_index(best_index)
                return self._supported_label(label), float(probabilities[best_index])

            label = str(self.classifier.predict(embedding)[0])
            return self._supported_label(label), 0.7

        return self._keyword_fallback(text)

    def _load(self) -> None:
        try:
            from joblib import load
            from sentence_transformers import SentenceTransformer
        except ImportError as exc:
            self._warn(f"Dipendenze embedding non disponibili, uso fallback keyword: {exc}")
            return

        if not self.model_path.exists():
            self._warn(f"Modello intent non trovato in {self.model_path}, uso fallback keyword")
            return

        self.embedding_model = SentenceTransformer(MODEL_NAME)
        artifact = load(self.model_path)
        if isinstance(artifact, dict):
            self.classifier = artifact.get("classifier")
            labels = artifact.get("labels")
            self.labels = list(labels) if labels else None
        else:
            self.classifier = artifact
            self.labels = list(getattr(artifact, "classes_", [])) or None

        self._info(f"Classificatore intent caricato da {self.model_path}")

    def _keyword_fallback(self, text: str) -> tuple[str, float]:
        normalized = text.lower().strip()

        if any(word in normalized for word in ("mappa", "esplora", "scansiona")):
            return "START_MAPPING", 0.75
        if any(phrase in normalized for phrase in ("pulisci", "aspira", "lava", "spolvera", "dai una passata", "fai una pulita", "ripulisci", "sistema")):
            return "CLEAN_AREA", 0.68
        if any(phrase in normalized for phrase in ("vai", "raggiungi", "portati", "spostati")):
            return "GO_TO_AREA", 0.68
        if any(phrase in normalized for phrase in ("torna alla base", "torna a casa", "ritorna alla base")):
            return "RETURN_HOME", 0.7
        if any(phrase in normalized for phrase in ("stato", "cosa stai facendo", "a che punto")):
            return "STATUS_REQUEST", 0.7
        if any(phrase in normalized for phrase in ("aiuto", "help", "cosa posso dire")):
            return "HELP_REQUEST", 0.72
        if normalized in {"si", "sì", "ok", "confermo", "va bene", "procedi", "esatto", "corretto", "fallo", "conferma"}:
            return "CONFIRM", 0.72
        if normalized in {"no", "annulla", "non confermo", "lascia stare", "non farlo", "negativo", "sbagliato", "non va bene", "rifiuto"}:
            return "DENY", 0.72

        return "UNKNOWN", 0.35

    def _supported_label(self, label: str) -> str:
        if label in INTERNAL_INTENTS:
            return label
        self._warn(f"Intent non supportato dal codice corrente: {label}. Uso UNKNOWN")
        return "UNKNOWN"

    def _label_for_index(self, index: int) -> str:
        if self.labels:
            return str(self.labels[index])
        classes = getattr(self.classifier, "classes_", INTERNAL_INTENTS)
        return str(classes[index])

    def _default_model_path(self) -> Path:
        candidates = []
        try:
            from ament_index_python.packages import get_package_share_directory

            candidates.append(
                Path(get_package_share_directory("cleanbit_simulate"))
                / "models"
                / "intent_classifier.joblib"
            )
        except Exception:
            pass

        candidates.extend(
            [
                Path(__file__).resolve().parents[3] / "models" / "intent_classifier.joblib",
                Path("~/cleanbit_ws/src/cleanbit_simulate/models/intent_classifier.joblib").expanduser(),
            ]
        )

        for candidate in candidates:
            if candidate.exists():
                return candidate
        return candidates[-1]

    def _info(self, message: str) -> None:
        if self.logger:
            self.logger.info(message)

    def _warn(self, message: str) -> None:
        if self.logger:
            self.logger.warning(message)
