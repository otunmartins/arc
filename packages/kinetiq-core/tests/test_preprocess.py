import numpy as np
import pytest

from kinetiq_contracts import JOINT_COUNT, JOINT_INDEX
from kinetiq_core import angles, synthetic
from kinetiq_core.geometry import FloatArray
from kinetiq_core.preprocess import mask_low_confidence, prepare, resample, smooth


def moving_joint(t_ms: list[int], x: list[float]) -> tuple[np.ndarray, FloatArray]:
    """All joints at the origin except joint 0, whose x follows `x`."""
    xyz = np.zeros((len(t_ms), JOINT_COUNT, 3))
    xyz[:, 0, 0] = x
    return np.array(t_ms, dtype=np.int32), xyz


def signal(values: FloatArray) -> FloatArray:
    xyz = np.zeros((len(values), JOINT_COUNT, 3))
    xyz[:, 0, 0] = values
    return xyz


def test_mask_low_confidence() -> None:
    keypoints = synthetic.to_keypoints(np.stack([synthetic.neutral_pose()] * 2))
    keypoints[0, 3, 3] = 0.49
    keypoints[1, 5] = (np.nan, np.nan, np.nan, 0.0)
    xyz = mask_low_confidence(keypoints, min_confidence=0.5)
    assert xyz.dtype == np.float64
    assert np.isnan(xyz[0, 3]).all()
    assert np.isnan(xyz[1, 5]).all()
    assert np.isfinite(xyz).sum() == (2 * JOINT_COUNT - 2) * 3


def test_resample_interpolates_linearly_onto_an_even_grid() -> None:
    t_ms = list(range(0, 1001, 10))
    t, xyz = moving_joint(t_ms, [ms / 1000 for ms in t_ms])  # x in metres equals time in seconds
    t_s, out = resample(t, xyz, rate_hz=30.0)
    assert t_s == pytest.approx(np.arange(31) / 30)
    assert out[:, 0, 0] == pytest.approx(t_s)
    assert out.shape == (31, JOINT_COUNT, 3)


def test_resample_handles_irregular_timestamps() -> None:
    t_ms = [0, 31, 70, 98, 135, 170, 200]
    t, xyz = moving_joint(t_ms, [2.0 * ms for ms in t_ms])
    t_s, out = resample(t, xyz, rate_hz=20.0)
    assert t_s == pytest.approx([0.0, 0.05, 0.1, 0.15, 0.2])
    assert out[:, 0, 0] == pytest.approx([0.0, 100.0, 200.0, 300.0, 400.0])


def test_resample_leaves_long_gaps_empty() -> None:
    t, xyz = moving_joint([0, 100, 200, 500, 600], [0.0, 1.0, 2.0, 5.0, 6.0])
    _, out = resample(t, xyz, rate_hz=10.0, max_gap_ms=200.0)
    x = out[:, 0, 0]
    assert x[[0, 1, 2, 5, 6]] == pytest.approx([0.0, 1.0, 2.0, 5.0, 6.0])
    assert np.isnan(x[[3, 4]]).all()


def test_resample_fills_a_short_dropout_of_one_joint() -> None:
    t, xyz = moving_joint([0, 100, 200, 300, 400], [0.0, 1.0, 0.0, 3.0, 4.0])
    xyz[2, 0] = np.nan
    _, out = resample(t, xyz, rate_hz=10.0, max_gap_ms=200.0)
    assert out[:, 0, 0] == pytest.approx([0.0, 1.0, 2.0, 3.0, 4.0])
    assert np.isfinite(out[:, 1]).all()


def test_resample_does_not_extrapolate_before_first_or_after_last_valid_sample() -> None:
    t, xyz = moving_joint([0, 100, 200, 300, 400], [0.0, 1.0, 2.0, 3.0, 4.0])
    xyz[[0, 4], 0] = np.nan
    _, out = resample(t, xyz, rate_hz=10.0)
    x = out[:, 0, 0]
    assert np.isnan(x[[0, 4]]).all()
    assert x[1:4] == pytest.approx([1.0, 2.0, 3.0])


def test_resample_keeps_a_joint_that_is_never_seen_as_missing() -> None:
    t, xyz = moving_joint([0, 100, 200], [0.0, 1.0, 2.0])
    xyz[:, 7] = np.nan
    _, out = resample(t, xyz, rate_hz=10.0)
    assert np.isnan(out[:, 7]).all()


def test_resample_uses_the_first_of_duplicate_timestamps() -> None:
    t, xyz = moving_joint([0, 0, 100], [1.0, 99.0, 2.0])
    _, out = resample(t, xyz, rate_hz=10.0)
    assert out[:, 0, 0] == pytest.approx([1.0, 2.0])


def test_resample_of_empty_scan() -> None:
    t_s, out = resample(np.empty(0, dtype=np.int32), np.empty((0, JOINT_COUNT, 3)))
    assert t_s.shape == (0,)
    assert out.shape == (0, JOINT_COUNT, 3)


def test_smooth_leaves_a_constant_signal_alone() -> None:
    out = smooth(signal(np.full(60, 1.25)))
    assert out[:, 0, 0] == pytest.approx(1.25)


def test_smooth_keeps_slow_movement_and_removes_fast_jitter() -> None:
    t = np.arange(180) / 30.0
    slow = 0.1 * np.sin(2 * np.pi * 1.0 * t)
    jitter = 0.02 * np.sin(2 * np.pi * 13.0 * t)
    out = smooth(signal(slow + jitter), rate_hz=30.0, cutoff_hz=6.0)[:, 0, 0]
    middle = slice(20, -20)
    assert np.abs(out - slow)[middle].max() < 0.002
    assert out[middle] == pytest.approx(slow[middle], abs=0.002)


def test_smooth_does_not_shift_the_signal_in_time() -> None:
    t = np.arange(180) / 30.0
    values = np.sin(2 * np.pi * 0.5 * t)
    out = smooth(signal(values))[:, 0, 0]
    assert int(np.argmax(out[:45])) == int(np.argmax(values[:45])) == 15


def test_smooth_preserves_gaps_and_short_runs() -> None:
    rng = np.random.default_rng(0)
    values = rng.normal(size=80)
    values[40:45] = np.nan
    values[50] = np.nan  # leaves a 5-sample run at 45..49, too short to filter
    out = smooth(signal(values))[:, 0, 0]
    assert np.isnan(out[40:45]).all()
    assert np.isnan(out[50])
    assert out[45:50] == pytest.approx(values[45:50])
    assert np.isfinite(out[:40]).all()
    assert not np.allclose(out[:40], values[:40])


def test_smooth_rejects_a_cutoff_at_or_above_half_the_rate() -> None:
    with pytest.raises(ValueError, match="cutoff_hz"):
        smooth(signal(np.zeros(60)), rate_hz=30.0, cutoff_hz=15.0)


def test_prepare_recovers_known_knee_angles_from_a_noisy_capture() -> None:
    """A knee bending 0° → 90° → 0° twice, with jitter, a dropout and uneven timestamps."""
    rng = np.random.default_rng(7)
    frame_count = 120
    t_ms = synthetic.timestamps(frame_count, rate_hz=30.0)
    flexion = np.radians(45.0 - 45.0 * np.cos(2 * np.pi * 0.5 * t_ms / 1000.0))
    neutral = synthetic.neutral_pose()
    poses = np.stack([synthetic.with_knee_flexion(neutral, "left", angle) for angle in flexion])
    poses += rng.normal(scale=0.004, size=poses.shape)  # 4 mm of jitter per axis
    keypoints = synthetic.to_keypoints(poses)
    keypoints[50:53, JOINT_INDEX["left_ankle"], 3] = 0.1  # ankle lost for 100 ms

    pose = prepare(t_ms, keypoints)
    measured = np.degrees(angles.knee_flexion(pose.xyz, "left"))

    assert pose.rate_hz == 30.0
    assert np.isfinite(measured).all()
    assert measured.max() == pytest.approx(90.0, abs=1.5)
    assert measured.min() < 3.0
    expected = 45.0 - 45.0 * np.cos(2 * np.pi * 0.5 * pose.t_s)
    assert np.abs(measured - expected)[5:-5].max() < 3.0
