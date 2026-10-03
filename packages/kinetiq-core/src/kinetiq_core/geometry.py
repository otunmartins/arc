"""Vector helpers. All operate along the last axis and propagate NaN."""

import numpy as np
from numpy.typing import NDArray

FloatArray = NDArray[np.float64]


def dot(u: FloatArray, v: FloatArray) -> FloatArray:
    return np.sum(u * v, axis=-1)


def normalise(v: FloatArray) -> FloatArray:
    """Unit vectors. A zero-length vector becomes NaN."""
    norm = np.linalg.norm(v, axis=-1, keepdims=True)
    with np.errstate(invalid="ignore", divide="ignore"):
        return np.where(norm > 0, v / norm, np.nan)


def angle_between(u: FloatArray, v: FloatArray) -> FloatArray:
    """Unsigned angle in radians, 0 to π. NaN if either vector has zero length."""
    cross = np.linalg.norm(np.cross(u, v), axis=-1)
    angle = np.arctan2(cross, dot(u, v))
    degenerate = (np.linalg.norm(u, axis=-1) == 0) | (np.linalg.norm(v, axis=-1) == 0)
    return np.where(degenerate, np.nan, angle)


def wrap_angle(angle: FloatArray) -> FloatArray:
    """Wrap radians into [-π, π)."""
    return (angle + np.pi) % (2 * np.pi) - np.pi
