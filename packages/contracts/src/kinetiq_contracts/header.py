"""Scan header: the JSON block at the start of every `.kqk.gz` file."""

import math
from typing import Annotated, Literal
from uuid import UUID

from pydantic import AwareDatetime, BaseModel, ConfigDict, Field, field_validator

PoseRuntime = Literal["tflite", "coreml", "onnx", "mediapipe", "tensorrt"]
Platform = Literal["ios", "android", "web", "edge"]
Orientation = Literal["portrait", "landscape"]
# Which side of the subject faces the camera.
CameraView = Literal["front", "side_left", "side_right"]
SegmentKind = Literal["assessment", "exercise", "test"]


class _Model(BaseModel):
    model_config = ConfigDict(extra="forbid")


class PoseModel(_Model):
    id: str = Field(min_length=1)
    version: str = Field(min_length=1)
    runtime: PoseRuntime


class Device(_Model):
    platform: Platform
    model: str
    app_version: str = Field(min_length=1)


class Camera(_Model):
    fps: float = Field(gt=0)
    width: int = Field(gt=0)
    height: int = Field(gt=0)
    orientation: Orientation
    view: CameraView
    height_m: float | None = Field(gt=0)
    # Unit vector pointing down (the way gravity pulls) in camera space; null if unknown.
    gravity: Annotated[list[float], Field(min_length=3, max_length=3)] | None

    @field_validator("gravity")
    @classmethod
    def _gravity_is_a_unit_vector(cls, value: list[float] | None) -> list[float] | None:
        if value is not None and not math.isclose(math.hypot(*value), 1.0, abs_tol=0.01):
            raise ValueError("gravity must be a unit vector")
        return value


class Battery(_Model):
    id: str = Field(min_length=1)
    version: str = Field(min_length=1)


class Segment(_Model):
    kind: SegmentKind
    code: str = Field(min_length=1)


class ScanHeader(_Model):
    format: Literal["kqk"]
    format_version: Literal[1]
    skeleton: Literal["kq-skel-v1"]
    scan_id: UUID
    pose_model: PoseModel
    device: Device
    camera: Camera
    battery: Battery
    segment: Segment
    frame_count: int = Field(ge=0)
    started_at: AwareDatetime
