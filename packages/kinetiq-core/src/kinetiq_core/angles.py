"""Joint angle time series from `kq-skel-v1` positions.

Every function takes `xyz` with shape (frames, 21, 3) in metres and returns radians with
shape (frames,). A frame with a missing joint (NaN) gives NaN.

Angles measured in the body frame do not depend on where the camera is. `trunk_lean` and
`pelvic_obliquity` are measured against `vertical`; pass `vertical_from_gravity(...)` so a
tilted camera does not bias them.
"""

from collections.abc import Sequence
from dataclasses import dataclass
from typing import Literal

import numpy as np

from kinetiq_contracts import JOINT_INDEX

from .geometry import FloatArray, angle_between, dot, normalise, wrap_angle

Side = Literal["left", "right"]

CAMERA_UP: FloatArray = np.array([0.0, 1.0, 0.0])


@dataclass(frozen=True)
class BodyFrame:
    """Unit axes of the subject per frame, each with shape (frames, 3)."""

    lateral: FloatArray  # toward the subject's left
    up: FloatArray  # along the trunk, pelvis to neck
    forward: FloatArray  # the way the subject faces


def vertical_from_gravity(gravity: Sequence[float] | None) -> FloatArray:
    """Up direction in camera space from the scan header's `camera.gravity`.

    Falls back to the camera's +Y axis when the device did not report gravity.
    """
    if gravity is None:
        return CAMERA_UP
    return -normalise(np.asarray(gravity, dtype=np.float64))


def joint(xyz: FloatArray, name: str) -> FloatArray:
    return xyz[:, JOINT_INDEX[name], :]


def body_frame(xyz: FloatArray) -> BodyFrame:
    lateral = normalise(joint(xyz, "left_hip") - joint(xyz, "right_hip"))
    trunk = joint(xyz, "neck") - joint(xyz, "pelvis")
    up = normalise(trunk - dot(trunk, lateral)[:, None] * lateral)
    return BodyFrame(lateral=lateral, up=up, forward=np.cross(lateral, up))


def knee_flexion(xyz: FloatArray, side: Side) -> FloatArray:
    """Angle between thigh (hip→knee) and shank (knee→ankle); 0 is a straight leg.

    Unsigned, so hyperextension also reads as a positive angle.
    """
    thigh = joint(xyz, f"{side}_knee") - joint(xyz, f"{side}_hip")
    shank = joint(xyz, f"{side}_ankle") - joint(xyz, f"{side}_knee")
    return angle_between(thigh, shank)


def hip_flexion(xyz: FloatArray, side: Side) -> FloatArray:
    """Sagittal angle of the thigh from the downward trunk line; forward is positive."""
    frame = body_frame(xyz)
    thigh = joint(xyz, f"{side}_knee") - joint(xyz, f"{side}_hip")
    return np.arctan2(dot(thigh, frame.forward), -dot(thigh, frame.up))


def shoulder_abduction(xyz: FloatArray, side: Side) -> FloatArray:
    """Frontal angle of the upper arm from the downward trunk line; outward is positive."""
    frame = body_frame(xyz)
    arm = joint(xyz, f"{side}_elbow") - joint(xyz, f"{side}_shoulder")
    outward = frame.lateral if side == "left" else -frame.lateral
    return np.arctan2(dot(arm, outward), -dot(arm, frame.up))


def knee_valgus(xyz: FloatArray, side: Side) -> FloatArray:
    """Frontal-plane projection angle of hip-knee-ankle; knee toward the midline is positive."""
    frame = body_frame(xyz)
    thigh = joint(xyz, f"{side}_knee") - joint(xyz, f"{side}_hip")
    shank = joint(xyz, f"{side}_ankle") - joint(xyz, f"{side}_knee")
    thigh_angle = np.arctan2(dot(thigh, frame.lateral), -dot(thigh, frame.up))
    shank_angle = np.arctan2(dot(shank, frame.lateral), -dot(shank, frame.up))
    deviation = wrap_angle(shank_angle - thigh_angle)
    return deviation if side == "left" else -deviation


def trunk_lean(xyz: FloatArray, vertical: FloatArray = CAMERA_UP) -> FloatArray:
    """Frontal-plane angle of the trunk from vertical; toward the subject's left is positive."""
    trunk = joint(xyz, "neck") - joint(xyz, "pelvis")
    hips = joint(xyz, "left_hip") - joint(xyz, "right_hip")
    level = normalise(hips - dot(hips, vertical)[:, None] * vertical)
    return np.arctan2(dot(trunk, level), dot(trunk, vertical))


def pelvic_obliquity(xyz: FloatArray, vertical: FloatArray = CAMERA_UP) -> FloatArray:
    """Angle of the hip line from horizontal; left hip higher is positive."""
    hips = joint(xyz, "left_hip") - joint(xyz, "right_hip")
    rise = dot(hips, vertical)
    run = np.linalg.norm(hips - rise[:, None] * vertical, axis=-1)
    return np.where(rise**2 + run**2 > 0, np.arctan2(rise, run), np.nan)
