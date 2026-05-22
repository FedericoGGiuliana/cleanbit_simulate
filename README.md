# cleanbit_simulate

Package ROS 2 Humble per la simulazione Cleanbit con Gazebo, SLAM Toolbox, Nav2, explore_lite e Supervisor.

## Avvio E Test

### 1. Build Workspace

```bash
cd ~/cleanbit_ws
colcon build
source install/setup.bash
```

### 2. Avvio Simulazione Idle Con Supervisor

```bash
ros2 launch cleanbit_simulate idle.launch.py
```

### 3. Avvio Nodo NLU

In un nuovo terminale:

```bash
cd ~/cleanbit_ws
source install/setup.bash
ros2 run cleanbit_simulate nlu_node
```

Il modulo NLU integrato in `cleanbit_simulate` legge comandi testuali da `/nlu/input_text` e pubblica JSON strutturato su `/nlp_intent`.

Esempio di output per `mappa la casa`:

```json
{
  "source": "cleanbit_nlu",
  "version": "1.0",
  "original_text": "mappa la casa",
  "intent": {
    "name": "START_MAPPING",
    "confidence": 0.75,
    "requires_clarification": false
  },
  "command": {
    "action": "map",
    "targets": [],
    "constraints": {
      "avoid": []
    }
  },
  "dialogue": {
    "state": "COMMAND_READY",
    "message": "Comando interpretato correttamente.",
    "question": null,
    "expected_replies": []
  }
}
```

### 4. Test Comando Testuale

In un nuovo terminale:

```bash
cd ~/cleanbit_ws
source install/setup.bash
ros2 topic pub --once /nlu/input_text std_msgs/msg/String "{data: 'mappa la casa'}"
```

### 5. Echo Output NLU

```bash
ros2 topic echo /nlp_intent --full-length
```

### 6. Test Mappatura Completa

1. Avvia la simulazione idle con Supervisor:

```bash
ros2 launch cleanbit_simulate idle.launch.py
```

2. Avvia il nodo NLU:

```bash
ros2 run cleanbit_simulate nlu_node
```

3. Pubblica il comando testuale:

```bash
ros2 topic pub --once /nlu/input_text std_msgs/msg/String "{data: 'mappa la casa'}"
```

4. Il nodo `nlu_node` pubblica su `/nlp_intent` un JSON con `intent.name: "START_MAPPING"` e `command.action: "map"`.

5. Nota: il Supervisor attuale potrebbe richiedere un aggiornamento per leggere il nuovo schema JSON `1.0` prima di avviare automaticamente:

```bash
ros2 launch cleanbit_simulate mapping.launch.py
```

### 7. Training Intent Classifier

```bash
cd ~/cleanbit_ws
python3 src/cleanbit_simulate/cleanbit_simulate/nlu/intent/train_intent_classifier.py
```

### 8. Training Slot Filler

```bash
cd ~/cleanbit_ws
python3 src/cleanbit_simulate/cleanbit_simulate/nlu/slots/train_slot_filler.py
```

### 9. Test Slot Filler

```bash
cd ~/cleanbit_ws
python3 src/cleanbit_simulate/cleanbit_simulate/nlu/tests/test_slot_filler.py
```

### 10. Terminale NLU

Con `nlu_node` gia avviato:

```bash
ros2 run cleanbit_simulate nlu_terminal
```

### 11. Dipendenze Python

```bash
python3 -m pip install --user joblib scikit-learn sentence-transformers spacy
python3 -m spacy download it_core_news_sm
```
