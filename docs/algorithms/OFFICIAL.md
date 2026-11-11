# 官方源：wuji-retargeting

`retargeting.type: official` 才需要。curl / vector 路径不装。

```bash
./init.sh install-wuji-retargeting
```

会 clone 到 `xr_hand_retarget/third_party/wuji-retargeting`（含 `wuji-description` 子模块），再 **editable 安装进当前 `.fa-env.toml` backend 环境**，并钉死 `numpy<2`（ROS Jazzy Pinocchio 与 NumPy 2.x 不兼容）。需要 `pin` 与 `nlopt`。

**目录有了 ≠ 已安装。** DualHand worker 用 `spawn`，只认 site-packages，不会自动把 `third_party/` 加进 `sys.path`。

## 装完自检

与 `run.sh` / `init.sh install` **同一 backend**（`uv` 的 `.venv` 或 `conda` 的 `fa-ros2`）：

```bash
# uv
source .venv/bin/activate
# conda: conda activate fa-ros2

python -c 'import wuji_retargeting; print(wuji_retargeting.__file__)'
```

应打印 `…/site-packages/…` 或 editable 路径下的 `wuji_retargeting/__init__.py`。若 `ModuleNotFoundError`：

1. 再跑一次 `./init.sh install-wuji-retargeting`，盯住 `uv pip` / `pip` 是否报错退出（常见：`pin` / `nlopt` 装不上）。
2. 确认没有装进 A 环境、却用 B 环境跑 `./run.sh`。
3. 镜像装不上 `pin` 时：

```bash
pip install pin==3.8.0 -i https://pypi.org/simple
# 或: uv pip install pin==3.8.0 -i https://pypi.org/simple
```

子模块空时：

```bash
git -C xr_hand_retarget/third_party/wuji-retargeting submodule update --init --recursive
```

覆盖路径：`WUJI_RETARGETING_ROOT=/path/to/wuji-retargeting`。

## beta1 与 beta2

| | **beta1** | **beta2** |
|--|--|--|
| 是什么 | 坐标系冻结的第一版 | 同一套关节 + 指尖触觉垫 |
| 官方 IK | yaml 指向这里 | 官方求解器还没用 |
| fa_w2 mock | 不直接用 | 从 beta2 改成 ROS xacro |

**不要改 fa_w2 去迁就求解器。** Hand 2 的 `optimizer.urdf_path` / `link_naming` 以官方 yaml 为准。

调参顺序见 [Parameter Tuning](https://docs.wuji.tech/docs/en/wuji-retargeting/latest/tuning/)。现场光学调试步骤见 [../user/WUJI_CALIB.md](../user/WUJI_CALIB.md)。
