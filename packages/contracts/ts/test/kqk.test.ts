import { readFileSync, writeFileSync } from "node:fs";
import { fileURLToPath } from "node:url";

import { gunzipSync, gzipSync } from "fflate";
import { describe, expect, it } from "vitest";

import { FRAME_BYTES, JOINTS, JOINT_COUNT, KqkError, decodeKqk, encodeKqk, validateFrames } from "../src";
import { FRAME_COUNT, sampleFrames, sampleHeader } from "./sample";

const fixture = (name: string) => fileURLToPath(new URL(`../../fixtures/${name}`, import.meta.url));

function expectSample(data: Uint8Array): void {
  const scan = decodeKqk(data);
  const { tMs, keypoints } = sampleFrames();
  expect(scan.header).toEqual(sampleHeader());
  expect(scan.tMs).toEqual(tMs);
  expect(scan.keypoints).toEqual(keypoints);
}

function encodeSample(): Uint8Array {
  const { tMs, keypoints } = sampleFrames();
  return encodeKqk(sampleHeader(), tMs, keypoints);
}

describe("skeleton", () => {
  it("matches the spec", () => {
    expect(JOINT_COUNT).toBe(21);
    expect(JOINTS).toHaveLength(21);
    expect(FRAME_BYTES).toBe(340);
    expect(JOINTS[13]).toBe("left_knee");
  });
});

describe("kqk codec", () => {
  it("round-trips", () => {
    expectSample(encodeSample());
  });

  it("writes the layout in the spec", () => {
    const payload = gunzipSync(encodeSample());
    const view = new DataView(payload.buffer, payload.byteOffset, payload.byteLength);
    const headerLength = view.getUint32(4, true);
    expect(new TextDecoder().decode(payload.subarray(0, 4))).toBe("KQK1");
    expect(payload.length).toBe(8 + headerLength + FRAME_COUNT * FRAME_BYTES);
    const second = 8 + headerLength + FRAME_BYTES;
    expect(view.getInt32(second, true)).toBe(33);
    expect(view.getFloat32(second + 4, true)).toBe(1);
    expect(view.getFloat32(second + 16, true)).toBe(0.25);
  });

  it("matches its committed fixture", () => {
    const path = fixture("ts-v1.kqk.gz");
    if (process.env.UPDATE_FIXTURES) writeFileSync(path, encodeSample());
    expectSample(readFileSync(path));
  });

  it("reads a file written by Python", () => {
    expectSample(readFileSync(fixture("py-v1.kqk.gz")));
  });

  it("rejects a frame count that differs from the header", () => {
    const { tMs, keypoints } = sampleFrames();
    expect(() => encodeKqk(sampleHeader(4), tMs, keypoints)).toThrow(KqkError);
  });

  it("rejects decreasing timestamps", () => {
    const { tMs, keypoints } = sampleFrames();
    tMs[3] = 10;
    expect(() => validateFrames(tMs, keypoints)).toThrow(/decrease/);
  });

  it("rejects confidence out of range", () => {
    const { tMs, keypoints } = sampleFrames();
    keypoints[3] = 1.5;
    expect(() => validateFrames(tMs, keypoints)).toThrow(/confidence/);
  });

  it("rejects NaN coordinates with non-zero confidence", () => {
    const { tMs, keypoints } = sampleFrames();
    keypoints[(JOINT_COUNT + 5) * 4] = NaN;
    expect(() => validateFrames(tMs, keypoints)).toThrow(/NaN/);
  });

  it("rejects infinite coordinates", () => {
    const { tMs, keypoints } = sampleFrames();
    keypoints[2] = Infinity;
    expect(() => validateFrames(tMs, keypoints)).toThrow(/finite/);
  });

  it("rejects non-gzip data", () => {
    expect(() => decodeKqk(new TextEncoder().encode("not a gzip file"))).toThrow(/gzip/);
  });

  it("rejects a bad magic", () => {
    expect(() => decodeKqk(gzipSync(new Uint8Array(24)))).toThrow(/KQK1/);
  });

  it("rejects an unknown skeleton", () => {
    const header = JSON.stringify({ ...sampleHeader(0), skeleton: "other" });
    const headerBytes = new TextEncoder().encode(header);
    const payload = new Uint8Array(8 + headerBytes.length);
    payload.set([0x4b, 0x51, 0x4b, 0x31]);
    new DataView(payload.buffer).setUint32(4, headerBytes.length, true);
    payload.set(headerBytes, 8);
    expect(() => decodeKqk(gzipSync(payload))).toThrow(/invalid header/);
  });
});
