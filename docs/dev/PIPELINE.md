# 手部映射分层与仓库边界

目标：`source → 标准手 21 点 → 灵巧手 q`。  
人只标定到标准手；灵巧手只标定一次到标准手。VR 是一种 source，不是映射核心。

## 1. 运行时分层

```
┌─────────────────────────────────────────────────────────┐
│  sources（可插拔）                                         │
│  xrt OpenXR26 │ dexcap │ wuji_glove │ replay              │
└──────────────────────────┬──────────────────────────────┘
                           ▼
┌─────────────────────────────────────────────────────────┐
│  HandFrame（契约，无 ROS、无厂商 SDK）                     │
│  xyz (21,3) m, MediaPipe 点序, wrist 原点, active         │
│  T_person → 标准手（users/<id>.yaml）                      │
└──────────────────────────┬──────────────────────────────┘
                           ▼
┌─────────────────────────────────────────────────────────┐
│  robots（每手一份 yaml + URDF + 求解器）                   │
│  wuji: official │ xhand1: vector │ o6/l6/o7: curl          │
│  T_robot 在 hands/<type>.yaml                             │
└──────────────────────────┬──────────────────────────────┘
                           ▼
              ROS Float64MultiArray / 其它 sink
```

禁止：source 直接出目标机器人 q；把 Wuji **20 维关节**当中间层；把 `segment_scaling` 和人焊在同一份 overlay 里。  
标准手是 **Wuji 21 点**（MediaPipe 点序，见 §4），不是 20-DOF。

## 2. 仓库边界

`xr_hand_retarget` 已是独立仓，经 `.gitmodules` 挂进 `fa-py-libraries`（`./init.sh submodules`）。VR 产品仍在本聚合仓的 `vr_pose_publisher`。

| | VR（`vr_pose_publisher`） | 手映射（`xr_hand_retarget`） |
|--|---------------------------|------------------------------|
| 负责 | 头显/腕 `/teleop/*`、FSM、bag | 21 点 → q |
| 不负责 | 灵巧手 IK、人骨长 | 臂笛卡尔、Pico Input 模式 |

`./run.sh vr-hand` / `vr-xrt wrist` = XRT source + 腕 EE + `DualHandRetargetNode`。  
手套/DexCap：`python -m xr_hand_retarget`（勿与 `vr-xrt` 同开：PC Service 单客户端）。

目录约定见 [LAYOUT.md](LAYOUT.md)；method 表见 [../algorithms/METHODS.md](../algorithms/METHODS.md)。

## 3. 里程碑（摘要）

| 状态 | 项 | 说明 |
|------|-----|------|
| 已落地 | **P0** 契约 | `HandFrame`；`step(frame)`；source 与 backend 解耦 |
| 已落地 | **P1** 配置 | `standard_hand` / `users` / `hands` / `local.yaml` → [CONFIG.md](CONFIG.md) |
| 进行中 | **P1b** EE⊥hand | 异步发布；红线与验收 → [ASYNC_TELEOP.md](ASYNC_TELEOP.md) |
| 已落地 | **P2** T_xhand | URDF 限位/捏合槽；`txhand` CLI → [TXHAND.md](TXHAND.md) |
| 下一 | **P3** 多源 | 每 source 实现 `HandSource.start/read/close` |

验证命令见 [RUN.md](RUN.md)。

## 4. 标准手 = Wuji 21（不是 20-DOF）

标准手是 **21 点笛卡尔**（与 wuji-sdk / 光学手套同一套），不是 Hand 2 的 20 个主动关节。

```
VR 26 / 手套 / DexCap  →  T_person（users/*.yaml）
                       →  标准手 xyz (21,3)     ← 用户只标定到这里
                       →  T_robot + attract
                       →  Wuji 20 / O6 / O7 / XHand1 q
```

- **21 点**覆盖指尖、骨方向、侧摆；20-DOF 是某一只机器人的命令，不能当契约。
- 捏合吸引属于 **T_robot**，不要写在 VR 原始 26 点或 20 轴 q 上当「标准」。
- 光学换视角：pose 用判定域（lo/hi），不要把 OpenXR 26 当标定文件。
