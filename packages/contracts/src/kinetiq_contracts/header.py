"""Scan header: the JSON block at the start of every `.kqk.gz` file."""

from typing import Literal
from uuid import UUID

from pydantic import AwareDatetime, BaseModel, ConfigDict, Field

PoseRuntime = Literal["tflite", "coreml", "onnx", "mediapipe", "tensorrt"]
Platform = Literal["ios", "android", "web", "edge"]
Orientation = Literal["portrait", "landscape"]
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
    height_m: float | None = Field(gt=0)


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
