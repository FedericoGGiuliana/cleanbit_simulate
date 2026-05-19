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

Per compatibilita con il Supervisor attuale, l'intent interno `START_MAPPING` viene pubblicato con:

```json
{
  "intent": "explore",
  "internal_intent": "START_MAPPING"
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

4. Il nodo `nlu_node` pubblica su `/nlp_intent` un JSON con `intent: "explore"` e `internal_intent: "START_MAPPING"`.

5. Il Supervisor riceve l'intent `explore` e avvia:

```bash
ros2 launch cleanbit_simulate mapping.launch.py
```

### 7. Training Classificatore NLU

```bash
cd ~/cleanbit_ws
python3 src/cleanbit_simulate/scripts/train_embedding_classifier.py
```

### 8. Dipendenze Python

```bash
python3 -m pip install --user joblib scikit-learn sentence-transformers spacy
python3 -m spacy download it_core_news_sm
```
