import { JOINTS } from '@kinetiq/contracts';
import { describe, expect, it } from 'vitest';

import { blazePoseToKqSkel, type PoseLandmark } from './blazepose';

/** 33 landmarks where landmark `i` sits at (i, 10 + i, 20 + i) with full visibility. */
function landmarks(): PoseLandmark[] {
  return Array.from({ length: 33 }, (_, i) => ({ x: i, y: 10 + i, z: 20 + i, visibility: 1 }));
}

function joint(frame: Float32Array, name: (typeof JOINTS)[number]): number[] {
  const start = JOINTS.indexOf(name) * 4;
  return Array.from(frame.slice(start, start + 4));
}

describe('blazePoseToKqSkel', () => {
  it('copies direct joints and flips y and z', () => {
    const frame = blazePoseToKqSkel(landmarks());
    expect(frame).toHaveLength(84);
    expect(joint(frame, 'left_knee')).toEqual([25, -35, -45, 1]);
    expect(joint(frame, 'right_knee')).toEqual([26, -36, -46, 1]);
    expect(joint(frame, 'left_shoulder')).toEqual([11, -21, -31, 1]);
    expect(joint(frame, 'right_wrist')).toEqual([16, -26, -36, 1]);
    expect(joint(frame, 'left_heel')).toEqual([29, -39, -49, 1]);
    expect(joint(frame, 'right_foot_index')).toEqual([32, -42, -52, 1]);
  });

  it('derives the trunk and head joints', () => {
    const frame = blazePoseToKqSkel(landmarks());
    expect(joint(frame, 'pelvis')).toEqual([23.5, -33.5, -43.5, 1]); // between the hips
    expect(joint(frame, 'neck')).toEqual([11.5, -21.5, -31.5, 1]); // between the shoulders
    expect(joint(frame, 'spine_mid')).toEqual([17.5, -27.5, -37.5, 1]); // halfway up
    expect(joint(frame, 'chest')).toEqual([14.5, -24.5, -34.5, 1]); // three quarters up
    expect(joint(frame, 'head')).toEqual([7.5, -17.5, -27.5, 1]); // between the ears
  });

  it('uses visibility as confidence, clamped to 0..1', () => {
    const input = landmarks();
    input[25]!.visibility = 0.4;
    input[26]!.visibility = 1.7;
    input[27]!.visibility = undefined;
    const frame = blazePoseToKqSkel(input);
    expect(joint(frame, 'left_knee')[3]).toBeCloseTo(0.4);
    expect(joint(frame, 'right_knee')[3]).toBe(1);
    expect(joint(frame, 'left_ankle')[3]).toBe(0);
  });

  it('gives a derived joint the confidence of its weaker source', () => {
    const input = landmarks();
    input[24]!.visibility = 0.25; // right hip, as when hidden in a side-on view
    const frame = blazePoseToKqSkel(input);
    expect(joint(frame, 'pelvis')[3]).toBe(0.25);
    expect(joint(frame, 'spine_mid')[3]).toBe(0.25);
    expect(joint(frame, 'neck')[3]).toBe(1);
  });

  it('marks a joint without finite coordinates as missing', () => {
    const input = landmarks();
    input[23]!.x = NaN;
    const frame = blazePoseToKqSkel(input);
    expect(joint(frame, 'left_hip')).toEqual([NaN, NaN, NaN, 0]);
    expect(joint(frame, 'pelvis')).toEqual([NaN, NaN, NaN, 0]);
    expect(joint(frame, 'chest')).toEqual([NaN, NaN, NaN, 0]);
    expect(joint(frame, 'right_hip')[3]).toBe(1);
  });

  it('rejects anything that is not 33 landmarks', () => {
    expect(() => blazePoseToKqSkel(landmarks().slice(0, 17))).toThrow(/33/);
  });
});
