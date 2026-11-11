# XR Hand Retarget

A toolkit that turns optical hand tracking into dexterous-hand joint commands.

Optical landmarks (MediaPipe order) → hand backends → joint `q` (published over ROS to the controller). Swap hands by config, not by code. Wrist / headset EE stay in [`vr_pose_publisher`](https://github.com/fiveages-sim/vr_pose_publisher); this package is the hand-mapping layer in the fa-py stack.

中文版：[README_CN.md](README_CN.md)

## Features

- 🖐️ Optical OpenXR / XRoboToolkit hand landmarks → multi-hand retarget
- 🤖 Multiple dexterous hands behind one config switch (`hands.type`)
- 🔄 Pluggable backends: vector (XHand1), `wuji-sdk` RetargetSession, PalmTip curl (Linker)
- 📡 Async `q_des` publish with LPF + velocity limit for smooth teleop
- 🧭 Person → standard-hand → robot calibration chain (21 MediaPipe points)
- ⚙️ Local knobs in `configs/local.yaml`; product defaults stay in the package

## Supported Hands

| `hands.type` | Method | Calibration |
|--------------|--------|-------------|
| `xhand1` | Key-vector (vector) | [CURL_CALIB](docs/user/CURL_CALIB.md) |
| `wuji` | `wuji-sdk` RetargetSession | [WUJI_CALIB](docs/user/WUJI_CALIB.md) · [OFFICIAL](docs/algorithms/OFFICIAL.md) |
| `o6` / `l6` / `o7` | PalmTip curl | [LINKER_CALIB](docs/user/LINKER_CALIB.md) |
| `none` (env / CLI only) | — | Wrist EE only; no dexterous hand |

`wuji-sdk` is a hard dependency of this package and installs with `./init.sh install`.

---

## Installation

### Recommended: fa-py-libraries root

When this repo is used as a `fa-py-libraries` submodule:

```bash
./init.sh install
cp configs/local.yaml.example configs/local.yaml   # set hands.type
```

Install details and the user-layer parameter whitelist: [docs/user/SWITCH.md](docs/user/SWITCH.md).

### Standalone (this repo alone)

```bash
cd ~/libraries/xr_hand_retarget   # or the path inside fa-py-libraries
pip install -e .
# optional (XHand1 vector solver):
pip install -e '.[vector]'
```

This installs:

- `numpy<2.0.0` — numerics
- `pyyaml` — config
- `wuji-sdk>=2026.7.21` — Wuji Hand 2 RetargetSession
- `scipy>=1.10` — optional, for the vector backend

---

## Usage

### Quick start (recommended: fa-py-libraries root)

Same XRoboToolkit PC Service may have only **one** SDK client. While `./run.sh vr-xrt` is running, do not start a separate `xr_hand_retarget` process.

```bash
# Optical wrist EE + dexterous hand
./run.sh vr-xrt wrist
```

Temporary hand switch (does not write `none` into `local.yaml`):

```bash
FA_HAND=wuji ./run.sh vr-xrt wrist
FA_HAND=none ./run.sh vr-xrt wrist                 # wrist only
./run.sh vr-xrt wrist --no-hands                   # same as none
```

Persistent hand choice: edit `configs/local.yaml`:

```yaml
hands:
  source: xrt
  type: xhand1    # xhand1 | wuji | o6 | l6 | o7
```

### Quick start (this repo alone)

```bash
# Example: Wuji optical path (PC Service already running; no parallel vr-xrt)
python -m xr_hand_retarget --config configs/wuji_hand2.yaml --side right
```

CLI entry points after install:

| Command | Role |
|---------|------|
| `xr-hand-retarget` | Live retarget node |
| `xr-hand-calibrate` | Calibration helpers |
| `xr-xhand1-*` | Legacy aliases (same entry points) |

### Calibration & smoothness

1. Calibrate for the selected hand (table above).
2. Tune follow feel via `command.filter_cutoff_hz` / `command.max_velocity` — see [SMOOTHNESS](docs/user/SMOOTHNESS.md).
3. Optional probe from the fa-py root:

```bash
python3 scripts/teleop_probe.py --sec 5 --csv /tmp/hand.csv
```

### Typical control flow

1. Start XRoboToolkit PC Service + headset app (see `vr_pose_publisher` README).
2. Set `hands.type` in `configs/local.yaml`.
3. Run `./run.sh vr-xrt wrist`.
4. Enter teleop FSM / UPDATE from the VR side as usual; hand `q` follows optical landmarks.

---

## Architecture

```
Optical source (XRT OpenXR / …)
    ↓
HandFrame — 21 MediaPipe landmarks (m), wrist origin
    ↓ T_person (users/<id>.yaml)
Standard hand xyz (21, 3)
    ↓ T_robot + backend solver
Dexterous hand q  (XHand1 / Wuji 20 / Linker O6·L6·O7)
    ↓ OnlineCommandFilter @ publish_hz
ROS q_des → controller
```

| Layer | Owns | Does not own |
|-------|------|--------------|
| `vr_pose_publisher` | Headset / wrist `/teleop/*`, FSM, bag | Dexterous IK, bone lengths |
| `xr_hand_retarget` | 21 points → `q` | Arm Cartesian, Pico Input modes |

Boundary notes: [docs/dev/PIPELINE.md](docs/dev/PIPELINE.md).

### File structure

```
xr_hand_retarget/
├── pyproject.toml
├── README.md / README_CN.md
├── configs/                 # hand indexes, hands/, calib/, users/
├── assets/                  # URDF (+ cspace)
├── docs/
│   ├── user/                # switch, calib, smoothness
│   ├── dev/                 # config layers, async, layout
│   └── algorithms/          # method map, official Wuji
└── xr_hand_retarget/
    ├── sources/             # XRT / landmarks → HandFrame
    ├── backends/            # xhand1 / wuji / linker
    ├── algorithms/          # vector, curl, collision, …
    ├── control/             # filter, gate, safety
    ├── ipc/                 # async retarget worker
    ├── node.py / dual_node.py
    └── calibrate.py / preview.py
```

---

## Documentation

| Path | Content |
|------|---------|
| [docs/user/](docs/user/) | Hand switch, calibration, teleop knobs |
| [docs/dev/](docs/dev/) | Config layers, async publish, layout |
| [docs/algorithms/](docs/algorithms/) | Per-hand methods |

---

## Troubleshooting

### Hand not moving while wrist EE works
1. Confirm `hands.type` is not effectively `none` (`FA_HAND` / `--no-hands`).
2. Check FSM / gate: commands only publish in allowed states — [COMMAND_SAFETY](docs/dev/COMMAND_SAFETY.md).
3. Ensure landmarks are active (headset tracking the hand).

### Wuji / XRT “already connected” or empty frames
Only one client may use the XRoboToolkit PC Service. Stop duplicate `vr-xrt` or `python -m xr_hand_retarget` processes before retrying.

### Jerky or laggy fingers
Tune `filter_cutoff_hz` and `max_velocity` in `configs/local.yaml` first; do not chase EE Hz. Protocol: [SMOOTHNESS](docs/user/SMOOTHNESS.md).

### Import / missing wuji-sdk
Re-run `./init.sh install` from fa-py-libraries, or `pip install -e .` inside this package so `wuji-sdk` is present.
