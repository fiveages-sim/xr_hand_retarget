"""Wuji Hand backend — ``wuji_sdk.RetargetSession`` only.

OpenXR 26 → MediaPipe 21 → SDK builtin IK → q[20] (firmware finger-major).
Archived ``wuji_retargeting.Retargeter`` is no longer used.
"""

from __future__ import annotations

import numpy as np

from xr_hand_retarget.landmarks import (
    palm_triangle_area_m2,
    pose_is_zero,
)
from xr_hand_retarget.pipeline import SideStep

_WUJI_SDK_HINT = (
    "wuji-sdk is not installed (declared by xr_hand_retarget). Run:\n"
    "  ./init.sh install\n"
    "  # or: pip install -e xr_hand_retarget\n"
    "then point FA_HAND_CONFIG at configs/wuji_hand2.yaml"
)


def preflight_wuji(cfg, side: str) -> None:
    """Fail before SDK/XRT init if wuji-sdk cannot be imported."""
    if cfg.wuji is None:
        raise ValueError("wuji backend requires a wuji: block in the yaml")
    if side not in ("left", "right"):
        raise ValueError(f"side must be left|right, got {side!r}")
    try:
        from wuji_sdk import HandModel, Handedness, RetargetSession  # noqa: F401
    except ImportError as exc:
        raise ImportError(_WUJI_SDK_HINT) from exc


class WujiBackend:
    """Official ``wuji_sdk.RetargetSession.for_hand`` per side."""

    def __init__(self, side: str, cfg):
        if side not in ("left", "right"):
            raise ValueError(f"side must be left|right, got {side!r}")
        if cfg.wuji is None:
            raise ValueError("wuji backend requires a wuji: block in the yaml")
        try:
            from wuji_sdk import HandModel, Handedness, RetargetSession
        except ImportError as exc:
            raise ImportError(_WUJI_SDK_HINT) from exc

        self.side = side
        self.dof = int(cfg.dof)
        self.retargeting_type = "official"
        self.vector_profile = ""
        self._cfg = cfg
        self._wuji = cfg.wuji
        cmd_names = list(cfg.joint_names)
        if self.dof != len(cmd_names):
            raise ValueError(
                f"hand.dof {self.dof} != len(joint_names) {len(cmd_names)}"
            )
        if self.dof != 20:
            raise ValueError(
                f"wuji_sdk RetargetSession returns 20 joints; hand.dof={self.dof}"
            )

        handedness = Handedness.Left if side == "left" else Handedness.Right
        self._session = RetargetSession.for_hand(
            HandModel.WujiHand2, side=handedness
        )
        # Firmware order is finger-major thumb..pinky × 4; matches joint_names.
        self._perm = np.arange(self.dof, dtype=np.int64)
        self._q_hold: np.ndarray | None = None
        self._was_held = True
        self._unlock = 0
        self._q_limits = None
        dt = 1.0 / max(float(cfg.rate_hz), 1.0)
        vel = max(float(cfg.max_joint_vel_rad_s), 0.0)
        self._max_delta = vel * dt if vel > 0.0 else 0.0

        print(
            f"[retarget] side={side} type=official engine=RetargetSession "
            f"model=WujiHand2 dof={self.dof} "
            f"clamp_urdf={cfg.clamp_urdf} max_dq={self._max_delta:.4f}rad/step "
            f"palm_area>={cfg.min_palm_area_m2} unlock={cfg.unlock_frames}",
            flush=True,
        )
        print(
            "[qpos map] i  BJC_name                     (firmware finger-major)",
            flush=True,
        )
        for i, cmd in enumerate(cmd_names):
            print(f"  {i:02d} {cmd:28s} q[{i}]", flush=True)

    def _hold(self, active: int, xyz_abs: float, reason: str, *, reset_unlock: bool = True) -> SideStep:
        if not self._was_held:
            try:
                self._session.reset()
            except Exception:
                pass
        if reset_unlock:
            self._unlock = 0
        self._was_held = True
        if self._q_hold is None:
            q = np.zeros(self.dof, dtype=np.float64)
        else:
            q = self._q_hold.copy()
        return SideStep(q=q, active=active, held=True, xyz_abs=xyz_abs, reason=reason, sat=-1)

    def _shape_q(self, q: np.ndarray) -> np.ndarray:
        q = np.asarray(q, dtype=np.float64).reshape(-1)
        if q.shape[0] != self.dof:
            if q.shape[0] > self.dof:
                q = q[: self.dof]
            else:
                pad = np.zeros(self.dof, dtype=np.float64)
                pad[: q.shape[0]] = q
                q = pad
        if self._cfg.clamp_urdf and self._q_limits is not None:
            q = np.clip(q, self._q_limits[:, 0], self._q_limits[:, 1])
        if self._max_delta > 0.0 and self._q_hold is not None:
            q = self._q_hold + np.clip(q - self._q_hold, -self._max_delta, self._max_delta)
        return q

    def step(self, frame, xrt=None, **_kwargs) -> SideStep:
        """``xrt`` accepted for SidePipeline parity (Linker j2-lock); unused here."""
        from xr_hand_retarget.sources.frame import HandFrame

        if not isinstance(frame, HandFrame):
            raise TypeError(f"expected HandFrame, got {type(frame)!r}")
        active = int(frame.active)
        raw = frame.ensure_joints26()
        xyz_abs = float(frame.xyz_abs)
        if self._cfg.hold_on_inactive and active == 0:
            return self._hold(active, xyz_abs, "inactive")
        if self._cfg.hold_on_zero_pose and pose_is_zero(raw):
            return self._hold(active, xyz_abs, "zero")

        mp21 = frame.ensure_xyz21()
        area = palm_triangle_area_m2(mp21)
        if area < float(self._cfg.min_palm_area_m2):
            return self._hold(active, xyz_abs, f"palm={area:.2e}")

        need = max(int(self._cfg.unlock_frames), 1)
        if self._was_held:
            self._unlock += 1
            if self._unlock < need:
                return self._hold(
                    active, xyz_abs, f"unlock {self._unlock}/{need}", reset_unlock=False
                )
            self._was_held = False
            self._unlock = need

        try:
            q_raw = np.asarray(
                self._session.step(np.asarray(mp21, dtype=np.float32)),
                dtype=np.float64,
            ).reshape(-1)
        except Exception as exc:
            return self._hold(active, xyz_abs, f"sdk:{exc}")

        q = q_raw[self._perm]
        q = self._shape_q(q)
        self._q_hold = q.copy()
        sat = -1
        if self._q_limits is not None:
            lo, hi = self._q_limits[:, 0], self._q_limits[:, 1]
            sat = int(np.sum((q - lo < 1e-3) | (hi - q < 1e-3)))
        return SideStep(q=q, active=active, held=False, xyz_abs=xyz_abs, reason="ok", sat=sat)
