import numpy as np
import pytest

from kinetiq_contracts import JOINT_INDEX
from kinetiq_core import METHOD_VERSION, Measurement, metrics, synthetic
from kinetiq_core.geometry import FloatArray


def knee_ramp(left_peak_deg: float, right_peak_deg: float, start_deg: float = 5.0) -> FloatArray:
    neutral = synthetic.neutral_pose()
    poses = []
    for left, right in zip(
        np.linspace(start_deg, left_peak_deg, 20),
        np.linspace(start_deg, right_peak_deg, 20),
        strict=True,
    ):
        pose = synthetic.with_knee_flexion(neutral, "left", np.radians(left))
        poses.append(synthetic.with_knee_flexion(pose, "right", np.radians(right)))
    return np.stack(poses)


def test_knee_flexion_peak_and_extension_deficit() -> None:
    xyz = knee_ramp(left_peak_deg=100.0, right_peak_deg=80.0)
    left = metrics.knee_flexion_peak(xyz, "left")
    right = metrics.knee_flexion_peak(xyz, "right")
    deficit = metrics.knee_extension_deficit(xyz, "left")
    assert left is not None
    assert (left.metric_code, left.side, left.unit) == ("knee_flexion_peak", "left", "rad")
    assert left.value == pytest.approx(np.radians(100.0))
    assert right is not None and right.value == pytest.approx(np.radians(80.0))
    assert deficit is not None
    assert deficit.metric_code == "knee_extension_deficit"
    assert deficit.value == pytest.approx(np.radians(5.0))


def test_measurements_carry_unit_side_and_method_version() -> None:
    measurement = metrics.knee_flexion_peak(knee_ramp(90.0, 90.0), "right")
    assert measurement is not None
    assert measurement.unit == "rad"
    assert measurement.side == "right"
    assert measurement.method_version == METHOD_VERSION
    assert measurement.base_metric is None


def test_hip_flexion_peak() -> None:
    neutral = synthetic.neutral_pose()
    xyz = np.stack(
        [synthetic.with_hip_flexion(neutral, "left", np.radians(a)) for a in (-10.0, 40.0, 75.0)]
    )
    measurement = metrics.hip_flexion_peak(xyz, "left")
    assert measurement is not None and measurement.value == pytest.approx(np.radians(75.0))


def test_shoulder_abduction_peak() -> None:
    neutral = synthetic.neutral_pose()
    xyz = np.stack(
        [synthetic.with_shoulder_abduction(neutral, "right", np.radians(a)) for a in (0, 60, 140)]
    )
    measurement = metrics.shoulder_abduction_peak(xyz, "right")
    assert measurement is not None and measurement.value == pytest.approx(np.radians(140.0))


def test_knee_valgus_peak() -> None:
    neutral = synthetic.neutral_pose()
    xyz = np.stack(
        [synthetic.with_knee_valgus(neutral, "right", np.radians(a)) for a in (-4.0, 3.0, 12.0)]
    )
    measurement = metrics.knee_valgus_peak(xyz, "right")
    assert measurement is not None and measurement.value == pytest.approx(np.radians(12.0))


def test_trunk_lean_peak_counts_either_direction() -> None:
    neutral = synthetic.neutral_pose()
    xyz = np.stack([synthetic.with_trunk_lean(neutral, np.radians(a)) for a in (4.0, -12.0, 6.0)])
    measurement = metrics.trunk_lean_peak(xyz)
    assert measurement is not None
    assert measurement.side == "none"
    assert measurement.value == pytest.approx(np.radians(12.0))


def test_symmetry_index() -> None:
    xyz = knee_ramp(left_peak_deg=100.0, right_peak_deg=80.0)
    left = metrics.knee_flexion_peak(xyz, "left")
    right = metrics.knee_flexion_peak(xyz, "right")
    assert left is not None and right is not None
    symmetry = metrics.symmetry_index(left, right)
    assert symmetry is not None
    assert (symmetry.metric_code, symmetry.side, symmetry.unit) == ("symmetry_index", "none", "%")
    assert symmetry.base_metric == "knee_flexion_peak"
    assert symmetry.value == pytest.approx(100 * 20 / 90)


def test_symmetry_index_of_equal_sides_is_zero() -> None:
    xyz = knee_ramp(90.0, 90.0)
    left = metrics.knee_flexion_peak(xyz, "left")
    right = metrics.knee_flexion_peak(xyz, "right")
    assert left is not None and right is not None
    symmetry = metrics.symmetry_index(left, right)
    assert symmetry is not None and symmetry.value == pytest.approx(0.0, abs=1e-9)


def test_symmetry_index_needs_matching_left_and_right() -> None:
    left = Measurement("knee_flexion_peak", "left", 1.0, "rad")
    with pytest.raises(ValueError, match="same metric"):
        metrics.symmetry_index(left, Measurement("hip_flexion_peak", "right", 1.0, "rad"))
    with pytest.raises(ValueError, match="same metric"):
        metrics.symmetry_index(left, left)


def test_symmetry_index_is_undefined_when_the_mean_is_not_positive() -> None:
    left = Measurement("knee_valgus_peak", "left", -0.1, "rad")
    right = Measurement("knee_valgus_peak", "right", 0.1, "rad")
    assert metrics.symmetry_index(left, right) is None


def test_metric_ignores_frames_where_the_joint_is_missing() -> None:
    xyz = knee_ramp(100.0, 80.0)
    xyz[-1, JOINT_INDEX["left_ankle"]] = np.nan  # hides the 100° frame
    measurement = metrics.knee_flexion_peak(xyz, "left")
    assert measurement is not None and measurement.value == pytest.approx(np.radians(95.0))


def test_metric_is_none_when_the_joint_is_never_visible() -> None:
    xyz = knee_ramp(100.0, 80.0)
    xyz[:, JOINT_INDEX["left_ankle"]] = np.nan
    assert metrics.knee_flexion_peak(xyz, "left") is None
    assert metrics.knee_extension_deficit(xyz, "left") is None
    assert metrics.knee_flexion_peak(xyz, "right") is not None
