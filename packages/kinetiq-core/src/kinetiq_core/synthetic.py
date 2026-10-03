"""Synthetic `kq-skel-v1` poses with known joint angles, for tests and demo data.

The neutral pose is a subject standing upright facing the camera: +X is the subject's
left, +Y is up, +Z is the way the subject faces. Each `with_*` function returns a copy
of the pose with one joint angle set, starting from neutral limb positions.
"""

import numpy as np
from numpy.typing import NDArray

from kinetiq_contracts import JOINT_COUNT, JOINT_INDEX

from .angles import Side
from .geometry import FloatArray

THIGH_M = 0.45
SHANK_M = 0.45
UPPER_ARM_M = 0.30
FOREARM_M = 0.25
HIP_HALF_WIDTH_M = 0.10

_UPPER_BODY = (
    "spine_mid",
    "chest",
    "neck",
    "head",
    "left_shoulder",
    "right_shoulder",
    "left_elbow",
    "right_elbow",
    "left_wrist",
    "right_wrist",
)

_NEUTRAL: dict[str, tuple[float, float, float]] = {
    "pelvis": (0.0, 1.0, 0.0),
    "left_hip": (HIP_HALF_WIDTH_M, 1.0, 0.0),
    "right_hip": (-HIP_HALF_WIDTH_M, 1.0, 0.0),
    "spine_mid": (0.0, 1.2, 0.0),
    "chest": (0.0, 1.4, 0.0),
    "neck": (0.0, 1.5, 0.0),
    "head": (0.0, 1.65, 0.0),
    "left_shoulder": (0.2, 1.45, 0.0),
    "right_shoulder": (-0.2, 1.45, 0.0),
    "left_elbow": (0.2, 1.45 - UPPER_ARM_M, 0.0),
    "right_elbow": (-0.2, 1.45 - UPPER_ARM_M, 0.0),
    "left_wrist": (0.2, 1.45 - UPPER_ARM_M - FOREARM_M, 0.0),
    "right_wrist": (-0.2, 1.45 - UPPER_ARM_M - FOREARM_M, 0.0),
    "left_knee": (HIP_HALF_WIDTH_M, 1.0 - THIGH_M, 0.0),
    "right_knee": (-HIP_HALF_WIDTH_M, 1.0 - THIGH_M, 0.0),
    "left_ankle": (HIP_HALF_WIDTH_M, 1.0 - THIGH_M - SHANK_M, 0.0),
    "right_ankle": (-HIP_HALF_WIDTH_M, 1.0 - THIGH_M - SHANK_M, 0.0),
    "left_heel": (HIP_HALF_WIDTH_M, 0.03, -0.05),
    "right_heel": (-HIP_HALF_WIDTH_M, 0.03, -0.05),
    "left_foot_index": (HIP_HALF_WIDTH_M, 0.02, 0.15),
    "right_foot_index": (-HIP_HALF_WIDTH_M, 0.02, 0.15),
}


def neutral_pose() -> FloatArray:
    """One upright pose with shape (21, 3), in metres."""
    pose = np.empty((JOINT_COUNT, 3))
    for name, position in _NEUTRAL.items():
        pose[JOINT_INDEX[name]] = position
    return pose


def with_knee_flexion(pose: FloatArray, side: Side, angle: float) -> FloatArray:
    """Bend the knee by `angle` radians, foot moving backward; the thigh stays vertical."""
    return _set_leg(pose, side, (0.0, -1.0, 0.0), (0.0, -np.cos(angle), -np.sin(angle)))


def with_hip_flexion(pose: FloatArray, side: Side, angle: float) -> FloatArray:
    """Swing the straight leg forward by `angle` radians (negative is backward)."""
    direction = (0.0, -np.cos(angle), np.sin(angle))
    return _set_leg(pose, side, direction, direction)


def with_knee_valgus(pose: FloatArray, side: Side, angle: float) -> FloatArray:
    """Move the knee toward the midline: a frontal hip-knee-ankle deviation of `angle`."""
    inward = -1.0 if side == "left" else 1.0
    half = angle / 2
    thigh = (inward * np.sin(half), -np.cos(half), 0.0)
    shank = (-inward * np.sin(half), -np.cos(half), 0.0)
    return _set_leg(pose, side, thigh, shank)


def with_shoulder_abduction(pose: FloatArray, side: Side, angle: float) -> FloatArray:
    """Raise the straight arm sideways by `angle` radians."""
    outward = 1.0 if side == "left" else -1.0
    direction = np.array([outward * np.sin(angle), -np.cos(angle), 0.0])
    posed = pose.copy()
    shoulder = posed[JOINT_INDEX[f"{side}_shoulder"]]
    posed[JOINT_INDEX[f"{side}_elbow"]] = shoulder + UPPER_ARM_M * direction
    posed[JOINT_INDEX[f"{side}_wrist"]] = shoulder + (UPPER_ARM_M + FOREARM_M) * direction
    return posed


def with_trunk_lean(pose: FloatArray, angle: float) -> FloatArray:
    """Tilt the upper body about the pelvis by `angle` radians toward the subject's left."""
    posed = pose.copy()
    pelvis = posed[JOINT_INDEX["pelvis"]]
    cos, sin = np.cos(angle), np.sin(angle)
    for name in _UPPER_BODY:
        x, y, z = posed[JOINT_INDEX[name]] - pelvis
        posed[JOINT_INDEX[name]] = pelvis + (x * cos + y * sin, -x * sin + y * cos, z)
    return posed


def with_pelvic_obliquity(pose: FloatArray, angle: float) -> FloatArray:
    """Tilt the hip line by `angle` radians, left hip rising."""
    posed = pose.copy()
    pelvis = posed[JOINT_INDEX["pelvis"]]
    offset = HIP_HALF_WIDTH_M * np.array([np.cos(angle), np.sin(angle), 0.0])
    posed[JOINT_INDEX["left_hip"]] = pelvis + offset
    posed[JOINT_INDEX["right_hip"]] = pelvis - offset
    return posed


def to_keypoints(poses: FloatArray, confidence: float = 1.0) -> NDArray[np.float32]:
    """Poses with shape (frames, 21, 3) → contract keypoints (frames, 21, 4)."""
    keypoints = np.empty((*poses.shape[:2], 4), dtype=np.float32)
    keypoints[..., :3] = poses
    keypoints[..., 3] = confidence
    return keypoints


def timestamps(frame_count: int, rate_hz: float = 30.0) -> NDArray[np.int32]:
    """Millisecond timestamps for `frame_count` frames at `rate_hz`, rounded as a device would."""
    return np.round(np.arange(frame_count) * 1000.0 / rate_hz).astype(np.int32)


def _set_leg(
    pose: FloatArray,
    side: Side,
    thigh_direction: tuple[float, float, float],
    shank_direction: tuple[float, float, float],
) -> FloatArray:
    posed = pose.copy()
    ankle_index = JOINT_INDEX[f"{side}_ankle"]
    old_ankle = pose[ankle_index]
    knee = posed[JOINT_INDEX[f"{side}_hip"]] + THIGH_M * np.array(thigh_direction)
    ankle = knee + SHANK_M * np.array(shank_direction)
    posed[JOINT_INDEX[f"{side}_knee"]] = knee
    posed[ankle_index] = ankle
    for foot_joint in (f"{side}_heel", f"{side}_foot_index"):
        posed[JOINT_INDEX[foot_joint]] = ankle + (pose[JOINT_INDEX[foot_joint]] - old_ankle)
    return posed
