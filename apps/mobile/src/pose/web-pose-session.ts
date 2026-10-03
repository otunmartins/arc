// Browser pose capture: webcam → MediaPipe BlazePose → kq-skel-v1 frames.
// Video frames are read by the model in the page and never stored or sent anywhere.

import type { CameraView } from '@kinetiq/contracts';
import type { NormalizedLandmark, PoseLandmarker } from '@mediapipe/tasks-vision';

import { blazePoseToKqSkel, type PoseLandmark } from './blazepose';
import { ScanRecorder } from './recorder';

// The library and wasm versions must match the installed @mediapipe/tasks-vision types.
// TODO: self-host the library, wasm and model files instead of loading them from public CDNs.
const VISION_URL = 'https://cdn.jsdelivr.net/npm/@mediapipe/tasks-vision@1.0.1/vision_bundle.mjs';
const WASM_URL = 'https://cdn.jsdelivr.net/npm/@mediapipe/tasks-vision@1.0.1/wasm';
const MODEL_URL =
  'https://storage.googleapis.com/mediapipe-models/pose_landmarker/pose_landmarker_full/float16/1/pose_landmarker_full.task';
const POSE_MODEL = { id: 'blazepose-full', version: '1', runtime: 'mediapipe' } as const;

// Pairs of BlazePose landmark indices joined by a line in the preview.
const SKELETON_LINES: [number, number][] = [
  [11, 12], [11, 13], [13, 15], [12, 14], [14, 16], [11, 23], [12, 24], [23, 24],
  [23, 25], [25, 27], [27, 29], [29, 31], [27, 31], [24, 26], [26, 28], [28, 30],
  [30, 32], [28, 32],
]; // prettier-ignore

export interface RecordedScan {
  frameCount: number;
  /** The scan as a .kqk.gz file. */
  kqk: Uint8Array;
  /** Raw model output per frame (image-plane and world landmarks) as JSON, for validation work. */
  raw: string;
}

interface RawFrame {
  t_ms: number;
  image: number[][];
  world: number[][];
}

export class WebPoseSession {
  private animationFrame = 0;
  private lastVideoTime = -1;
  private recorder: ScanRecorder | null = null;
  private rawFrames: RawFrame[] = [];
  private recordingStartMs = 0;

  private constructor(
    private readonly video: HTMLVideoElement,
    private readonly canvas: HTMLCanvasElement,
    private readonly stream: MediaStream,
    private readonly landmarker: PoseLandmarker,
    private readonly onFrameCount: (count: number) => void,
  ) {}

  /** Ask for the camera, load the model and start tracking into `canvas`. */
  static async start(
    video: HTMLVideoElement,
    canvas: HTMLCanvasElement,
    onFrameCount: (count: number) => void,
  ): Promise<WebPoseSession> {
    const stream = await navigator.mediaDevices.getUserMedia({
      audio: false,
      video: { width: { ideal: 1280 }, height: { ideal: 720 }, frameRate: { ideal: 30 } },
    });
    try {
      video.srcObject = stream;
      await video.play();
      const { FilesetResolver, PoseLandmarker } = await loadVision();
      const fileset = await FilesetResolver.forVisionTasks(WASM_URL);
      const landmarker = await PoseLandmarker.createFromOptions(fileset, {
        baseOptions: { modelAssetPath: MODEL_URL, delegate: 'GPU' },
        runningMode: 'VIDEO',
        numPoses: 1,
      });
      const session = new WebPoseSession(video, canvas, stream, landmarker, onFrameCount);
      session.tick();
      return session;
    } catch (error) {
      stream.getTracks().forEach((track) => track.stop());
      throw error;
    }
  }

  startRecording(): void {
    this.recorder = new ScanRecorder();
    this.rawFrames = [];
    this.recordingStartMs = performance.now();
  }

  stopRecording(view: CameraView, appVersion: string): RecordedScan | null {
    const recorder = this.recorder;
    this.recorder = null;
    if (!recorder || recorder.frameCount === 0) return null;

    const { videoWidth: width, videoHeight: height } = this.video;
    const kqk = recorder.encode({
      scan_id: crypto.randomUUID(),
      pose_model: POSE_MODEL,
      device: { platform: 'web', model: 'browser', app_version: appVersion },
      camera: {
        fps: this.stream.getVideoTracks()[0]?.getSettings().frameRate ?? 30,
        width,
        height,
        orientation: height > width ? 'portrait' : 'landscape',
        view,
        height_m: null,
        gravity: null, // desktop browsers have no motion sensor
      },
      battery: { id: 'rehab-knee', version: '1' },
      segment: { kind: 'assessment', code: 'pose_spike' },
    });
    return { frameCount: recorder.frameCount, kqk, raw: JSON.stringify(this.rawFrames) };
  }

  close(): void {
    cancelAnimationFrame(this.animationFrame);
    this.stream.getTracks().forEach((track) => track.stop());
    this.video.srcObject = null;
    this.landmarker.close();
  }

  private tick = (): void => {
    const { video } = this;
    if (video.readyState >= 2 && video.currentTime !== this.lastVideoTime) {
      this.lastVideoTime = video.currentTime;
      const now = performance.now();
      const result = this.landmarker.detectForVideo(video, now);
      const image = result.landmarks[0];
      const world = result.worldLandmarks[0];
      this.draw(image);
      if (this.recorder && image && world) {
        this.recorder.add(now, blazePoseToKqSkel(world));
        this.rawFrames.push({
          t_ms: Math.round(now - this.recordingStartMs),
          image: image.map(compact),
          world: world.map(compact),
        });
        this.onFrameCount(this.recorder.frameCount);
      }
    }
    this.animationFrame = requestAnimationFrame(this.tick);
  };

  private draw(image: NormalizedLandmark[] | undefined): void {
    const { canvas, video } = this;
    if (canvas.width !== video.videoWidth) canvas.width = video.videoWidth;
    if (canvas.height !== video.videoHeight) canvas.height = video.videoHeight;
    const context = canvas.getContext('2d');
    if (!context) return;
    context.clearRect(0, 0, canvas.width, canvas.height);
    if (!image) return;

    context.lineWidth = Math.max(2, canvas.width / 320);
    context.strokeStyle = '#3c87f7';
    context.beginPath();
    for (const [from, to] of SKELETON_LINES) {
      const a = image[from];
      const b = image[to];
      if (!a || !b) continue;
      context.moveTo(a.x * canvas.width, a.y * canvas.height);
      context.lineTo(b.x * canvas.width, b.y * canvas.height);
    }
    context.stroke();
  }
}

// Metro cannot bundle @mediapipe/tasks-vision (it contains a computed dynamic import), so
// the browser loads it as a module at run time. `new Function` keeps Metro from rewriting
// the import.
function loadVision(): Promise<typeof import('@mediapipe/tasks-vision')> {
  return new Function('url', 'return import(url)')(VISION_URL);
}

function compact(landmark: PoseLandmark): number[] {
  return [landmark.x, landmark.y, landmark.z, landmark.visibility ?? 0].map(
    (value) => Math.round(value * 1e5) / 1e5,
  );
}
