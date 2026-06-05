# cleanbit_simulate

ROS 2 simulation package for the **Cleanbit** autonomous cleaning robot.

> This repository contains the simulation stack for Cleanbit. For hardware specifications, CAD renders, real-world photos and videos, and the full robot control stack, refer to the **[main Cleanbit repository](https://github.com/FedericoGGiuliana/cleanbit_control)**.

---

## Overview

`cleanbit_simulate` provides a full simulation environment for Cleanbit using Gazebo Ignition, and implements an **NLP-driven autonomous behaviour architecture** currently under development as part of the course **Artificial Intelligence for Robotics** at the **University of Palermo**.

The architecture allows a user to control the robot through natural language commands (Italian). These are interpreted by an on-board NLU module and dispatched by a Supervisor node to the appropriate autonomous behaviour.

```
User (text) → NLU Node → /nlp_intent → Supervisor → Behaviour Launchers / Nav2 Action Clients
```

---

## Architecture

| Component | Description |
|---|---|
| `nlu_node` | Joint BERTino-based NLU — classifies intent and extracts slots in a single pass |
| `supervisor.py` | Reads structured intents and dispatches to the correct behaviour |
| `mapping.launch.py` | SLAM Toolbox + Nav2 + explore_lite for autonomous mapping |
| `navigation.launch.py` | map_server + AMCL + Nav2 for navigation on a saved map |
| `map_manager_node.py` | Detects end of exploration, saves the map, launches the room editor |
| `room_editor.py` | GUI tool to draw and name rooms on the saved map |
| `navigation_manager.py` | Converts room names to Nav2 waypoints, manages keepout zones |

---

## NLU Module

The NLU module is based on **BERTino** (`indigo-ai/BERTino`), an Italian DistilBERT model fine-tuned on robot command data. It performs **joint intent classification and slot filling** in a single forward pass — both tasks share the same encoder representation.

**Supported intents:**

| Intent | Example command |
|---|---|
| `START_MAPPING` | *"mappa la casa"* |
| `GO_TO_AREA` | *"vai in cucina"* |
| `CLEAN_AREA` | *"pulisci il soggiorno evitando il bagno"* |
| `RETURN_HOME` | *"torna alla base"* |
| `STOP_TASK` | *"fermati"* |
| `UNKNOWN` | anything unrecognised |

**Extracted slots:** `targets` (areas to reach or clean), `avoid` (areas to avoid).

---

## Getting Started

### 1. Build

```bash
cd ~/cleanbit_ws
colcon build --symlink-install
source install/setup.bash
```

### 2. Train the NLU model

This step is required before running the system for the first time.

```bash
python3 src/cleanbit_simulate/cleanbit_simulate/nlu/joint/train_joint_nlu.py
```

### 3. Launch the simulation

```bash
ros2 launch cleanbit_simulate idle.launch.py
```

### 4. Launch the GUI

```bash
python3 src/cleanbit_simulate/cleanbit_simulate/pyqt_gui_interface.py
```

---

## Mapping Workflow

1. Launch the simulation and GUI
2. Send a mapping command — the supervisor automatically starts `mapping.launch.py`
3. explore_lite autonomously explores the environment
4. When exploration is complete, the map is saved and the **Room Editor** opens
5. Draw and name rooms on the map — coordinates are saved to `rooms.json`
6. The robot is now ready for room-level navigation and cleaning

---

## Python Dependencies

```bash
python3 -m pip install --user torch transformers
```

---

## Related

- **[Cleanbit main repository](https://github.com/FedericoGGiuliana/cleanbit_control)** — hardware, control stack, renders, and real-world demos.
- **Course**: Artificial Intelligence for Robotics — University of Palermo
