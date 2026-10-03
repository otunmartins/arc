"""Canonical skeleton `kq-skel-v1`. Left/right are the subject's left and right."""

SKELETON_VERSION = "kq-skel-v1"

JOINTS: tuple[str, ...] = (
    "pelvis",
    "left_hip",
    "right_hip",
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
    "left_knee",
    "right_knee",
    "left_ankle",
    "right_ankle",
    "left_heel",
    "right_heel",
    "left_foot_index",
    "right_foot_index",
)

JOINT_COUNT = len(JOINTS)

JOINT_INDEX: dict[str, int] = {name: index for index, name in enumerate(JOINTS)}
