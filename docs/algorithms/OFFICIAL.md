# 官方源：wuji-sdk RetargetSession

`retargeting.type: official` 才需要。XHand1 / Linker curl 路径不装。

`wuji-sdk` 已写在 `xr_hand_retarget` 的 `pyproject.toml` 依赖里；`./init.sh install` 装 hand 时会一并安装。

运行时：`wuji_sdk.RetargetSession.for_hand(HandModel.WujiHand2, side=…)`，输入 MediaPipe `(21, 3)` 米制关键点，输出 firmware 顺序 20 关节角。内置调参。

文档：

- [Hand Retargeting](https://docs.wuji.tech/docs/en/wuji-sdk/latest/retargeting)
- [Retarget Session](https://docs.wuji.tech/docs/en/wuji-sdk/latest/sdk-practice/retarget-session)

离线人–物数据集（非实时遥操）见 [TopoRetarget](https://github.com/wuji-technology/toporetarget)，与本仓生产路径无关。

现场光学调试见 [../user/WUJI_CALIB.md](../user/WUJI_CALIB.md)。
