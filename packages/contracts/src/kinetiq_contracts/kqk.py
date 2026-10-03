"""Encoder and decoder for `.kqk.gz` keypoint files.

Layout (before gzip): `"KQK1"` · uint32 LE header length · header JSON (UTF-8) ·
`frame_count` frames, each int32 LE `t_ms` + 21 × 4 float32 LE (x, y, z, confidence).
"""

import struct
import zlib
from dataclasses import dataclass

import numpy as np
from numpy.typing import NDArray
from pydantic import ValidationError

from .header import ScanHeader
from .skeleton import JOINT_COUNT

MAGIC = b"KQK1"
FORMAT_VERSION = 1
FRAME_BYTES = 4 + JOINT_COUNT * 4 * 4
DEFAULT_MAX_BYTES = 64 * 1024 * 1024

_FRAME_DTYPE = np.dtype([("t_ms", "<i4"), ("kp", "<f4", (JOINT_COUNT, 4))])
_PREFIX_BYTES = len(MAGIC) + 4


class KqkError(ValueError):
    """The bytes or arrays do not form a valid `.kqk.gz` scan."""


@dataclass(frozen=True)
class KqkScan:
    header: ScanHeader
    t_ms: NDArray[np.int32]  # shape (frame_count,)
    keypoints: NDArray[np.float32]  # shape (frame_count, 21, 4): x, y, z, confidence


def validate_frames(t_ms: NDArray[np.int32], keypoints: NDArray[np.float32]) -> None:
    """Check frame arrays against the `kq-skel-v1` rules; raise `KqkError` if they break one."""
    if t_ms.ndim != 1:
        raise KqkError("t_ms must be one-dimensional")
    if keypoints.shape != (t_ms.shape[0], JOINT_COUNT, 4):
        raise KqkError(
            f"keypoints must have shape ({t_ms.shape[0]}, {JOINT_COUNT}, 4), got {keypoints.shape}"
        )
    if t_ms.shape[0] == 0:
        return
    if int(t_ms[0]) < 0:
        raise KqkError("timestamps must not be negative")
    if bool(np.any(np.diff(t_ms.astype(np.int64)) < 0)):
        raise KqkError("timestamps must not decrease")

    xyz = keypoints[..., :3]
    confidence = keypoints[..., 3]
    if bool(np.any(np.isinf(xyz))):
        raise KqkError("coordinates must be finite or NaN")
    if not bool(np.all((confidence >= 0) & (confidence <= 1))):
        raise KqkError("confidence must be between 0 and 1")
    missing = np.any(np.isnan(xyz), axis=-1)
    if bool(np.any(missing & (confidence != 0))):
        raise KqkError("a joint with NaN coordinates must have confidence 0")


def encode_kqk(
    header: ScanHeader, t_ms: NDArray[np.int32], keypoints: NDArray[np.float32]
) -> bytes:
    """Serialise a scan to gzip-compressed `.kqk.gz` bytes."""
    validate_frames(t_ms, keypoints)
    if header.frame_count != t_ms.shape[0]:
        raise KqkError(
            f"header.frame_count is {header.frame_count} but {t_ms.shape[0]} frames were given"
        )

    frames = np.empty(t_ms.shape[0], dtype=_FRAME_DTYPE)
    frames["t_ms"] = t_ms
    frames["kp"] = keypoints
    header_json = header.model_dump_json().encode("utf-8")
    payload = MAGIC + struct.pack("<I", len(header_json)) + header_json + frames.tobytes()

    compressor = zlib.compressobj(wbits=31)
    return compressor.compress(payload) + compressor.flush()


def decode_kqk(data: bytes, *, max_bytes: int = DEFAULT_MAX_BYTES) -> KqkScan:
    """Parse and validate `.kqk.gz` bytes.

    `max_bytes` caps the decompressed size so a hostile upload cannot exhaust memory.
    """
    payload = _gunzip(data, max_bytes)
    if len(payload) < _PREFIX_BYTES or payload[: len(MAGIC)] != MAGIC:
        raise KqkError("not a KQK1 file")

    (header_length,) = struct.unpack_from("<I", payload, len(MAGIC))
    frames_start = _PREFIX_BYTES + header_length
    if frames_start > len(payload):
        raise KqkError("header length exceeds file size")
    try:
        header = ScanHeader.model_validate_json(payload[_PREFIX_BYTES:frames_start])
    except ValidationError as exc:
        raise KqkError(f"invalid header: {exc}") from exc

    frame_bytes = len(payload) - frames_start
    if frame_bytes != header.frame_count * FRAME_BYTES:
        raise KqkError(
            f"expected {header.frame_count} frames ({header.frame_count * FRAME_BYTES} bytes), "
            f"found {frame_bytes} bytes"
        )

    frames = np.frombuffer(payload, dtype=_FRAME_DTYPE, offset=frames_start)
    t_ms = frames["t_ms"].astype(np.int32)
    keypoints = frames["kp"].astype(np.float32)
    validate_frames(t_ms, keypoints)
    return KqkScan(header=header, t_ms=t_ms, keypoints=keypoints)


def _gunzip(data: bytes, max_bytes: int) -> bytes:
    decompressor = zlib.decompressobj(wbits=31)
    try:
        payload = decompressor.decompress(data, max_bytes + 1)
    except zlib.error as exc:
        raise KqkError(f"not valid gzip data: {exc}") from exc
    if len(payload) > max_bytes:
        raise KqkError(f"decompressed size exceeds {max_bytes} bytes")
    if not decompressor.eof:
        raise KqkError("gzip stream is truncated")
    return payload
