# Wuji Hand 2 标定

生产路径：`wuji_sdk.RetargetSession`（builtin Hand2 IK）。安装见 [../algorithms/OFFICIAL.md](../algorithms/OFFICIAL.md)。

## 安装与冒烟

```bash
./init.sh install   # 已含 wuji-sdk
python -c "from wuji_sdk import HandModel, Handedness, RetargetSession; RetargetSession.for_hand(HandModel.WujiHand2, side=Handedness.Right)"
```

## 手套

按官方 SDK 用户与标定流程（Studio / CLI / `wuji_glove` 示例），再跑 SDK 仓库示例：

```bash
pip install wuji-sdk numpy
# wuji-sdk repo → examples/python/retargeting/1.teleop_real.py
```

文档：

- [Hand Retargeting](https://docs.wuji.tech/docs/en/wuji-sdk/latest/retargeting)
- [Retarget Session](https://docs.wuji.tech/docs/en/wuji-sdk/latest/sdk-practice/retarget-session)

## Pico 光学手势（本仓库 teleop）

任意源只要变成 MediaPipe 21 点即可。本库在 `active=0`、掌三角形过小时 hold。

`RetargetSession` 使用内置调参，不暴露 YAML overlay。

### 关键点预览（不跑 IK）

先停 `./run.sh vr-xrt` 和 `python -m xr_hand_retarget`（同一 PC Service 只能一个 SDK 客户端）。

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
