// Encoder and decoder for `.kqk.gz` keypoint files.
//
// Layout (before gzip): "KQK1" · uint32 LE header length · header JSON (UTF-8) ·
// frame_count frames, each int32 LE t_ms + 21 × 4 float32 LE (x, y, z, confidence).

import { gunzipSync, gzipSync } from "fflate";

import type { ScanHeader } from "./header.generated";
import { FRAME_BYTES, JOINT_COUNT, SKELETON_VERSION } from "./skeleton.generated";

const MAGIC = [0x4b, 0x51, 0x4b, 0x31]; // "KQK1"
const PREFIX_BYTES = MAGIC.length + 4;
const VALUES_PER_FRAME = JOINT_COUNT * 4;
const FORMAT_VERSION = 1;

/** The bytes or arrays do not form a valid `.kqk.gz` scan. */
export class KqkError extends Error {
  override name = "KqkError";
}

export interface KqkScan {
  header: ScanHeader;
  /** Milliseconds from scan start, one per frame. */
  tMs: Int32Array;
  /** Flat `frame × joint × (x, y, z, confidence)`, length `frames × 21 × 4`. */
  keypoints: Float32Array;
}

/** Check frame arrays against the `kq-skel-v1` rules; throw `KqkError` if they break one. */
export function validateFrames(tMs: Int32Array, keypoints: Float32Array): void {
  if (keypoints.length !== tMs.length * VALUES_PER_FRAME) {
    throw new KqkError(
      `keypoints must have length ${tMs.length * VALUES_PER_FRAME} (${tMs.length} frames × ${JOINT_COUNT} joints × 4), got ${keypoints.length}`,
    );
  }
  if (tMs.length === 0) return;
  if (tMs[0]! < 0) throw new KqkError("timestamps must not be negative");
  for (let i = 1; i < tMs.length; i++) {
    if (tMs[i]! < tMs[i - 1]!) throw new KqkError("timestamps must not decrease");
  }

  for (let offset = 0; offset < keypoints.length; offset += 4) {
    const x = keypoints[offset]!;
    const y = keypoints[offset + 1]!;
    const z = keypoints[offset + 2]!;
    const confidence = keypoints[offset + 3]!;
    if (!(confidence >= 0 && confidence <= 1)) {
      throw new KqkError("confidence must be between 0 and 1");
    }
    const missing = Number.isNaN(x) || Number.isNaN(y) || Number.isNaN(z);
    if (missing) {
      if (confidence !== 0) {
        throw new KqkError("a joint with NaN coordinates must have confidence 0");
      }
    } else if (!Number.isFinite(x) || !Number.isFinite(y) || !Number.isFinite(z)) {
      throw new KqkError("coordinates must be finite or NaN");
    }
  }
}

/** Serialise a scan to gzip-compressed `.kqk.gz` bytes. */
export function encodeKqk(
  header: ScanHeader,
  tMs: Int32Array,
  keypoints: Float32Array,
): Uint8Array {
  validateFrames(tMs, keypoints);
  if (header.frame_count !== tMs.length) {
    throw new KqkError(
      `header.frame_count is ${header.frame_count} but ${tMs.length} frames were given`,
    );
  }

  const headerBytes = new TextEncoder().encode(JSON.stringify(header));
  const payload = new Uint8Array(PREFIX_BYTES + headerBytes.length + tMs.length * FRAME_BYTES);
  const view = new DataView(payload.buffer);
  payload.set(MAGIC, 0);
  view.setUint32(MAGIC.length, headerBytes.length, true);
  payload.set(headerBytes, PREFIX_BYTES);

  let offset = PREFIX_BYTES + headerBytes.length;
  for (let frame = 0; frame < tMs.length; frame++) {
    view.setInt32(offset, tMs[frame]!, true);
    offset += 4;
    const start = frame * VALUES_PER_FRAME;
    for (let value = 0; value < VALUES_PER_FRAME; value++) {
      view.setFloat32(offset, keypoints[start + value]!, true);
      offset += 4;
    }
  }
  return gzipSync(payload, { mtime: 0 });
}

/**
 * Parse `.kqk.gz` bytes. Header checks here cover only what decoding needs; the
 * backend validates the full header schema.
 */
export function decodeKqk(data: Uint8Array): KqkScan {
  let payload: Uint8Array;
  try {
    payload = gunzipSync(data);
  } catch (error) {
    throw new KqkError(`not valid gzip data: ${String(error)}`);
  }
  if (payload.length < PREFIX_BYTES || !MAGIC.every((byte, i) => payload[i] === byte)) {
    throw new KqkError("not a KQK1 file");
  }

  const view = new DataView(payload.buffer, payload.byteOffset, payload.byteLength);
  const framesStart = PREFIX_BYTES + view.getUint32(MAGIC.length, true);
  if (framesStart > payload.length) throw new KqkError("header length exceeds file size");
  const header = parseHeader(payload.subarray(PREFIX_BYTES, framesStart));

  const frameBytes = payload.length - framesStart;
  if (frameBytes !== header.frame_count * FRAME_BYTES) {
    throw new KqkError(
      `expected ${header.frame_count} frames (${header.frame_count * FRAME_BYTES} bytes), found ${frameBytes} bytes`,
    );
  }

  const tMs = new Int32Array(header.frame_count);
  const keypoints = new Float32Array(header.frame_count * VALUES_PER_FRAME);
  let offset = framesStart;
  for (let frame = 0; frame < header.frame_count; frame++) {
    tMs[frame] = view.getInt32(offset, true);
    offset += 4;
    const start = frame * VALUES_PER_FRAME;
    for (let value = 0; value < VALUES_PER_FRAME; value++) {
      keypoints[start + value] = view.getFloat32(offset, true);
      offset += 4;
    }
  }
  validateFrames(tMs, keypoints);
  return { header, tMs, keypoints };
}

function parseHeader(bytes: Uint8Array): ScanHeader {
  let header: Partial<ScanHeader>;
  try {
    header = JSON.parse(new TextDecoder().decode(bytes)) as Partial<ScanHeader>;
  } catch {
    throw new KqkError("invalid header: not JSON");
  }
  if (
    typeof header !== "object" ||
    header === null ||
    header.format !== "kqk" ||
    header.format_version !== FORMAT_VERSION ||
    header.skeleton !== SKELETON_VERSION
  ) {
    throw new KqkError("invalid header: unsupported format, version or skeleton");
  }
  if (!Number.isInteger(header.frame_count) || header.frame_count! < 0) {
    throw new KqkError("invalid header: frame_count must be a non-negative integer");
  }
  return header as ScanHeader;
}
