# 代码布局

手映射唯一家在独立仓 `xr_hand_retarget`（`fa-py-libraries` 子模块）。VR 产品仍在聚合仓 `vr_pose_publisher`。

```
fa-py-libraries/
  xr_hand_retarget/          # 子模块
    xr_hand_retarget/        # importable：algorithms / backends / control / sources / …
    configs/                 # 手型索引 + hands/ users/ calib/ official/
    assets/                  # URDF + cspace
    third_party/wuji-retargeting/   # 可选；./init.sh install-wuji-retargeting
  vr_pose_publisher/         # XRT 路径 import xr_hand_retarget.dual_node
  configs/local.yaml         # 本机白名单
```

安装：`./init.sh install`（或 `uv pip install -e xr_hand_retarget`）。旧包 `xr_xhand1_retarget` 已删除；旧 CLI 名仍指向本包入口。

里程碑摘要见 [PIPELINE.md](PIPELINE.md)。验证命令见 [RUN.md](RUN.md)。
