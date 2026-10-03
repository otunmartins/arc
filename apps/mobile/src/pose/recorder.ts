// Collects kq-skel-v1 frames during a scan and encodes them as a .kqk.gz file.

import { FRAME_BYTES, encodeKqk, type ScanHeader } from '@kinetiq/contracts';

const VALUES_PER_FRAME = (FRAME_BYTES - 4) / 4;

/** Everything in the scan header that the recorder cannot work out from the frames. */
export type ScanInfo = Omit<
  ScanHeader,
  'format' | 'format_version' | 'skeleton' | 'frame_count' | 'started_at'
>;

export class ScanRecorder {
  private readonly times: number[] = [];
  private readonly frames: Float32Array[] = [];
  private firstTimeMs: number | null = null;
  private startedAt: Date | null = null;

  get frameCount(): number {
    return this.times.length;
  }

  /** Add a frame. `timeMs` is any monotonic clock; the first frame becomes time zero. */
  add(timeMs: number, frame: Float32Array): void {
    if (frame.length !== VALUES_PER_FRAME) {
      throw new Error(`expected ${VALUES_PER_FRAME} values per frame, got ${frame.length}`);
    }
    if (this.firstTimeMs === null) {
      this.firstTimeMs = timeMs;
      this.startedAt = new Date();
    }
    const previous = this.times.at(-1) ?? 0;
    this.times.push(Math.max(previous, Math.round(timeMs - this.firstTimeMs)));
    this.frames.push(frame);
  }

  /** Build the header and return the gzip-compressed file. */
  encode(info: ScanInfo): Uint8Array {
    const keypoints = new Float32Array(this.frames.length * VALUES_PER_FRAME);
    this.frames.forEach((frame, index) => keypoints.set(frame, index * VALUES_PER_FRAME));
    const header: ScanHeader = {
      format: 'kqk',
      format_version: 1,
      skeleton: 'kq-skel-v1',
      ...info,
      frame_count: this.frames.length,
      started_at: (this.startedAt ?? new Date()).toISOString(),
    };
    return encodeKqk(header, Int32Array.from(this.times), keypoints);
  }
}
