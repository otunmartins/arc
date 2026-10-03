import type { ScanHeader } from "../src";
import { JOINT_COUNT } from "../src";

export const FRAME_COUNT = 5;
export const MISSING = { frame: 2, joint: 7 };

export function sampleHeader(frameCount = FRAME_COUNT): ScanHeader {
  return {
    format: "kqk",
    format_version: 1,
    skeleton: "kq-skel-v1",
    scan_id: "00000000-0000-4000-8000-000000000001",
    pose_model: { id: "kq-pose", version: "1.0.0", runtime: "tflite" },
    device: { platform: "ios", model: "iPhone15,3", app_version: "0.1.0" },
    camera: {
      fps: 30,
      width: 1280,
      height: 720,
      orientation: "portrait",
      view: "side_left",
      height_m: null,
      gravity: [0, -1, 0],
    },
    battery: { id: "rehab-knee", version: "1" },
    segment: { kind: "test", code: "sts_30s" },
    frame_count: frameCount,
    started_at: "2026-10-03T09:15:00Z",
  };
}

/** Same formula as `tests/test_kqk.py`, so both languages build identical frames. */
export function sampleFrames(): { tMs: Int32Array; keypoints: Float32Array } {
  const tMs = Int32Array.from({ length: FRAME_COUNT }, (_, i) => i * 33);
  const keypoints = new Float32Array(FRAME_COUNT * JOINT_COUNT * 4);
  for (let i = 0; i < FRAME_COUNT; i++) {
    for (let j = 0; j < JOINT_COUNT; j++) {
      const missing = i === MISSING.frame && j === MISSING.joint;
      keypoints.set(
        missing
          ? [NaN, NaN, NaN, 0]
          : [i + j * 0.01, i * 0.5 - j * 0.02, 2 + i * 0.25, ((i + j) % 5) / 4],
        (i * JOINT_COUNT + j) * 4,
      );
    }
  }
  return { tMs, keypoints };
}
