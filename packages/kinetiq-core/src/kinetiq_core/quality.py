"""Data-quality checks on raw scan frames. These describe the capture, not the patient."""

from collections.abc import Sequence
from dataclasses import dataclass

import numpy as np
from numpy.typing import NDArray

from kinetiq_contracts import JOINT_INDEX, JOINTS

from .preprocess import DEFAULT_MIN_CONFIDENCE


@dataclass(frozen=True)
class QualityReport:
    score: float  # 0..1; currently equal to valid_fraction
    valid_fraction: float  # share of (frame, joint) samples that are usable
    mean_confidence: float
    frame_count: int
    duration_s: float
    frame_rate_hz: float  # mean rate over the scan
    max_gap_ms: float  # longest time between consecutive frames


def assess_quality(
    t_ms: NDArray[np.int32],
    keypoints: NDArray[np.float32],
    *,
    min_confidence: float = DEFAULT_MIN_CONFIDENCE,
    joints: Sequence[str] = JOINTS,
) -> QualityReport:
    """Summarise capture quality over `joints` (default: the whole skeleton)."""
    frame_count = int(t_ms.shape[0])
    if frame_count == 0:
        return QualityReport(0.0, 0.0, 0.0, 0, 0.0, 0.0, 0.0)

    selected = keypoints[:, [JOINT_INDEX[name] for name in joints], :]
    confidence = selected[..., 3]
    usable = (confidence >= min_confidence) & np.isfinite(selected[..., :3]).all(axis=-1)
    valid_fraction = float(usable.mean())

    duration_s = float(t_ms[-1] - t_ms[0]) / 1000.0
    gaps = np.diff(t_ms)
    return QualityReport(
        score=valid_fraction,
        valid_fraction=valid_fraction,
        mean_confidence=float(confidence.mean()),
        frame_count=frame_count,
        duration_s=duration_s,
        frame_rate_hz=(frame_count - 1) / duration_s if duration_s > 0 else 0.0,
        max_gap_ms=float(gaps.max()) if gaps.size else 0.0,
    )
