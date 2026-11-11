"""Wuji Hand 2 curl feature extraction and calib I/O.

Shared helpers for Linker curl_o6 (OpenXR feature pack). Hand 2 production
retarget uses ``wuji_sdk.RetargetSession``, not this lerp path.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from pathlib import Path
from typing import Any

import numpy as np

from xr_hand_retarget.algorithms.curl_xhand1 import PinchKnot
from xr_hand_retarget.algorithms.remap import (
    finger_chain_flexions,
    four_finger_tip_span,
    thumb_chain_flexion,
    thumb_tip_palm_x_m,
)

FINGERS = ("index", "middle", "ring", "pinky")
SCHEMA = "wuji_hand2_curl_calib.v2"

_SEED_FIST_MCP = 1.15
_SEED_FIST_PIP = 1.05
_SEED_FIST_DIP = 0.90
_SEED_THUMB_MCP = 1.10
_SEED_THUMB_IP = 1.05
_SEED_OPEN_THUMB_LAT = 0.045
_SEED_PINKY_THUMB_LAT = -0.025


@dataclass
class CurlFeatures2:
    mcp: dict[str, float]
    pip: dict[str, float]
    dip: dict[str, float]
    thumb_mcp: float
    thumb_ip: float
    thumb_lat: float
    finger_span: float = 0.0


@dataclass
class SideCurlCalib2:
    open_mcp: dict[str, float]
    open_pip: dict[str, float]
    open_dip: dict[str, float]
    fist_mcp: dict[str, float]
    fist_pip: dict[str, float]
    fist_dip: dict[str, float]
    open_thumb_mcp: float
    open_thumb_ip: float
    thumb_flex_mcp: float
    thumb_flex_ip: float
    open_thumb_lat: float
    thumb_to_pinky_lat: float
    along_thumb_lat: float | None = None
    pinch_skipped: bool = True
    pinch: dict[str, PinchKnot | None] = field(default_factory=dict)
    together_finger_span: float | None = None
    spread_finger_span: float | None = None


def extract_curl_features2(joints26: np.ndarray, side: str) -> CurlFeatures2:
    mcp: dict[str, float] = {}
    pip: dict[str, float] = {}
    dip: dict[str, float] = {}
    for name in FINGERS:
        mcp[name], pip[name], dip[name] = finger_chain_flexions(joints26, name)
    t_mcp, t_ip = thumb_chain_flexion(joints26)
    return CurlFeatures2(
        mcp=mcp,
        pip=pip,
        dip=dip,
        thumb_mcp=t_mcp,
        thumb_ip=t_ip,
        thumb_lat=thumb_tip_palm_x_m(joints26, side),
        finger_span=four_finger_tip_span(joints26),
    )


def seed_side_calib() -> SideCurlCalib2:
    zeros = {n: 0.0 for n in FINGERS}
    return SideCurlCalib2(
        open_mcp=dict(zeros),
        open_pip=dict(zeros),
        open_dip=dict(zeros),
        fist_mcp={n: _SEED_FIST_MCP for n in FINGERS},
        fist_pip={n: _SEED_FIST_PIP for n in FINGERS},
        fist_dip={n: _SEED_FIST_DIP for n in FINGERS},
        open_thumb_mcp=0.0,
        open_thumb_ip=0.0,
        thumb_flex_mcp=_SEED_THUMB_MCP,
        thumb_flex_ip=_SEED_THUMB_IP,
        open_thumb_lat=_SEED_OPEN_THUMB_LAT,
        thumb_to_pinky_lat=_SEED_PINKY_THUMB_LAT,
        pinch_skipped=True,
        pinch={n: None for n in FINGERS},
        together_finger_span=None,
        spread_finger_span=None,
    )


def _floats(block: dict[str, Any], suffix: str, default: float) -> dict[str, float]:
    return {n: float(block.get(f"{n}_{suffix}", default)) for n in FINGERS}


def _opt_float(block: dict[str, Any], *keys: str) -> float | None:
    for k in keys:
        if k in block and block[k] is not None:
            return float(block[k])
    return None


def _parse_pinch(raw: dict[str, Any] | None) -> tuple[bool, dict[str, PinchKnot | None]]:
    out: dict[str, PinchKnot | None] = {n: None for n in FINGERS}
    if not raw:
        return True, out
    skipped = bool(raw.get("skipped", False))
    captured = 0
    for name in FINGERS:
        item = raw.get(name)
        if not isinstance(item, dict):
            continue
        lat = item.get("thumb_lat")
        if lat is None:
            continue
        out[name] = PinchKnot(
            thumb_lat=float(lat),
            q=_opt_float(item, "q"),
            thumb_mcp=_opt_float(item, "thumb_mcp"),
            thumb_ip=_opt_float(item, "thumb_ip"),
            finger_mcp=_opt_float(item, f"{name}_mcp", "finger_mcp", "mcp"),
            finger_pip=_opt_float(item, f"{name}_pip", "finger_pip", "pip"),
            finger_dip=_opt_float(item, f"{name}_dip", "finger_dip", "dip"),
        )
        captured += 1
    if captured == 0:
        skipped = True
    return skipped, out


def side_calib_from_dict(raw: dict[str, Any] | None) -> SideCurlCalib2:
    seed = seed_side_calib()
    if not raw:
        return seed
    open_b = raw.get("open") or {}
    fist_b = raw.get("fist") or {}
    pinky_b = raw.get("thumb_to_pinky") or raw.get("thumb_left") or {}
    along_b = raw.get("thumb_along") or {}
    flex_b = raw.get("thumb_flex") or {}
    fist_thumb_mcp = fist_b.get("thumb_mcp")
    fist_thumb_ip = fist_b.get("thumb_ip")
    pinch_skipped, pinch = _parse_pinch(raw.get("pinch"))
    ft_b = raw.get("fingers_together") or {}
    fs_b = raw.get("fingers_spread") or {}
    return SideCurlCalib2(
        open_mcp=_floats(open_b, "mcp", 0.0),
        open_pip=_floats(open_b, "pip", 0.0),
        open_dip=_floats(open_b, "dip", 0.0),
        fist_mcp=_floats(fist_b, "mcp", _SEED_FIST_MCP),
        fist_pip=_floats(fist_b, "pip", _SEED_FIST_PIP),
        fist_dip=_floats(fist_b, "dip", _SEED_FIST_DIP),
        open_thumb_mcp=float(open_b.get("thumb_mcp", 0.0)),
        open_thumb_ip=float(open_b.get("thumb_ip", 0.0)),
        thumb_flex_mcp=float(
            fist_thumb_mcp
            if fist_thumb_mcp is not None
            else flex_b.get("mcp", _SEED_THUMB_MCP)
        ),
        thumb_flex_ip=float(
            fist_thumb_ip
            if fist_thumb_ip is not None
            else flex_b.get("ip", _SEED_THUMB_IP)
        ),
        open_thumb_lat=float(open_b.get("thumb_lat", seed.open_thumb_lat)),
        thumb_to_pinky_lat=float(pinky_b.get("thumb_lat", seed.thumb_to_pinky_lat)),
        along_thumb_lat=_opt_float(along_b, "thumb_lat", "lat"),
        pinch_skipped=pinch_skipped,
        pinch=pinch,
        together_finger_span=_opt_float(ft_b, "finger_span", "span"),
        spread_finger_span=_opt_float(fs_b, "finger_span", "span"),
    )


def side_calib_to_dict(calib: SideCurlCalib2) -> dict[str, Any]:
    open_b: dict[str, float] = {}
    fist_b: dict[str, float] = {}
    for name in FINGERS:
        open_b[f"{name}_mcp"] = float(calib.open_mcp[name])
        open_b[f"{name}_pip"] = float(calib.open_pip[name])
        open_b[f"{name}_dip"] = float(calib.open_dip[name])
        fist_b[f"{name}_mcp"] = float(calib.fist_mcp[name])
        fist_b[f"{name}_pip"] = float(calib.fist_pip[name])
        fist_b[f"{name}_dip"] = float(calib.fist_dip[name])
    open_b["thumb_mcp"] = float(calib.open_thumb_mcp)
    open_b["thumb_ip"] = float(calib.open_thumb_ip)
    open_b["thumb_lat"] = float(calib.open_thumb_lat)
    fist_b["thumb_mcp"] = float(calib.thumb_flex_mcp)
    fist_b["thumb_ip"] = float(calib.thumb_flex_ip)
    pinch: dict[str, Any] = {"skipped": bool(calib.pinch_skipped)}
    for name in FINGERS:
        knot = (calib.pinch or {}).get(name)
        if knot is None:
            continue
        from xr_hand_retarget.algorithms.curl_xhand1 import _pinch_knot_to_item

        pinch[name] = _pinch_knot_to_item(name, knot)
    out: dict[str, Any] = {
        "open": open_b,
        "fist": fist_b,
        "thumb_to_pinky": {"thumb_lat": float(calib.thumb_to_pinky_lat)},
        "thumb_flex": {
            "mcp": float(calib.thumb_flex_mcp),
            "ip": float(calib.thumb_flex_ip),
        },
        "pinch": pinch,
    }
    if calib.along_thumb_lat is not None:
        out["thumb_along"] = {"thumb_lat": float(calib.along_thumb_lat)}
    if calib.together_finger_span is not None:
        out["fingers_together"] = {"finger_span": float(calib.together_finger_span)}
    if calib.spread_finger_span is not None:
        out["fingers_spread"] = {"finger_span": float(calib.spread_finger_span)}
    return out


def load_calib_file(path: str | Path) -> dict[str, SideCurlCalib2]:
    import yaml

    cfg_path = Path(path)
    if not cfg_path.is_file():
        raise FileNotFoundError(f"curl calib not found: {cfg_path}")
    with cfg_path.open("r", encoding="utf-8") as f:
        raw: dict[str, Any] = yaml.safe_load(f) or {}
    sides = raw.get("sides") or {}
    return {
        "left": side_calib_from_dict(sides.get("left")),
        "right": side_calib_from_dict(sides.get("right")),
    }


def dump_calib_file(
    path: str | Path,
    sides: dict[str, SideCurlCalib2],
    *,
    source: str = "xrobotoolkit",
    headset: str = "pico",
) -> None:
    import yaml

    payload: dict[str, Any] = {
        "schema": SCHEMA,
        "source": source,
        "headset": headset,
        "sides": {
            name: side_calib_to_dict(sides[name])
            for name in ("left", "right")
            if name in sides
        },
    }
    path = Path(path)
    path.parent.mkdir(parents=True, exist_ok=True)
    header = (
        "# Wuji Hand 2 curl calibration dump (feature I/O helper).\n"
        "# schema: wuji_hand2_curl_calib.v1\n"
        "# Production retarget uses wuji_sdk.RetargetSession, not this lerp path.\n"
    )
    with path.open("w", encoding="utf-8") as f:
        f.write(header)
        yaml.safe_dump(payload, f, sort_keys=False, allow_unicode=True)
