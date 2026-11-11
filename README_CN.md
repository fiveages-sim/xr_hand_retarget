# XR 手部重定向

一个用于把光学手势转化为灵巧手控制指令的工具库。

光学关键点（MediaPipe 点序）→ 各灵巧手后端 → 关节 `q`（经 ROS 发给控制器）。换手只改配置，不必改代码。腕 / 头显 EE 仍在 [`vr_pose_publisher`](https://github.com/fiveages-sim/vr_pose_publisher)；本包是 fa-py 栈里的手映射层。

English: [README.md](README.md)

## 功能特性

- 🖐️ 光学 OpenXR / XRoboToolkit 手部关键点 → 多手型重定向
- 🤖 多种灵巧手共用一个配置开关（`hands.type`）
- 🔄 可插拔后端：vector（XHand1）、`wuji-sdk` RetargetSession、PalmTip curl（Linker）
- 📡 异步发布 `q_des`，带 LPF + 速度限制，改善遥操顺畅度
- 🧭 人 → 标准手 → 机器人的标定链（MediaPipe 21 点）
- ⚙️ 本机旋钮写在 `configs/local.yaml`；产品默认留在包内

## 支持的手型

| `hands.type` | 映射方式 | 标定 |
|--------------|----------|------|
| `xhand1` | 键向量（vector） | [CURL_CALIB](docs/user/CURL_CALIB.md) |
| `wuji` | `wuji-sdk` RetargetSession | [WUJI_CALIB](docs/user/WUJI_CALIB.md) · [OFFICIAL](docs/algorithms/OFFICIAL.md) |
| `o6` / `l6` / `o7` | PalmTip curl | [LINKER_CALIB](docs/user/LINKER_CALIB.md) |
| `none`（仅 env / CLI） | — | 仅光学腕 EE，不启灵巧手 |

`wuji-sdk` 已写在本包依赖里，随 `./init.sh install` 安装。

---

## 安装

### 推荐：fa-py-libraries 根目录

若本仓库作为 `fa-py-libraries` 子模块使用：

```bash
./init.sh install
cp configs/local.yaml.example configs/local.yaml   # 改 hands.type
```

安装参数与用户层白名单见 [docs/user/SWITCH.md](docs/user/SWITCH.md)。

### 本仓库单独使用

```bash
cd ~/libraries/xr_hand_retarget   # 或 fa-py-libraries 内路径
pip install -e .
# 可选（XHand1 vector 求解）：
pip install -e '.[vector]'
```

将安装：

- `numpy<2.0.0` — 数值计算
- `pyyaml` — 配置解析
- `wuji-sdk>=2026.7.21` — Wuji Hand 2 RetargetSession
- `scipy>=1.10` — 可选，vector 后端

---

## 使用方法

### 快速开始（推荐：fa-py-libraries 根目录）

同一 XRoboToolkit PC Service 只能有一个 SDK 客户端。跑 `./run.sh vr-xrt` 时不要再开独立的 `xr_hand_retarget` 进程。

```bash
# 光学腕 EE + 灵巧手
./run.sh vr-xrt wrist
```

临时换手（不会把 `none` 写入 `local.yaml`）：

```bash
FA_HAND=wuji ./run.sh vr-xrt wrist
FA_HAND=none ./run.sh vr-xrt wrist                 # 只要腕
./run.sh vr-xrt wrist --no-hands                   # 同 none
```

持久选手型：改 `configs/local.yaml`：

```yaml
hands:
  source: xrt
  type: xhand1    # xhand1 | wuji | o6 | l6 | o7
```

### 快速开始（本仓库单独使用）

```bash
# 例：Wuji 光学路径（PC Service 已启动；勿与 vr-xrt 并行）
python -m xr_hand_retarget --config configs/wuji_hand2.yaml --side right
```

安装后的 CLI：

| 命令 | 作用 |
|------|------|
| `xr-hand-retarget` | 在线重定向节点 |
| `xr-hand-calibrate` | 标定辅助 |
| `xr-xhand1-*` | 旧名别名（同一入口） |

### 标定与顺畅度

1. 按上表对手型做标定。
2. 跟手感通过 `command.filter_cutoff_hz` / `command.max_velocity` 调节 — 见 [SMOOTHNESS](docs/user/SMOOTHNESS.md)。
3. 可选探针（在 fa-py 根目录）：

```bash
python3 scripts/teleop_probe.py --sec 5 --csv /tmp/hand.csv
```

### 典型控制流程

1. 启动 XRoboToolkit PC Service + 头显 App（见 `vr_pose_publisher` README）。
2. 在 `configs/local.yaml` 设置 `hands.type`。
3. 运行 `./run.sh vr-xrt wrist`。
4. 按 VR 侧惯例进入遥操 FSM / UPDATE；手部 `q` 跟随光学关键点。

---

## 架构

```
光学源（XRT OpenXR / …）
    ↓
HandFrame — MediaPipe 21 点（米），腕原点
    ↓ T_person（users/<id>.yaml）
标准手 xyz (21, 3)
    ↓ T_robot + 后端求解
灵巧手 q（XHand1 / Wuji 20 / Linker O6·L6·O7）
    ↓ OnlineCommandFilter @ publish_hz
ROS q_des → 控制器
```

| 层 | 负责 | 不负责 |
|----|------|--------|
| `vr_pose_publisher` | 头显 / 腕 `/teleop/*`、FSM、bag | 灵巧手 IK、人骨长 |
| `xr_hand_retarget` | 21 点 → `q` | 臂笛卡尔、Pico Input 模式 |

边界说明：[docs/dev/PIPELINE.md](docs/dev/PIPELINE.md)。

### 文件结构

```
xr_hand_retarget/
├── pyproject.toml
├── README.md / README_CN.md
├── configs/                 # 手型索引、hands/、calib/、users/
├── assets/                  # URDF（+ cspace）
├── docs/
│   ├── user/                # 换手、标定、顺畅度
│   ├── dev/                 # 配置分层、异步发布、布局
│   └── algorithms/          # method 对照、官方 Wuji
└── xr_hand_retarget/
    ├── sources/             # XRT / landmarks → HandFrame
    ├── backends/            # xhand1 / wuji / linker
    ├── algorithms/          # vector、curl、collision、…
    ├── control/             # filter、gate、safety
    ├── ipc/                 # 异步 retarget worker
    ├── node.py / dual_node.py
    └── calibrate.py / preview.py
```

---

## 文档

| 目录 | 内容 |
|------|------|
| [docs/user/](docs/user/) | 换手、标定、遥操旋钮 |
| [docs/dev/](docs/dev/) | 配置分层、异步发布、布局 |
| [docs/algorithms/](docs/algorithms/) | 各手型 method |

---

## 故障排除

### 腕 EE 正常但手不动
1. 确认当前不是 `none`（检查 `FA_HAND` / `--no-hands`）。
2. 检查 FSM / gate：仅在允许状态下发令 — [COMMAND_SAFETY](docs/dev/COMMAND_SAFETY.md)。
3. 确认头显正在追踪手部关键点。

### Wuji / XRT「已连接」或帧为空
同一 PC Service 只能一个客户端。重试前停掉多余的 `vr-xrt` 或 `python -m xr_hand_retarget`。

### 手指发涩或拖尾
先调 `configs/local.yaml` 里的 `filter_cutoff_hz` 与 `max_velocity`，不要追 EE Hz。协议见 [SMOOTHNESS](docs/user/SMOOTHNESS.md)。

### 导入失败 / 缺少 wuji-sdk
在 fa-py-libraries 重跑 `./init.sh install`，或在本包内 `pip install -e .`，确保装上 `wuji-sdk`。
