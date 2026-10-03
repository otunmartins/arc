import gzip
import importlib.util
import os
import struct
from datetime import UTC, datetime
from pathlib import Path
from uuid import UUID

import numpy as np
import pytest

from kinetiq_contracts import (
    FRAME_BYTES,
    JOINT_COUNT,
    JOINT_INDEX,
    JOINTS,
    MAGIC,
    KqkError,
    ScanHeader,
    decode_kqk,
    encode_kqk,
    validate_frames,
)

PACKAGE_ROOT = Path(__file__).parent.parent
FIXTURES = PACKAGE_ROOT / "fixtures"
FRAME_COUNT = 5
MISSING = (2, 7)  # frame, joint


def sample_header(frame_count: int = FRAME_COUNT) -> ScanHeader:
    return ScanHeader.model_validate(
        {
            "format": "kqk",
            "format_version": 1,
            "skeleton": "kq-skel-v1",
            "scan_id": UUID("00000000-0000-4000-8000-000000000001"),
            "pose_model": {"id": "kq-pose", "version": "1.0.0", "runtime": "tflite"},
            "device": {"platform": "ios", "model": "iPhone15,3", "app_version": "0.1.0"},
            "camera": {
                "fps": 30,
                "width": 1280,
                "height": 720,
                "orientation": "portrait",
                "view": "side_left",
                "height_m": None,
                "gravity": [0, -1, 0],
            },
            "battery": {"id": "rehab-knee", "version": "1"},
            "segment": {"kind": "test", "code": "sts_30s"},
            "frame_count": frame_count,
            "started_at": datetime(2026, 10, 3, 9, 15, tzinfo=UTC),
        }
    )


def sample_frames() -> tuple[np.ndarray, np.ndarray]:
    """Same formula as `ts/test/sample.ts`, so both languages build identical frames."""
    t_ms = np.arange(FRAME_COUNT, dtype=np.int32) * 33
    keypoints = np.empty((FRAME_COUNT, JOINT_COUNT, 4), dtype=np.float32)
    for i in range(FRAME_COUNT):
        for j in range(JOINT_COUNT):
            keypoints[i, j] = (i + j * 0.01, i * 0.5 - j * 0.02, 2 + i * 0.25, ((i + j) % 5) / 4)
    keypoints[MISSING] = (np.nan, np.nan, np.nan, 0)
    return t_ms, keypoints


def assert_is_sample(data: bytes) -> None:
    scan = decode_kqk(data)
    t_ms, keypoints = sample_frames()
    assert scan.header == sample_header()
    assert np.array_equal(scan.t_ms, t_ms)
    assert np.array_equal(scan.keypoints, keypoints, equal_nan=True)


def raw_file(header_json: bytes, frames: bytes) -> bytes:
    return gzip.compress(MAGIC + struct.pack("<I", len(header_json)) + header_json + frames)


def test_skeleton_matches_spec() -> None:
    assert JOINT_COUNT == 21
    assert FRAME_BYTES == 340
    assert JOINTS[0] == "pelvis"
    assert JOINT_INDEX["left_knee"] == 13
    assert JOINT_INDEX["right_foot_index"] == 20


def test_round_trip() -> None:
    assert_is_sample(encode_kqk(sample_header(), *sample_frames()))


def test_layout_matches_spec() -> None:
    payload = gzip.decompress(encode_kqk(sample_header(), *sample_frames()))
    (header_length,) = struct.unpack_from("<I", payload, 4)
    assert payload[:4] == b"KQK1"
    assert len(payload) == 8 + header_length + FRAME_COUNT * FRAME_BYTES
    # Second frame: t_ms then joint 0 as x, y, z, confidence.
    second = struct.unpack_from("<i4f", payload, 8 + header_length + FRAME_BYTES)
    assert second == (33, 1.0, 0.5, 2.25, 0.25)


def test_empty_scan_round_trips() -> None:
    header = sample_header(frame_count=0)
    empty_t = np.empty(0, dtype=np.int32)
    empty_kp = np.empty((0, JOINT_COUNT, 4), dtype=np.float32)
    scan = decode_kqk(encode_kqk(header, empty_t, empty_kp))
    assert scan.t_ms.shape == (0,)
    assert scan.keypoints.shape == (0, JOINT_COUNT, 4)


def test_python_fixture() -> None:
    path = FIXTURES / "py-v1.kqk.gz"
    if os.environ.get("UPDATE_FIXTURES"):
        path.write_bytes(encode_kqk(sample_header(), *sample_frames()))
    assert_is_sample(path.read_bytes())


def test_reads_file_written_by_typescript() -> None:
    assert_is_sample((FIXTURES / "ts-v1.kqk.gz").read_bytes())


def test_committed_schema_is_current() -> None:
    spec = importlib.util.spec_from_file_location("contracts_build", PACKAGE_ROOT / "build.py")
    assert spec is not None and spec.loader is not None
    build = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(build)
    assert build.SCHEMA_PATH.read_text(encoding="utf-8") == build.header_schema_json()
    generated = (build.TS_SRC / "skeleton.generated.ts").read_text(encoding="utf-8")
    assert generated == build.skeleton_ts()


def test_rejects_wrong_frame_count() -> None:
    t_ms, keypoints = sample_frames()
    with pytest.raises(KqkError, match="frame_count"):
        encode_kqk(sample_header(frame_count=4), t_ms, keypoints)


def test_rejects_decreasing_timestamps() -> None:
    t_ms, keypoints = sample_frames()
    t_ms[3] = 10
    with pytest.raises(KqkError, match="decrease"):
        validate_frames(t_ms, keypoints)


def test_rejects_confidence_out_of_range() -> None:
    t_ms, keypoints = sample_frames()
    keypoints[0, 0, 3] = 1.5
    with pytest.raises(KqkError, match="confidence"):
        validate_frames(t_ms, keypoints)


def test_rejects_nan_coordinates_with_confidence() -> None:
    t_ms, keypoints = sample_frames()
    keypoints[1, 5, 0] = np.nan
    with pytest.raises(KqkError, match="NaN"):
        validate_frames(t_ms, keypoints)


def test_rejects_infinite_coordinates() -> None:
    t_ms, keypoints = sample_frames()
    keypoints[1, 4, 2] = np.inf
    with pytest.raises(KqkError, match="finite"):
        validate_frames(t_ms, keypoints)


def test_rejects_wrong_shape() -> None:
    t_ms, keypoints = sample_frames()
    with pytest.raises(KqkError, match="shape"):
        validate_frames(t_ms, keypoints[:, :20])


def test_rejects_non_gzip() -> None:
    with pytest.raises(KqkError, match="gzip"):
        decode_kqk(b"not a gzip file")


def test_rejects_truncated_gzip() -> None:
    data = encode_kqk(sample_header(), *sample_frames())
    with pytest.raises(KqkError):
        decode_kqk(data[: len(data) // 2])


def test_rejects_bad_magic() -> None:
    with pytest.raises(KqkError, match="KQK1"):
        decode_kqk(gzip.compress(b"NOPE" + bytes(20)))


def test_rejects_oversized_payload() -> None:
    data = encode_kqk(sample_header(), *sample_frames())
    with pytest.raises(KqkError, match="exceeds"):
        decode_kqk(data, max_bytes=100)


def test_rejects_frame_bytes_not_matching_header() -> None:
    header_json = sample_header().model_dump_json().encode()
    with pytest.raises(KqkError, match="expected 5 frames"):
        decode_kqk(raw_file(header_json, bytes(FRAME_BYTES * 4)))


def test_rejects_header_length_past_end() -> None:
    with pytest.raises(KqkError, match="header length"):
        decode_kqk(gzip.compress(MAGIC + struct.pack("<I", 9999) + b"{}"))


def test_rejects_unknown_skeleton() -> None:
    header_json = sample_header(frame_count=0).model_dump_json().replace("kq-skel-v1", "other")
    with pytest.raises(KqkError, match="invalid header"):
        decode_kqk(raw_file(header_json.encode(), b""))


def test_gravity_may_be_unknown_but_must_be_a_unit_vector() -> None:
    header = sample_header().model_dump()
    header["camera"]["gravity"] = None
    assert ScanHeader.model_validate(header).camera.gravity is None
    header["camera"]["gravity"] = [0.0, -0.6, -0.8]
    assert ScanHeader.model_validate(header).camera.gravity == [0.0, -0.6, -0.8]
    for bad in ([0.0, -9.81, 0.0], [0.0, 0.0, 0.0], [0.0, float("nan"), 0.0], [0.0, -1.0]):
        header["camera"]["gravity"] = bad
        with pytest.raises(ValueError):
            ScanHeader.model_validate(header)


def test_rejects_unknown_header_field() -> None:
    header_json = sample_header(frame_count=0).model_dump_json()[:-1] + ',"video_url":"x"}'
    with pytest.raises(KqkError, match="invalid header"):
        decode_kqk(raw_file(header_json.encode(), b""))
