// Maps MediaPipe BlazePose world landmarks (33 points) onto the canonical kq-skel-v1
// skeleton (21 joints). The mapping is documented in features/data/DATA.md.

import { JOINTS, JOINT_COUNT, type Joint } from '@kinetiq/contracts';

export const BLAZEPOSE_LANDMARK_COUNT = 33;

/** One BlazePose landmark: metres, x to the camera's right, y down, z away from the camera. */
export interface PoseLandmark {
  x: number;
  y: number;
  z: number;
  visibility?: number;
}

const DIRECT: Partial<Record<Joint, number>> = {
  left_shoulder: 11,
  right_shoulder: 12,
  left_elbow: 13,
  right_elbow: 14,
  left_wrist: 15,
  right_wrist: 16,
  left_hip: 23,
  right_hip: 24,
  left_knee: 25,
  right_knee: 26,
  left_ankle: 27,
  right_ankle: 28,
  left_heel: 29,
  right_heel: 30,
  left_foot_index: 31,
  right_foot_index: 32,
};

const LEFT_EAR = 7;
const RIGHT_EAR = 8;
const LEFT_SHOULDER = 11;
const RIGHT_SHOULDER = 12;
const LEFT_HIP = 23;
const RIGHT_HIP = 24;

// Fractions of the way from pelvis to neck.
const SPINE_MID_FRACTION = 0.5;
const CHEST_FRACTION = 0.75;

type Point = [x: number, y: number, z: number, confidence: number];

const MISSING: Point = [NaN, NaN, NaN, 0];

/**
 * Convert one frame of BlazePose world landmarks to a kq-skel-v1 frame: 21 joints ×
 * (x, y, z, confidence), with +Y up and +Z toward the camera. The origin stays at the
 * hip centre, where BlazePose puts it.
 */
export function blazePoseToKqSkel(world: readonly PoseLandmark[]): Float32Array {
  if (world.length !== BLAZEPOSE_LANDMARK_COUNT) {
    throw new Error(`expected ${BLAZEPOSE_LANDMARK_COUNT} landmarks, got ${world.length}`);
  }

  const pelvis = between(point(world[LEFT_HIP]!), point(world[RIGHT_HIP]!), 0.5);
  const neck = between(point(world[LEFT_SHOULDER]!), point(world[RIGHT_SHOULDER]!), 0.5);
  const derived: Partial<Record<Joint, Point>> = {
    pelvis,
    neck,
    spine_mid: between(pelvis, neck, SPINE_MID_FRACTION),
    chest: between(pelvis, neck, CHEST_FRACTION),
    head: between(point(world[LEFT_EAR]!), point(world[RIGHT_EAR]!), 0.5),
  };

  const frame = new Float32Array(JOINT_COUNT * 4);
  JOINTS.forEach((joint, index) => {
    const source = DIRECT[joint];
    frame.set(source === undefined ? derived[joint]! : point(world[source]!), index * 4);
  });
  return frame;
}

function point(landmark: PoseLandmark): Point {
  const { x, y, z } = landmark;
  if (!Number.isFinite(x) || !Number.isFinite(y) || !Number.isFinite(z)) return MISSING;
  const visibility = landmark.visibility ?? 0;
  const confidence = Number.isFinite(visibility) ? Math.min(1, Math.max(0, visibility)) : 0;
  return [x, -y, -z, confidence];
}

/** Point `fraction` of the way from `a` to `b`; as confident as the less confident end. */
function between(a: Point, b: Point, fraction: number): Point {
  if (Number.isNaN(a[0]) || Number.isNaN(b[0])) return MISSING;
  return [
    a[0] + (b[0] - a[0]) * fraction,
    a[1] + (b[1] - a[1]) * fraction,
    a[2] + (b[2] - a[2]) * fraction,
    Math.min(a[3], b[3]),
  ];
}
