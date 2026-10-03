"""Scan-level metrics from the catalogue in `features/data/DATA.md`.

Each function takes prepared positions (see `preprocess.prepare`) and returns a
`Measurement` in SI units, or `None` when the joints needed were never visible.
"""

from dataclasses import dataclass
from typing import Literal

import numpy as np

from . import angles
from .angles import Side
from .geometry import FloatArray

METHOD_VERSION = "kinetiq-core/0.1.0"


@dataclass(frozen=True)
class Measurement:
    metric_code: str
    side: Literal["left", "right", "none"]
    value: float
    unit: str
    method_version: str = METHOD_VERSION
    base_metric: str | None = None  # set for symmetry_index


def knee_flexion_peak(xyz: FloatArray, side: Side) -> Measurement | None:
    return _measure("knee_flexion_peak", side, _max(angles.knee_flexion(xyz, side)))


def knee_extension_deficit(xyz: FloatArray, side: Side) -> Measurement | None:
    """Smallest knee flexion reached; 0 is full extension."""
    return _measure("knee_extension_deficit", side, _min(angles.knee_flexion(xyz, side)))


def hip_flexion_peak(xyz: FloatArray, side: Side) -> Measurement | None:
    return _measure("hip_flexion_peak", side, _max(angles.hip_flexion(xyz, side)))


def shoulder_abduction_peak(xyz: FloatArray, side: Side) -> Measurement | None:
    return _measure("shoulder_abduction_peak", side, _max(angles.shoulder_abduction(xyz, side)))


def knee_valgus_peak(xyz: FloatArray, side: Side) -> Measurement | None:
    return _measure("knee_valgus_peak", side, _max(angles.knee_valgus(xyz, side)))


def trunk_lean_peak(xyz: FloatArray, vertical: FloatArray = angles.CAMERA_UP) -> Measurement | None:
    """Largest lean to either side. `vertical` comes from `angles.vertical_from_gravity`."""
    return _measure("trunk_lean_peak", "none", _max(np.abs(angles.trunk_lean(xyz, vertical))))


def symmetry_index(left: Measurement, right: Measurement) -> Measurement | None:
    """`100 × |L − R| / ((L + R) / 2)` for the same metric measured on each side."""
    if left.metric_code != right.metric_code or (left.side, right.side) != ("left", "right"):
        raise ValueError("symmetry_index needs the same metric measured on the left and the right")
    mean = (left.value + right.value) / 2
    if mean <= 0:
        return None
    value = 100 * abs(left.value - right.value) / mean
    return Measurement("symmetry_index", "none", value, "%", base_metric=left.metric_code)


def _measure(code: str, side: Literal["left", "right", "none"], value: float) -> Measurement | None:
    return None if np.isnan(value) else Measurement(code, side, value, "rad")


def _max(series: FloatArray) -> float:
    finite = series[np.isfinite(series)]
    return float(finite.max()) if finite.size else float("nan")


def _min(series: FloatArray) -> float:
    finite = series[np.isfinite(series)]
    return float(finite.min()) if finite.size else float("nan")
