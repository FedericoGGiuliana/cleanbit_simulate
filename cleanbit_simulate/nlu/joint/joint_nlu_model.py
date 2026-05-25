from __future__ import annotations

import torch
from torch import nn


BERTINO_MODEL_NAME = "indigo-ai/BERTino"


class JointNLUModel(nn.Module):
    def __init__(
        self,
        num_intents: int,
        num_slot_labels: int,
        model_name: str = BERTINO_MODEL_NAME,
        dropout: float = 0.1,
    ) -> None:
        super().__init__()
        from transformers import AutoModel

        self.encoder = AutoModel.from_pretrained(model_name)
        hidden_size = self.encoder.config.hidden_size
        self.dropout = nn.Dropout(dropout)
        self.intent_classifier = nn.Linear(hidden_size, num_intents)
        self.slot_classifier = nn.Linear(hidden_size, num_slot_labels)

    def forward(
        self,
        input_ids: torch.Tensor,
        attention_mask: torch.Tensor,
        token_type_ids: torch.Tensor | None = None,
        intent_labels: torch.Tensor | None = None,
        slot_labels: torch.Tensor | None = None,
    ) -> dict[str, torch.Tensor | None]:
        outputs = self.encoder(input_ids=input_ids, attention_mask=attention_mask)
        sequence_output = self.dropout(outputs.last_hidden_state)
        pooled_output = self.dropout(outputs.last_hidden_state[:, 0])

        intent_logits = self.intent_classifier(pooled_output)
        slot_logits = self.slot_classifier(sequence_output)

        loss = None
        if intent_labels is not None and slot_labels is not None:
            intent_loss = nn.CrossEntropyLoss()(intent_logits, intent_labels)
            slot_loss = nn.CrossEntropyLoss(ignore_index=-100)(
                slot_logits.view(-1, slot_logits.shape[-1]),
                slot_labels.view(-1),
            )
            loss = intent_loss + slot_loss

        return {
            "loss": loss,
            "intent_logits": intent_logits,
            "slot_logits": slot_logits,
        }
