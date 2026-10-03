import { decodeKqk } from '@kinetiq/contracts';
import { describe, expect, it } from 'vitest';

import { blazePoseToKqSkel } from './blazepose';
import { ScanRecorder, type ScanInfo } from './recorder';

const INFO: ScanInfo = {
  scan_id: '00000000-0000-4000-8000-000000000002',
  pose_model: { id: 'blazepose-full', version: '1', runtime: 'mediapipe' },
  device: { platform: 'web', model: 'browser', app_version: '1.0.0' },
  camera: {
    fps: 30,
    width: 1280,
    height: 720,
    orientation: 'landscape',
    view: 'side_left',
    height_m: null,
    gravity: null,
  },
  battery: { id: 'rehab-knee', version: '1' },
  segment: { kind: 'assessment', code: 'pose_spike' },
};

function frame(offset: number): Float32Array {
  return blazePoseToKqSkel(
    Array.from({ length: 33 }, (_, i) => ({ x: i + offset, y: i, z: i, visibility: 0.9 })),
  );
}

describe('ScanRecorder', () => {
  it('produces a file the contract decoder accepts', () => {
    const recorder = new ScanRecorder();
    recorder.add(5000.2, frame(0));
    recorder.add(5033.6, frame(1));
    recorder.add(5066.9, frame(2));
    expect(recorder.frameCount).toBe(3);

    const scan = decodeKqk(recorder.encode(INFO));
    expect(scan.header.frame_count).toBe(3);
    expect(scan.header.skeleton).toBe('kq-skel-v1');
    expect(scan.header.camera.view).toBe('side_left');
    expect(Array.from(scan.tMs)).toEqual([0, 33, 67]);
    expect(scan.keypoints.slice(0, 84)).toEqual(frame(0));
    expect(scan.keypoints.slice(168)).toEqual(frame(2));
    expect(Number.isNaN(Date.parse(scan.header.started_at))).toBe(false);
  });

  it('never lets timestamps go backwards', () => {
    const recorder = new ScanRecorder();
    recorder.add(100, frame(0));
    recorder.add(140, frame(0));
    recorder.add(120, frame(0));
    expect(Array.from(decodeKqk(recorder.encode(INFO)).tMs)).toEqual([0, 40, 40]);
  });

  it('encodes an empty scan', () => {
    const scan = decodeKqk(new ScanRecorder().encode(INFO));
    expect(scan.header.frame_count).toBe(0);
    expect(scan.tMs).toHaveLength(0);
  });

  it('rejects a frame of the wrong size', () => {
    expect(() => new ScanRecorder().add(0, new Float32Array(10))).toThrow(/84/);
  });
});
