# cleanbit_simulate

ROS 2 simulation package for the **Cleanbit** autonomous cleaning robot.

> This repository contains the simulation stack for Cleanbit. For hardware specifications, CAD renders, real-world photos and videos, and the full robot control stack, refer to the **[main Cleanbit repository](https://github.com/FedericoGGiuliana/cleanbit_control)**.

---

## Overview

`cleanbit_simulate` provides a full simulation environment for Cleanbit using Gazebo Ignition, and implements an **NLP-driven autonomous behaviour architecture** currently under development as part of the course **Artificial Intelligence for Robotics** at the **University of Palermo**.

The architecture allows a user to control the robot through natural language commands (Italian). These are interpreted by an on-board NLU module and dispatched by a Supervisor node to the appropriate autonomous behaviour — mapping, navigation, or cleaning.

```
User (text) → NLU Node → /nlp_intent → Supervisor → Behaviour Launchers
                                                   ↘ Nav2 Action Clients
```

---

## Architecture

| Component | Description |
|---|---|
| `nlu_node` | Interprets natural language input and publishes structured JSON intents |
| `supervisor.py` | Reads intents and dispatches to the correct behaviour |
| `mapping.launch.py` | SLAM Toolbox + Nav2 + explore_lite for autonomous mapping |
| `navigation.launch.py` | map_server + AMCL + Nav2 for navigation on a saved map |
| `map_manager_node.py` | Detects end of exploration, saves the map, launches the room editor |
| `room_editor.py` | GUI tool to draw and name rooms on the saved map |
| `navigation_manager.py` | Converts room names to Nav2 waypoints, manages avoid zones |

---

## Supported Intents

| Intent | Example command | Behaviour |
|---|---|---|
| `START_MAPPING` | *"mappa la casa"* | Launches autonomous exploration and mapping |
| `GO_TO_AREA` | *"vai in cucina"* | Navigates to the named room |
| `CLEAN_AREA` | *"pulisci il soggiorno evitando la cucina"* | Navigates and cleans the named room avoiding desired rooms in the path|

---

## Getting Started

### 1. Build

```bash
cd ~/cleanbit_ws
colcon build
source install/setup.bash
```

### 2. Launch Simulation (Idle + Supervisor)

```bash
ros2 launch cleanbit_simulate idle.launch.py
```

### 3. Launch NLU Node

```bash
# In a new terminal
source ~/cleanbit_ws/install/setup.bash
ros2 run cleanbit_simulate nlu_node
```

### 4. Send a Text Command

```bash
ros2 topic pub --once /nlu/input_text std_msgs/msg/String "{data: 'mappa la casa'}"
```

### 5. Monitor NLU Output

```bash
ros2 topic echo /nlp_intent --full-length
```

---

## Mapping Workflow

1. Launch idle simulation and supervisor
2. Launch the NLU node
3. Send the mapping command — the supervisor automatically starts `mapping.launch.py`
4. explore_lite autonomously explores the environment
5. When exploration is complete, the map is saved and the **Room Editor** opens
6. Draw and name rooms on the map — coordinates are saved to `rooms.json`
7. The robot is now ready for room-level navigation and cleaning

---

## Python Dependencies

```bash
python3 -m pip install --user joblib scikit-learn sentence-transformers spacy
python3 -m spacy download it_core_news_sm
```

---

## NLU Training

```bash
# Train intent classifier
python3 src/cleanbit_simulate/cleanbit_simulate/nlu/intent/train_intent_classifier.py

# Train slot filler
python3 src/cleanbit_simulate/cleanbit_simulate/nlu/slots/train_slot_filler.py

# Test slot filler
python3 src/cleanbit_simulate/cleanbit_simulate/nlu/tests/test_slot_filler.py
```

---

## Interactive NLU Terminal

With `nlu_node` already running:

```bash
ros2 run cleanbit_simulate nlu_terminal
```

---

## Related

- [**Cleanbit main repository**](https://github.com/FedericoGGiuliana/cleanbit_control) — hardware, control stack, renders, and real-world demos
- **Course**: Artificial Intelligence for Robotics — University of Palermo
