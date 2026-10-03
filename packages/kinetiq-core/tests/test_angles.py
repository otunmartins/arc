from collections.abc import Callable

import numpy as np
import pytest

from kinetiq_contracts import JOINT_INDEX
from kinetiq_core import angles, synthetic
from kinetiq_core.angles import Side
from kinetiq_core.geometry import FloatArray

SIDES: tuple[Side, ...] = ("left", "right")


def frames(*poses: FloatArray) -> FloatArray:
    return np.stack(poses)


def moved_camera(xyz: FloatArray) -> FloatArray:
    """The same poses seen from a camera that is rotated and somewhere else."""
    yaw, pitch = np.radians(40.0), np.radians(15.0)
    about_y = np.array([[np.cos(yaw), 0, np.sin(yaw)], [0, 1, 0], [-np.sin(yaw), 0, np.cos(yaw)]])
    about_x = np.array(
        [[1, 0, 0], [0, np.cos(pitch), -np.sin(pitch)], [0, np.sin(pitch), np.cos(pitch)]]
    )
    return xyz @ (about_x @ about_y).T + np.array([0.4, -0.2, -3.0])


def degrees(series: FloatArray) -> float:
    return float(np.degrees(series[0]))


def test_body_frame_of_neutral_pose() -> None:
    frame = angles.body_frame(frames(synthetic.neutral_pose()))
    assert frame.lateral[0] == pytest.approx([1.0, 0.0, 0.0])
    assert frame.up[0] == pytest.approx([0.0, 1.0, 0.0])
    assert frame.forward[0] == pytest.approx([0.0, 0.0, 1.0])


def test_neutral_pose_reads_zero_everywhere() -> None:
    xyz = frames(synthetic.neutral_pose())
    for side in SIDES:
        assert degrees(angles.knee_flexion(xyz, side)) == pytest.approx(0.0, abs=1e-6)
        assert degrees(angles.hip_flexion(xyz, side)) == pytest.approx(0.0, abs=1e-6)
        assert degrees(angles.shoulder_abduction(xyz, side)) == pytest.approx(0.0, abs=1e-6)
        assert degrees(angles.knee_valgus(xyz, side)) == pytest.approx(0.0, abs=1e-6)
    assert degrees(angles.trunk_lean(xyz)) == pytest.approx(0.0, abs=1e-6)
    assert degrees(angles.pelvic_obliquity(xyz)) == pytest.approx(0.0, abs=1e-6)


@pytest.mark.parametrize("side", SIDES)
@pytest.mark.parametrize("angle_deg", [0.0, 15.0, 45.0, 90.0, 135.0])
def test_knee_flexion(side: Side, angle_deg: float) -> None:
    xyz = frames(synthetic.with_knee_flexion(synthetic.neutral_pose(), side, np.radians(angle_deg)))
    assert degrees(angles.knee_flexion(xyz, side)) == pytest.approx(angle_deg, abs=1e-6)
    assert degrees(angles.knee_flexion(moved_camera(xyz), side)) == pytest.approx(angle_deg)


@pytest.mark.parametrize("side", SIDES)
@pytest.mark.parametrize("angle_deg", [-20.0, 0.0, 30.0, 90.0, 120.0])
def test_hip_flexion(side: Side, angle_deg: float) -> None:
    xyz = frames(synthetic.with_hip_flexion(synthetic.neutral_pose(), side, np.radians(angle_deg)))
    assert degrees(angles.hip_flexion(xyz, side)) == pytest.approx(angle_deg, abs=1e-6)
    assert degrees(angles.hip_flexion(moved_camera(xyz), side)) == pytest.approx(angle_deg)


@pytest.mark.parametrize("side", SIDES)
@pytest.mark.parametrize("angle_deg", [0.0, 30.0, 90.0, 150.0])
def test_shoulder_abduction(side: Side, angle_deg: float) -> None:
    pose = synthetic.with_shoulder_abduction(synthetic.neutral_pose(), side, np.radians(angle_deg))
    xyz = frames(pose)
    assert degrees(angles.shoulder_abduction(xyz, side)) == pytest.approx(angle_deg, abs=1e-6)
    assert degrees(angles.shoulder_abduction(moved_camera(xyz), side)) == pytest.approx(angle_deg)


@pytest.mark.parametrize("side", SIDES)
@pytest.mark.parametrize("angle_deg", [-8.0, 0.0, 5.0, 20.0])
def test_knee_valgus_is_positive_toward_the_midline(side: Side, angle_deg: float) -> None:
    xyz = frames(synthetic.with_knee_valgus(synthetic.neutral_pose(), side, np.radians(angle_deg)))
    assert degrees(angles.knee_valgus(xyz, side)) == pytest.approx(angle_deg, abs=1e-6)
    assert degrees(angles.knee_valgus(moved_camera(xyz), side)) == pytest.approx(angle_deg)


def test_knee_valgus_moves_the_knee_inward() -> None:
    neutral = synthetic.neutral_pose()
    left = synthetic.with_knee_valgus(neutral, "left", np.radians(20.0))
    right = synthetic.with_knee_valgus(neutral, "right", np.radians(20.0))
    assert left[JOINT_INDEX["left_knee"], 0] < neutral[JOINT_INDEX["left_knee"], 0]
    assert right[JOINT_INDEX["right_knee"], 0] > neutral[JOINT_INDEX["right_knee"], 0]


@pytest.mark.parametrize("angle_deg", [-25.0, -5.0, 0.0, 10.0, 30.0])
def test_trunk_lean_is_positive_toward_the_left(angle_deg: float) -> None:
    xyz = frames(synthetic.with_trunk_lean(synthetic.neutral_pose(), np.radians(angle_deg)))
    assert degrees(angles.trunk_lean(xyz)) == pytest.approx(angle_deg, abs=1e-6)


def test_trunk_lean_ignores_which_way_the_subject_faces() -> None:
    xyz = frames(synthetic.with_trunk_lean(synthetic.neutral_pose(), np.radians(10.0)))
    yaw = np.radians(35.0)
    turned = (
        xyz @ np.array([[np.cos(yaw), 0, np.sin(yaw)], [0, 1, 0], [-np.sin(yaw), 0, np.cos(yaw)]]).T
    )
    assert degrees(angles.trunk_lean(turned)) == pytest.approx(10.0)


def test_vertical_from_gravity() -> None:
    assert angles.vertical_from_gravity(None) == pytest.approx([0.0, 1.0, 0.0])
    assert angles.vertical_from_gravity([0.0, -2.0, 0.0]) == pytest.approx([0.0, 1.0, 0.0])
    assert angles.vertical_from_gravity((0.0, -0.6, -0.8)) == pytest.approx([0.0, 0.6, 0.8])


def test_gravity_corrects_trunk_lean_and_pelvic_obliquity_for_a_tilted_camera() -> None:
    lean = frames(synthetic.with_trunk_lean(synthetic.neutral_pose(), np.radians(10.0)))
    tilt = frames(synthetic.with_pelvic_obliquity(synthetic.neutral_pose(), np.radians(7.0)))
    roll, pitch = np.radians(12.0), np.radians(25.0)
    about_z = np.array(
        [[np.cos(roll), -np.sin(roll), 0], [np.sin(roll), np.cos(roll), 0], [0, 0, 1]]
    )
    about_x = np.array(
        [[1, 0, 0], [0, np.cos(pitch), -np.sin(pitch)], [0, np.sin(pitch), np.cos(pitch)]]
    )
    camera = about_x @ about_z  # world → tilted camera
    gravity = camera @ np.array([0.0, -1.0, 0.0])
    vertical = angles.vertical_from_gravity(gravity.tolist())

    assert degrees(angles.trunk_lean(lean @ camera.T, vertical)) == pytest.approx(10.0)
    assert degrees(angles.pelvic_obliquity(tilt @ camera.T, vertical)) == pytest.approx(7.0)
    # Without the correction the 12° camera roll leaks straight into the reading.
    assert abs(degrees(angles.trunk_lean(lean @ camera.T)) - 10.0) > 5.0


@pytest.mark.parametrize("angle_deg", [-12.0, 0.0, 7.0])
def test_pelvic_obliquity_is_positive_when_left_hip_is_higher(angle_deg: float) -> None:
    xyz = frames(synthetic.with_pelvic_obliquity(synthetic.neutral_pose(), np.radians(angle_deg)))
    assert degrees(angles.pelvic_obliquity(xyz)) == pytest.approx(angle_deg, abs=1e-6)


def test_angles_do_not_leak_between_frames() -> None:
    neutral = synthetic.neutral_pose()
    xyz = frames(
        synthetic.with_knee_flexion(neutral, "left", np.radians(30.0)),
        synthetic.with_knee_flexion(neutral, "left", np.radians(60.0)),
        neutral,
    )
    assert np.degrees(angles.knee_flexion(xyz, "left")) == pytest.approx(
        [30.0, 60.0, 0.0], abs=1e-6
    )
    assert np.degrees(angles.knee_flexion(xyz, "right")) == pytest.approx([0.0, 0.0, 0.0], abs=1e-6)


@pytest.mark.parametrize(
    ("measure", "joint"),
    [
        (lambda xyz: angles.knee_flexion(xyz, "left"), "left_ankle"),
        (lambda xyz: angles.hip_flexion(xyz, "right"), "right_knee"),
        (lambda xyz: angles.hip_flexion(xyz, "right"), "neck"),
        (lambda xyz: angles.shoulder_abduction(xyz, "left"), "left_elbow"),
        (lambda xyz: angles.knee_valgus(xyz, "left"), "left_hip"),
        (angles.trunk_lean, "pelvis"),
        (angles.pelvic_obliquity, "right_hip"),
    ],
)
def test_missing_joint_gives_nan_only_in_that_frame(
    measure: Callable[[FloatArray], FloatArray], joint: str
) -> None:
    xyz = frames(synthetic.neutral_pose(), synthetic.neutral_pose())
    xyz[1, JOINT_INDEX[joint]] = np.nan
    series = measure(xyz)
    assert np.isfinite(series[0])
    assert np.isnan(series[1])
