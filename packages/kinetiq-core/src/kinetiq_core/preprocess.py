"""Turn raw scan frames into a clean, evenly sampled pose series.

Raw frames come straight from the device: irregular timestamps, low-confidence joints,
jitter. Everything downstream works on the output of `prepare`.
"""

from dataclasses import dataclass
from typing import cast

import numpy as np
from numpy.typing import NDArray
from scipy.signal import butter, filtfilt

from .geometry import FloatArray

DEFAULT_MIN_CONFIDENCE = 0.5
DEFAULT_MAX_GAP_MS = 200.0
DEFAULT_RATE_HZ = 30.0
DEFAULT_CUTOFF_HZ = 6.0
_FILTER_ORDER = 2  # applied forward and backward, so effectively 4th order with no lag


@dataclass(frozen=True)
class Pose:
    t_s: FloatArray  # (frames,) seconds from scan start
    xyz: FloatArray  # (frames, 21, 3) metres; NaN where a joint is missing
    rate_hz: float


def mask_low_confidence(
    keypoints: NDArray[np.float32], min_confidence: float = DEFAULT_MIN_CONFIDENCE
) -> FloatArray:
    """Positions as float64, with NaN for joints below `min_confidence` or already missing."""
    xyz = keypoints[..., :3].astype(np.float64)
    unusable = (keypoints[..., 3] < min_confidence) | ~np.isfinite(xyz).all(axis=-1)
    xyz[unusable] = np.nan
    return xyz


def resample(
    t_ms: NDArray[np.int32],
    xyz: FloatArray,
    *,
    rate_hz: float = DEFAULT_RATE_HZ,
    max_gap_ms: float = DEFAULT_MAX_GAP_MS,
) -> tuple[FloatArray, FloatArray]:
    """Linearly interpolate each joint onto an even grid starting at the first frame.

    A grid point is filled only when the valid samples either side of it are at most
    `max_gap_ms` apart; longer gaps stay NaN rather than being invented.
    Returns `(t_s, xyz)`.
    """
    joint_count = xyz.shape[1]
    if t_ms.shape[0] == 0:
        return np.empty(0), np.empty((0, joint_count, 3))

    t = t_ms.astype(np.float64)
    first_of_each_time = np.concatenate(([True], np.diff(t) > 0))
    t = t[first_of_each_time]
    xyz = xyz[first_of_each_time]

    step_ms = 1000.0 / rate_hz
    count = int(np.floor((t[-1] - t[0]) / step_ms + 1e-9)) + 1
    # Clamp so rounding in the last step cannot push it past the final frame.
    grid = np.minimum(t[0] + step_ms * np.arange(count), t[-1])
    out = np.full((count, joint_count, 3), np.nan)

    for j in range(joint_count):
        valid = np.isfinite(xyz[:, j, :]).all(axis=1)
        if not valid.any():
            continue
        times = t[valid]
        positions = xyz[valid, j, :]
        after = cast("NDArray[np.intp]", np.searchsorted(times, grid, side="left"))
        hi = np.clip(after, 0, len(times) - 1)
        lo = np.clip(after - 1, 0, len(times) - 1)
        on_sample = (after < len(times)) & (times[hi] == grid)
        between = (after > 0) & (after < len(times))
        fill = on_sample | (between & (times[hi] - times[lo] <= max_gap_ms))
        for axis in range(3):
            out[fill, j, axis] = np.interp(grid, times, positions[:, axis])[fill]

    return grid / 1000.0, out


def smooth(
    xyz: FloatArray, *, rate_hz: float = DEFAULT_RATE_HZ, cutoff_hz: float = DEFAULT_CUTOFF_HZ
) -> FloatArray:
    """Zero-lag Butterworth low-pass on each coordinate.

    Each unbroken run of valid samples is filtered on its own; runs too short for the
    filter are left as they are, and NaN gaps are preserved.
    """
    if not 0 < cutoff_hz < rate_hz / 2:
        raise ValueError("cutoff_hz must be between 0 and half the sample rate")
    b, a = butter(_FILTER_ORDER, cutoff_hz / (rate_hz / 2))
    shortest = 3 * max(len(a), len(b)) + 1

    out = xyz.copy()
    columns = out.reshape(out.shape[0], -1)
    for column in range(columns.shape[1]):
        series = columns[:, column]
        for start, stop in _finite_runs(series):
            if stop - start >= shortest:
                series[start:stop] = filtfilt(b, a, series[start:stop])
    return out


def prepare(
    t_ms: NDArray[np.int32],
    keypoints: NDArray[np.float32],
    *,
    min_confidence: float = DEFAULT_MIN_CONFIDENCE,
    max_gap_ms: float = DEFAULT_MAX_GAP_MS,
    rate_hz: float = DEFAULT_RATE_HZ,
    cutoff_hz: float = DEFAULT_CUTOFF_HZ,
) -> Pose:
    """Mask unreliable joints, resample to an even rate with short gaps filled, then smooth."""
    xyz = mask_low_confidence(keypoints, min_confidence)
    t_s, xyz = resample(t_ms, xyz, rate_hz=rate_hz, max_gap_ms=max_gap_ms)
    return Pose(t_s=t_s, xyz=smooth(xyz, rate_hz=rate_hz, cutoff_hz=cutoff_hz), rate_hz=rate_hz)


def _finite_runs(series: FloatArray) -> list[tuple[int, int]]:
    """Half-open index ranges of consecutive finite values."""
    finite = np.concatenate(([False], np.isfinite(series), [False]))
    edges = np.flatnonzero(np.diff(finite.astype(np.int8)))
    return [(int(start), int(stop)) for start, stop in zip(edges[::2], edges[1::2], strict=True)]
