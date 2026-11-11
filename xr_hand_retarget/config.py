"""Load a single hand YAML and dispatch to xhand1 | wuji | o6 | l6 | o7."""

from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
from typing import Any

from xr_hand_retarget.backends.xhand1_config import HandConfig, load_hand_config

from xr_hand_retarget.control.command_safety import (
    CommandSafetyConfig,
    parse_command_safety,
)
from xr_hand_retarget.safety import MotionSafetyGains, parse_motion_safety

_PACKAGE_ROOT = Path(__file__).resolve().parents[1]
_REPO_ROOT = _PACKAGE_ROOT.parent
_DEFAULT_CONFIG = _PACKAGE_ROOT / "configs" / "wuji_hand2.yaml"
_DEFAULT_O6_CALIB = _PACKAGE_ROOT / "configs" / "users" / "pico.yaml"
_LINKER_LAYOUTS = ("o6", "l6", "o7")


@dataclass
class O6CurlGains:
    """LinkerHand O6/L6/O7 curl knobs.

    All three use palm-tip features (see palm_tip.py). Robot q lives in
    configs/hands/{o6,l6,o7}.yaml; human curl/az in that hand's linker.user.
    """

    calib_path: Path | None = None
    output_alpha: float = 0.85
    thumb_alpha: float | None = None
    finger_alpha: float | None = None
    neighbor_soft: float = 0.0
    pinch_target_link: str = "pip"
    pinch_axis: int = 1
    opposition_index: int = 1
    urdf_path: str | None = None
    finger_flex_weights: tuple[float, float, float] = (0.45, 0.35, 0.20)
    thumb_flex_weights: tuple[float, float] = (0.55, 0.45)
    model: str = "o6"
    thumb3_opp: float = 0.65
    thumb3_curl: float = 0.35
    thumb_j2_index: float = 1.0
    thumb_j2_middle: float = 1.3
    thumb_j3_index: float = 0.18
    thumb_j3_middle: float = 0.36
    thumb_j3_ring: float = 0.50
    thumb_j3_pinky: float = 0.70
    thumb_j3_ulnar: float = 0.70
    fist_j1: Any = None
    along_j1: Any = None
    attract_near: float = 0.28
    attract_far: float = 0.60
    attract_enabled: bool = True
    slot_near: float = 0.28
    slot_far: float = 1.0
    j2_lock_button: str = "on"
    j2_lock_lo: float | None = None
    j2_lock_hi: float | None = None
    pinch_index_q: Any = None
    pinch_middle_q: Any = None
    pinch_ring_q: Any = None
    pinch_pinky_q: Any = None
    fist_env_enabled: bool = True
    fist_env_fingers: tuple[str, ...] = ("index", "middle")
    fist_env_finger_t: float = 0.92
    fist_env_j2_split: float = 0.6
    fist_env_j1_roof: float = 0.44
    calib_source_side: str = "both"  # both | left | right
    calib_mirror_az: float = 1.0  # +1 copy, -1 negate thumb_az when mirroring
    closed_reach_t: float = 0.88
    pinch_knot_max_t: float | None = None
    nest_r_near: float = 0.32
    nest_r_far: float = 1.15
    nest_curl_span: float = 0.08
    nest_lat_along: float = 0.42
    nest_lat_opp: float = -0.02
    thumb_j2_along: float = 0.22
    thumb_j2_along_fade: float = 0.12
    thumb_j2_pinch_hw: float = 0.25
    mp_o7_thumb: str = "curl"  # curl | legacy — O7 mp_curl thumb path
    pinch_ceiling_enabled: bool = False
    pinch_ceiling_margin_rad: float = 0.0
    pinch_fk_project_enabled: bool = False
    pinch_fk_clearance_m: float | None = None
    pinch_fk_sphere_radius_m: float | None = None


@dataclass
class WujiBackendConfig:
    """Wuji Hand 2 via ``wuji_sdk.RetargetSession`` (builtin IK)."""

    cfg_path: Path


@dataclass
class HandRuntimeConfig:
    """Common ROS/publish fields + one backend payload."""

    backend: str
    hand_id: str
    dof: int
    joint_names: list[str]
    controller: str
    topic_suffix: str
    fsm_topic: str
    fsm_command: int
    auto_movej: bool
    rate_hz: float
    hold_on_inactive: bool
    hold_on_zero_pose: bool
    clamp_urdf: bool
    max_joint_vel_rad_s: float
    min_palm_area_m2: float
    unlock_frames: int
    stream_movej: bool
    path: Path
    xhand1: HandConfig | None
    wuji: WujiBackendConfig | None
    o6_curl: O6CurlGains | None = None
    motion: MotionSafetyGains | None = None
    command: CommandSafetyConfig | None = None

    wuji_type: str = "official"
    linker_type: str = "curl"  # curl | nest | veccurl | mp_curl

    @property
    def retargeting_type(self) -> str:
        if self.backend == "xhand1" and self.xhand1 is not None:
            return self.xhand1.retargeting_type
        if self.backend == "wuji":
            return "official"
        if self.backend in ("o6", "l6", "o7"):
            return self.linker_type or "curl"
        return self.backend

    @property
    def command_topic(self) -> str:
        name = self.controller.strip().strip("/")
        return f"/{name}/{self.topic_suffix}"


def default_config_path() -> Path:
    return resolve_config_path(None)


def resolve_config_path(path: str | Path | None = None) -> Path:
    """``--config`` > ``FA_HAND_CONFIG`` > package ``configs/wuji_hand2.yaml``.

    Bare names like ``configs/o6.yaml`` or ``o6.yaml`` resolve under the
    package ``configs/`` tree (cwd-independent).
    """
    import os

    if path:
        cfg = Path(path).expanduser()
        if cfg.is_file():
            return cfg.resolve()
        name = cfg.name
        candidates = [
            cfg,
            _PACKAGE_ROOT / "configs" / name,
            _PACKAGE_ROOT / cfg,
            _PACKAGE_ROOT / "configs" / cfg,
            _REPO_ROOT / cfg,
            _REPO_ROOT / "xr_hand_retarget" / "configs" / name,
        ]
        seen: set[str] = set()
        for cand in candidates:
            key = str(cand)
            if key in seen:
                continue
            seen.add(key)
            if cand.is_file():
                return cand.resolve()
        raise FileNotFoundError(f"hand config not found: {cfg}")
    for key in ("FA_HAND_CONFIG", "FA_XHAND1_CONFIG"):
        env = os.environ.get(key)
        if not env:
            continue
        cfg = Path(env).expanduser()
        if cfg.is_file():
            return cfg.resolve()
        raise FileNotFoundError(f"{key} points to missing file: {cfg}")
    if _DEFAULT_CONFIG.is_file():
        return _DEFAULT_CONFIG.resolve()
    raise FileNotFoundError(f"hand config not found: {_DEFAULT_CONFIG}")


def _normalize_backend(raw: str) -> str:
    b = raw.strip().lower().replace("-", "_")
    aliases = {
        "xhand": "xhand1",
        "xhand1": "xhand1",
        "wuji": "wuji",
        "wuji_retargeting": "wuji",
        "wuji_hand": "wuji",
        "wuji_hand2": "wuji",
        "wuji_hand_2": "wuji",
        "hand2": "wuji",
        "o6": "o6",
        "linkerhand_o6": "o6",
        "linker_o6": "o6",
        "l6": "l6",
        "linkerhand_l6": "l6",
        "linker_l6": "l6",
        "o7": "o7",
        "linkerhand_o7": "o7",
        "linker_o7": "o7",
        "linker": "linker",
        "linkerhand": "linker",
    }
    if b not in aliases:
        return b
    return aliases[b]


def _linker_layout(raw: dict[str, Any]) -> str:
    layout = str(raw.get("layout") or "").strip().lower()
    if layout in _LINKER_LAYOUTS:
        return layout
    hand_id = str((raw.get("hand") or {}).get("id") or "").lower()
    for key in _LINKER_LAYOUTS:
        if key in hand_id:
            return key
    return ""


def detect_backend(raw: dict[str, Any]) -> str:
    layout = _linker_layout(raw)
    backend_raw = str(raw.get("backend") or "").strip().lower().replace("-", "_")
    if backend_raw in ("linker", "linkerhand") or (
        layout and backend_raw in ("", layout, f"linkerhand_{layout}", f"linker_{layout}")
    ):
        if layout:
            return layout
    if raw.get("backend"):
        b = _normalize_backend(str(raw["backend"]))
        if b == "linker":
            if layout:
                return layout
            raise ValueError(
                "backend: linker needs layout: o6|l6|o7 (or hand.id linkerhand_o7)"
            )
        return b
    if layout:
        return layout
    if raw.get("wuji"):
        return "wuji"
    hand_id = str((raw.get("hand") or {}).get("id") or "").lower()
    if "o7" in hand_id or hand_id in ("linkerhand_o7", "linker_o7"):
        return "o7"
    if "l6" in hand_id or hand_id in ("linkerhand_l6", "linker_l6"):
        return "l6"
    if "o6" in hand_id or hand_id in ("linkerhand_o6", "linker_o6"):
        return "o6"
    if "wuji" in hand_id or hand_id in ("hand2", "wuji_hand_2"):
        return "wuji"
    if raw.get("retargeting"):
        return "xhand1"
    raise ValueError(
        "cannot detect hand backend: set top-level backend: "
        "xhand1|wuji|linker (with layout: o6|l6|o7)"
    )


def _resolve_curl_calib(raw_path: str | None, cfg_path: Path) -> Path | None:
    if not raw_path:
        return None
    p = Path(raw_path)
    candidates = [
        p,
        cfg_path.parent / p,
        _PACKAGE_ROOT / "configs" / p,
        _PACKAGE_ROOT / "configs" / "users" / p.name,
        _PACKAGE_ROOT / "configs" / "calib" / p.name,
        _PACKAGE_ROOT / "configs" / "hands" / p.name,
        _PACKAGE_ROOT / "configs" / "tests" / p.name,
    ]
    for cand in candidates:
        if cand.is_file():
            return cand.resolve()
    return p.resolve()


def _resolve_linker_calib(
    raw_path: str | None, cfg_path: Path, model: str
) -> Path | None:
    del model
    default = _DEFAULT_O6_CALIB
    if not raw_path:
        return default.resolve() if default.is_file() else None
    return _resolve_curl_calib(raw_path, cfg_path)


def _deep_merge(base: dict[str, Any], overlay: dict[str, Any]) -> dict[str, Any]:
    out = dict(base)
    for key, val in overlay.items():
        if isinstance(out.get(key), dict) and isinstance(val, dict):
            out[key] = _deep_merge(out[key], val)
        else:
            out[key] = val
    return out


def _resolve_packaged_yaml(spec: str | Path, cfg_path: Path) -> Path:
    p = Path(spec)
    if p.is_absolute() and p.is_file():
        return p.resolve()
    search = [
        cfg_path.parent / p,
        _PACKAGE_ROOT / "configs" / p,
        _PACKAGE_ROOT / "configs" / p.name,
        _PACKAGE_ROOT / p,
    ]
    for cand in search:
        if cand.is_file():
            return cand.resolve()
    raise FileNotFoundError(f"indexed yaml not found: {spec} (from {cfg_path})")


def _load_yaml_mapping(path: Path) -> dict[str, Any]:
    import yaml

    raw = yaml.safe_load(path.read_text(encoding="utf-8")) or {}
    if not isinstance(raw, dict):
        raise ValueError(f"{path} must be a mapping")
    return raw


def _resolve_user_calib(spec: str, cfg_path: Path) -> Path:
    text = spec.strip()
    if text and "/" not in text.replace("\\", "/") and not text.endswith(
        (".yaml", ".yml")
    ):
        text = f"users/{text}.yaml"
    path = _resolve_curl_calib(text, cfg_path)
    if path is None:
        raise FileNotFoundError(f"user calib not found: {spec}")
    return Path(path)


def _expand_linker_profile(
    raw: dict[str, Any],
    cfg_path: Path,
    *,
    user: str | Path | None = None,
) -> dict[str, Any]:
    """Merge linker.defaults / workspace / test, then apply user calib path."""
    linker = raw.get("linker") if isinstance(raw.get("linker"), dict) else {}
    backend_raw = str(raw.get("backend") or "").strip().lower()
    is_linker = bool(linker) or backend_raw in (
        "linker",
        "linkerhand",
        *_LINKER_LAYOUTS,
    )
    if not is_linker:
        return raw
    merged: dict[str, Any] = {}
    for key in ("defaults", "workspace", "test"):
        spec = linker.get(key)
        if spec:
            merged = _deep_merge(
                merged, _load_yaml_mapping(_resolve_packaged_yaml(spec, cfg_path))
            )
    merged = _deep_merge(merged, raw)
    user_spec = None if user in (None, "") else str(user)
    if not user_spec:
        user_spec = linker.get("user")
    if user_spec:
        calib_path = _resolve_user_calib(str(user_spec), cfg_path)
        ret = merged.get("retargeting")
        if not isinstance(ret, dict):
            ret = {}
            merged["retargeting"] = ret
        curl = ret.get("curl")
        if not isinstance(curl, dict):
            curl = {}
            ret["curl"] = curl
        curl["calib"] = str(calib_path)
        linker_out = dict(merged.get("linker") or linker)
        linker_out["user"] = str(calib_path)
        merged["linker"] = linker_out
    return merged


def _floats3(raw, default: tuple[float, float, float]) -> tuple[float, float, float]:
    if not raw:
        return default
    vals = [float(x) for x in raw]
    if len(vals) != 3:
        raise ValueError(f"finger_flex_weights must have 3 values, got {len(vals)}")
    return (vals[0], vals[1], vals[2])


def _floats2(raw, default: tuple[float, float]) -> tuple[float, float]:
    if not raw:
        return default
    vals = [float(x) for x in raw]
    if len(vals) != 2:
        raise ValueError(f"thumb_flex_weights must have 2 values, got {len(vals)}")
    return (vals[0], vals[1])


def _parse_calib_source_side(raw: dict[str, Any]) -> tuple[str, float]:
    src = str(raw.get("source_side") or raw.get("calib_side") or "both").strip().lower()
    aliases = {
        "both": "both",
        "all": "both",
        "full": "both",
        "left": "left",
        "l": "left",
        "lh": "left",
        "right": "right",
        "r": "right",
        "rh": "right",
    }
    src = aliases.get(src, "both")
    az = str(raw.get("mirror_az") or "copy").strip().lower()
    az_sign = -1.0 if az in ("negate", "flip", "minus", "-1") else 1.0
    return src, az_sign


def _parse_fist_fingers(raw) -> tuple[str, ...]:
    allowed = ("index", "middle", "ring", "pinky")
    names: list[str] = []
    if isinstance(raw, str):
        raw = [p.strip() for p in raw.split(",")]
    if raw:
        for item in raw:
            n = str(item).strip().lower()
            if n in allowed:
                names.append(n)
    return tuple(names) or ("index", "middle")


def _parse_attract_enabled(attract: dict[str, Any]) -> bool:
    """Explicit ``enabled`` wins. Else on only when near/far are usable."""
    if not isinstance(attract, dict):
        return True
    if "enabled" in attract:
        return bool(attract["enabled"])
    near = float(attract.get("near", 0.22) or 0.0)
    far = float(attract.get("far", 0.45) or 0.0)
    return near > 0.0 and far > 0.0


def _parse_j2_lock_button(raw: Any) -> str:
    """Pico A/X rising-edge toggle. ``off`` disables the controller button."""
    if raw is None or raw is False:
        return "off"
    if isinstance(raw, str):
        name = raw.strip().lower()
    elif isinstance(raw, dict):
        name = str(raw.get("button", "off") or "off").strip().lower()
    else:
        return "off"
    name = name.replace("_button", "").replace("-", "")
    if name in ("a", "x"):
        return "a"
    if name in ("b", "y"):
        return "b"
    return "off"


def _parse_j2_lock_bound(raw: Any, key: str) -> float | None:
    if not isinstance(raw, dict) or raw.get(key) is None:
        return None
    return float(raw[key])


def _parse_o6_curl(
    retargeting: dict[str, Any], cfg_path: Path, *, model: str = "o6"
) -> O6CurlGains:
    raw = retargeting.get("curl") or retargeting.get("curl_calib") or {}
    calib_raw = raw.get("calib") or raw.get("calib_path")
    key = str(raw.get("model") or model).strip().lower()
    thumb3 = raw.get("thumb3") or {}
    ws = raw.get("workspace") or {}
    j2 = ws.get("thumb_joint2") or {}
    j3 = ws.get("thumb_joint3") or {}
    attract = raw.get("attract") or {}
    snap = raw.get("snap") or {}
    pinch_q = ws.get("pinch_q") or {}
    idx_q = pinch_q.get("index")
    mid_q = pinch_q.get("middle")
    rng_q = pinch_q.get("ring")
    pky_q = pinch_q.get("pinky")
    env = raw.get("fist_envelope") or ws.get("fist_envelope") or {}
    nest = raw.get("nest") or ws.get("nest") or {}
    source_side, mirror_az = _parse_calib_source_side(raw)
    j2_lock = raw.get("j2_lock") or ws.get("j2_lock")
    pinch_cfg = raw.get("pinch") or {}
    fk_clear = pinch_cfg.get("fk_project_clearance_m")
    fk_sphere = pinch_cfg.get("fk_sphere_radius_m")
    return O6CurlGains(
        calib_path=_resolve_linker_calib(
            None if calib_raw is None else str(calib_raw), cfg_path, key
        ),
        output_alpha=float(raw.get("output_alpha", 0.85)),
        thumb_alpha=(
            None
            if raw.get("thumb_alpha") is None
            else float(raw.get("thumb_alpha"))
        ),
        finger_alpha=(
            None
            if raw.get("finger_alpha") is None
            else float(raw.get("finger_alpha"))
        ),
        neighbor_soft=float(raw.get("neighbor_soft", 0.0)),
        pinch_target_link=str(
            raw.get("pinch_target_link") or raw.get("pinch_target") or "pip"
        ),
        pinch_axis=int(raw.get("pinch_axis", 1)),
        opposition_index=int(raw.get("opposition_index", 1)),
        urdf_path=raw.get("urdf_path"),
        finger_flex_weights=_floats3(
            raw.get("finger_flex_weights"), (0.45, 0.35, 0.20)
        ),
        thumb_flex_weights=_floats2(raw.get("thumb_flex_weights"), (0.55, 0.45)),
        model=key,
        thumb3_opp=float(thumb3.get("opposition", raw.get("thumb3_opp", 0.65))),
        thumb3_curl=float(thumb3.get("curl", raw.get("thumb3_curl", 0.35))),
        thumb_j2_index=float(j2.get("index", raw.get("thumb_j2_index", 1.0))),
        thumb_j2_middle=float(j2.get("middle", raw.get("thumb_j2_middle", 1.3))),
        thumb_j2_along=float(j2.get("along", raw.get("thumb_j2_along", 0.22))),
        thumb_j2_along_fade=float(
            j2.get("along_fade", raw.get("thumb_j2_along_fade", 0.12))
        ),
        thumb_j2_pinch_hw=float(
            j2.get("pinch_halfwidth", raw.get("thumb_j2_pinch_hw", 0.25))
        ),
        thumb_j3_index=float(j3.get("index", raw.get("thumb_j3_index", 0.18))),
        thumb_j3_middle=float(j3.get("middle", raw.get("thumb_j3_middle", 0.36))),
        thumb_j3_ring=float(j3.get("ring", raw.get("thumb_j3_ring", 0.50))),
        thumb_j3_pinky=float(j3.get("pinky", raw.get("thumb_j3_pinky", 0.70))),
        thumb_j3_ulnar=float(
            j3.get(
                "pinky",
                j3.get("ulnar", raw.get("thumb_j3_ulnar", 0.70)),
            )
        ),
        fist_j1=(
            None
            if ws.get("fist_j1", raw.get("fist_j1")) is None
            else float(ws.get("fist_j1", raw.get("fist_j1")))
        ),
        along_j1=(
            None
            if ws.get("along_j1", raw.get("along_j1")) is None
            else float(ws.get("along_j1", raw.get("along_j1")))
        ),
        closed_reach_t=float(ws.get("closed_reach_t", raw.get("closed_reach_t", 0.88))),
        pinch_knot_max_t=(
            None
            if ws.get("pinch_knot_max_t", raw.get("pinch_knot_max_t")) is None
            else float(ws.get("pinch_knot_max_t", raw.get("pinch_knot_max_t")))
        ),
        attract_near=float(
            attract.get("near", snap.get("enter", raw.get("attract_near", 0.22)))
        ),
        attract_far=float(
            attract.get("far", snap.get("exit", raw.get("attract_far", 0.45)))
        ),
        attract_enabled=_parse_attract_enabled(attract),
        slot_near=float(attract.get("slot_near", 0.28)),
        slot_far=float(attract.get("slot_far", 1.0)),
        j2_lock_button=_parse_j2_lock_button(j2_lock),
        j2_lock_lo=_parse_j2_lock_bound(j2_lock, "lo"),
        j2_lock_hi=_parse_j2_lock_bound(j2_lock, "hi"),
        pinch_index_q=idx_q,
        pinch_middle_q=mid_q,
        pinch_ring_q=rng_q,
        pinch_pinky_q=pky_q,
        fist_env_enabled=bool(env.get("enabled", True)),
        fist_env_fingers=_parse_fist_fingers(env.get("fingers")),
        fist_env_finger_t=float(env.get("finger_t", 0.92)),
        fist_env_j2_split=float(env.get("j2_split", 0.6)),
        fist_env_j1_roof=float(env.get("j1_roof", 0.44)),
        calib_source_side=source_side,
        calib_mirror_az=mirror_az,
        nest_r_near=float(nest.get("r_near", 0.32)),
        nest_r_far=float(nest.get("r_far", 1.15)),
        nest_curl_span=float(nest.get("curl_span", 0.08)),
        nest_lat_along=float(nest.get("lat_along", 0.42)),
        nest_lat_opp=float(nest.get("lat_opp", -0.02)),
        mp_o7_thumb=str(raw.get("mp_o7_thumb", "curl")).strip().lower() or "curl",
        pinch_ceiling_enabled=bool(pinch_cfg.get("ceiling_enabled", False)),
        pinch_ceiling_margin_rad=float(pinch_cfg.get("ceiling_margin_rad", 0.0)),
        pinch_fk_project_enabled=bool(pinch_cfg.get("fk_project_enabled", False)),
        pinch_fk_clearance_m=(
            None if fk_clear is None else float(fk_clear)
        ),
        pinch_fk_sphere_radius_m=(
            None if fk_sphere is None else float(fk_sphere)
        ),
    )


def _parse_wuji(cfg_path: Path) -> WujiBackendConfig:
    return WujiBackendConfig(cfg_path=cfg_path.resolve())


def load_runtime_config(
    path: str | Path | None = None,
    *,
    user: str | Path | None = None,
) -> HandRuntimeConfig:
    try:
        import yaml
    except ImportError as exc:
        raise ImportError("PyYAML is required") from exc

    cfg_path = resolve_config_path(path)

    with cfg_path.open("r", encoding="utf-8") as f:
        raw: dict[str, Any] = yaml.safe_load(f) or {}
    if not isinstance(raw, dict):
        raise ValueError(f"{cfg_path} must be a mapping")
    raw = _expand_linker_profile(raw, cfg_path, user=user)

    backend = detect_backend(raw)
    ros = raw.get("ros") or {}
    safety = raw.get("safety") or {}
    publish = raw.get("publish") or {}
    hand = raw.get("hand") or {}

    xhand1: HandConfig | None = None
    wuji: WujiBackendConfig | None = None
    o6_curl: O6CurlGains | None = None
    wuji_type = "official"
    linker_type = "curl"
    if backend == "xhand1":
        inner = raw.get("xhand1", {}).get("config") if isinstance(raw.get("xhand1"), dict) else None
        xhand1_path = cfg_path
        if inner:
            inner_path = Path(inner)
            cand: list[Path] = []
            if inner_path.is_absolute():
                cand.append(inner_path)
            cand.extend(
                [
                    _PACKAGE_ROOT / inner,
                    _PACKAGE_ROOT / "configs" / inner,
                    cfg_path.parent / inner,
                ]
            )
            self_resolved = cfg_path.resolve()
            xhand1_path = next(
                (
                    c
                    for c in cand
                    if c.is_file() and c.resolve() != self_resolved
                ),
                inner_path,
            )
        xhand1 = load_hand_config(xhand1_path)
        hand_id = str(hand.get("id") or xhand1.hand_id)
        joint_names = list(hand.get("joint_names") or xhand1.joint_names)
        dof = int(hand.get("dof") or xhand1.dof)
        controller = str(ros.get("controller") or xhand1.controller)
        topic_suffix = str(ros.get("topic_suffix") or xhand1.topic_suffix)
        fsm_topic = str(ros.get("fsm_topic") or xhand1.fsm_topic)
        fsm_command = int(ros.get("fsm_command", 3))
        auto_movej = bool(ros.get("auto_movej", xhand1.auto_movej))
        rate_hz = float(publish.get("rate_hz", xhand1.rate_hz))
        hold_on_inactive = bool(safety.get("hold_on_inactive", xhand1.hold_on_inactive))
        hold_on_zero_pose = bool(safety.get("hold_on_zero_pose", xhand1.hold_on_zero_pose))
    else:
        ret = raw.get("retargeting") or {}
        names = list(hand.get("joint_names") or [])
        linker = {
            "o6": (6, "linkerhand_o6"),
            "l6": (6, "linkerhand_l6"),
            "o7": (7, "linkerhand_o7"),
        }
        default_dof, default_id = linker.get(backend, (20, "wuji_hand2"))
        dof = int(hand.get("dof") or (len(names) if names else default_dof))
        if names and len(names) != dof:
            raise ValueError(
                f"hand.joint_names length {len(names)} != hand.dof {dof}"
            )
        if not names:
            names = [f"joint_{i}" for i in range(dof)]
        hand_id = str(hand.get("id") or default_id)
        joint_names = names
        controller = str(ros.get("controller") or "hand_joint_controller")
        topic_suffix = str(ros.get("topic_suffix") or "target_joint_position")
        fsm_topic = str(ros.get("fsm_topic") or "/fsm_command")
        fsm_command = int(ros.get("fsm_command", 4))
        auto_movej = bool(ros.get("auto_movej", True))
        rate_hz = float(publish.get("rate_hz", 50.0))
        hold_on_inactive = bool(safety.get("hold_on_inactive", True))
        hold_on_zero_pose = bool(safety.get("hold_on_zero_pose", True))
        if backend in ("o6", "l6", "o7"):
            o6_curl = _parse_o6_curl(ret, cfg_path, model=backend)
            raw_t = str(ret.get("type") or "curl").lower()
            if raw_t in ("mp_curl", "mediapipe", "mp21_curl"):
                linker_type = "mp_curl"
            elif raw_t in ("nest", "keyvec", "nest_vec"):
                linker_type = "nest"
            elif raw_t in ("veccurl", "vcurl"):
                linker_type = "veccurl"
            else:
                linker_type = "curl"
        else:
            # Wuji production path is RetargetSession only.
            wuji_type = "official"
            wuji = _parse_wuji(cfg_path)

    clamp_urdf = bool(safety.get("clamp_urdf", True))
    max_joint_vel_rad_s = float(safety.get("max_joint_vel_rad_s", 0.0))
    min_palm_area_m2 = float(safety.get("min_palm_area_m2", 1e-5))
    unlock_frames = int(safety.get("unlock_frames", 5))
    stream_movej = bool(ros.get("stream_movej", backend in ("wuji", "o6", "l6", "o7")))
    motion = parse_motion_safety(safety)
    command = parse_command_safety(safety, backend=backend)
    if command.max_velocity is None and max_joint_vel_rad_s > 0.0:
        command.max_velocity = float(max_joint_vel_rad_s)

    return HandRuntimeConfig(
        backend=backend,
        hand_id=hand_id,
        dof=dof,
        joint_names=joint_names,
        controller=controller,
        topic_suffix=topic_suffix,
        fsm_topic=fsm_topic,
        fsm_command=fsm_command,
        auto_movej=auto_movej,
        rate_hz=rate_hz,
        hold_on_inactive=hold_on_inactive,
        hold_on_zero_pose=hold_on_zero_pose,
        clamp_urdf=clamp_urdf,
        max_joint_vel_rad_s=max_joint_vel_rad_s,
        min_palm_area_m2=min_palm_area_m2,
        unlock_frames=unlock_frames,
        stream_movej=stream_movej,
        path=cfg_path.resolve(),
        xhand1=xhand1,
        wuji=wuji,
        o6_curl=o6_curl,
        motion=motion,
        command=command,
        wuji_type=wuji_type,
        linker_type=linker_type,
    )
