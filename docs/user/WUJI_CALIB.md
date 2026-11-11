# Wuji Hand 2 标定

本仓路径：Pico / XRoboToolkit 光学关键点 → `wuji_sdk.RetargetSession` → 20 关节。安装见 [../algorithms/OFFICIAL.md](../algorithms/OFFICIAL.md)。

## 安装与冒烟

```bash
./init.sh install   # 已含 wuji-sdk
python -c "from wuji_sdk import HandModel, Handedness, RetargetSession; RetargetSession.for_hand(HandModel.WujiHand2, side=Handedness.Right)"
```

算法与 I/O 说明：

- [Hand Retargeting](https://docs.wuji.tech/docs/en/wuji-sdk/latest/retargeting)
- [Retarget Session](https://docs.wuji.tech/docs/en/wuji-sdk/latest/sdk-practice/retarget-session)

## Pico 光学手势

输入需是 MediaPipe 顺序的 21 点（米）。本库在 `active=0`、掌三角形过小时 hold。`RetargetSession` 使用内置调参，不暴露 YAML overlay。

### 关键点预览（不跑 IK）

先停 `./run.sh vr-xrt` 和独立的 `python -m xr_hand_retarget`（同一 PC Service 只能一个 SDK 客户端）。

```bash
python -m xr_hand_retarget.preview --side right \
  --config xr_hand_retarget/configs/wuji_hand2.yaml
```

帮助文案：

```bash
python -m xr_hand_retarget.calibrate --config xr_hand_retarget/configs/wuji_hand2.yaml
```

## 与驱动的约定

`wujihand2_ros2_control` 吃 BJC `Float64MultiArray`，**按下标**。`hand.joint_names` 必须与 firmware finger-major（thumb..pinky × 4）一致，与 `RetargetSession.step` 输出对齐。
