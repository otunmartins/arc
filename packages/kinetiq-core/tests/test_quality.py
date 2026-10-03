import numpy as np
import pytest

from kinetiq_contracts import JOINT_COUNT, JOINT_INDEX
from kinetiq_core import assess_quality, synthetic


def capture(frame_count: int = 31) -> tuple[np.ndarray, np.ndarray]:
    poses = np.stack([synthetic.neutral_pose()] * frame_count)
    return synthetic.timestamps(frame_count, rate_hz=30.0), synthetic.to_keypoints(poses)


def test_clean_capture_scores_one() -> None:
    report = assess_quality(*capture())
    assert report.score == 1.0
    assert report.valid_fraction == 1.0
    assert report.mean_confidence == pytest.approx(1.0)
    assert report.frame_count == 31
    assert report.duration_s == pytest.approx(1.0)
    assert report.frame_rate_hz == pytest.approx(30.0)
    assert report.max_gap_ms == 34.0


def test_score_is_the_share_of_usable_samples() -> None:
    t_ms, keypoints = capture(frame_count=10)
    keypoints[:5, JOINT_INDEX["left_wrist"], 3] = 0.2
    keypoints[0, JOINT_INDEX["head"]] = (np.nan, np.nan, np.nan, 0.0)
    report = assess_quality(t_ms, keypoints)
    assert report.valid_fraction == pytest.approx(1 - 6 / (10 * JOINT_COUNT))
    assert report.score == report.valid_fraction


def test_quality_can_be_limited_to_the_joints_a_test_needs() -> None:
    t_ms, keypoints = capture(frame_count=10)
    keypoints[:, JOINT_INDEX["left_wrist"], 3] = 0.0
    legs = ["left_hip", "left_knee", "left_ankle"]
    assert assess_quality(t_ms, keypoints, joints=legs).score == 1.0
    assert assess_quality(t_ms, keypoints).score < 1.0


def test_reports_the_longest_gap_between_frames() -> None:
    t_ms, keypoints = capture(frame_count=4)
    t_ms = np.array([0, 33, 400, 433], dtype=np.int32)
    assert assess_quality(t_ms, keypoints).max_gap_ms == 367.0


def test_empty_scan_scores_zero() -> None:
    report = assess_quality(np.empty(0, dtype=np.int32), np.empty((0, JOINT_COUNT, 4), np.float32))
    assert report.score == 0.0
    assert report.frame_count == 0


def test_single_frame_has_no_rate() -> None:
    report = assess_quality(*capture(frame_count=1))
    assert report.frame_rate_hz == 0.0
    assert report.max_gap_ms == 0.0
