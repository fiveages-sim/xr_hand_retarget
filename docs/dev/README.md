# 开发文档

配置分层、后端接线、本仓迁移状态。捏合数学见 [../algorithms/](../algorithms/)。

总览入口：[../../README.md](../../README.md) / [../../README_CN.md](../../README_CN.md)。

| 文档 | 内容 |
|------|------|
| [RUN.md](RUN.md) | 验证命令：`local.yaml` / `python -m xr_hand_retarget --config …` |
| [CONFIG.md](CONFIG.md) | User / Product / Dev 分层与白名单 |
| [COMMAND_SAFETY.md](COMMAND_SAFETY.md) | 发布门控与安全 |
| [TXHAND.md](TXHAND.md) | XHand1 设备一次标定（URDF 限位 / 捏合槽） |
| [PIPELINE.md](PIPELINE.md) | `source → 21 点 → q` 分层；与 VR 仓边界 |
| [LAYOUT.md](LAYOUT.md) | 代码目录约定 |
| [ASYNC_TELEOP.md](ASYNC_TELEOP.md) | EE⊥hand 三方解耦：目标 / 框架 / 红线 / P0–P3 / 验收 |

用户操作见 [../user/](../user/)。
