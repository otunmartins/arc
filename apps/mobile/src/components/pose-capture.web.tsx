import type { CameraView } from '@kinetiq/contracts';
import Constants from 'expo-constants';
import { useEffect, useRef, useState } from 'react';
import { Pressable, StyleSheet, View } from 'react-native';

import { ThemedText } from './themed-text';
import { ThemedView } from './themed-view';

import { Spacing } from '@/constants/theme';
import { WebPoseSession } from '@/pose/web-pose-session';

type Status = 'idle' | 'loading' | 'ready' | 'recording';

const VIEWS: { value: CameraView; label: string }[] = [
  { value: 'side_left', label: 'Left side' },
  { value: 'side_right', label: 'Right side' },
  { value: 'front', label: 'Front' },
];

const APP_VERSION = Constants.expoConfig?.version ?? '0.0.0';

export default function PoseCapture() {
  const videoRef = useRef<HTMLVideoElement>(null);
  const canvasRef = useRef<HTMLCanvasElement>(null);
  const [session, setSession] = useState<WebPoseSession | null>(null);
  const [status, setStatus] = useState<Status>('idle');
  const [message, setMessage] = useState<string | null>(null);
  const [view, setView] = useState<CameraView>('side_left');
  const [frameCount, setFrameCount] = useState(0);

  useEffect(() => () => session?.close(), [session]);

  async function startCamera() {
    if (!videoRef.current || !canvasRef.current) return;
    setStatus('loading');
    setMessage(null);
    try {
      setSession(await WebPoseSession.start(videoRef.current, canvasRef.current, setFrameCount));
      setStatus('ready');
    } catch (error) {
      setMessage(error instanceof Error ? error.message : String(error));
      setStatus('idle');
    }
  }

  function toggleRecording() {
    if (!session) return;
    if (status !== 'recording') {
      setFrameCount(0);
      setMessage(null);
      session.startRecording();
      setStatus('recording');
      return;
    }
    const scan = session.stopRecording(view, APP_VERSION);
    setStatus('ready');
    if (!scan) {
      setMessage('No frames with a person in view were recorded.');
      return;
    }
    const name = `scan-${new Date().toISOString().replace(/[:.]/g, '-')}`;
    download(`${name}.kqk.gz`, scan.kqk, 'application/gzip');
    download(`${name}.raw.json`, scan.raw, 'application/json');
    setMessage(`Saved ${scan.frameCount} frames.`);
  }

  return (
    <View style={styles.container}>
      <View style={styles.stage}>
        <video ref={videoRef} style={mediaStyle} muted playsInline />
        <canvas ref={canvasRef} style={mediaStyle} />
      </View>

      <View style={styles.row}>
        {VIEWS.map(({ value, label }) => (
          <Pressable key={value} disabled={status === 'recording'} onPress={() => setView(value)}>
            <ThemedView
              type={view === value ? 'backgroundSelected' : 'backgroundElement'}
              style={styles.button}>
              <ThemedText type="small">{label}</ThemedText>
            </ThemedView>
          </Pressable>
        ))}
      </View>

      <View style={styles.row}>
        {status === 'idle' || status === 'loading' ? (
          <Pressable disabled={status === 'loading'} onPress={startCamera}>
            <ThemedView type="backgroundSelected" style={styles.button}>
              <ThemedText type="smallBold">
                {status === 'loading' ? 'Loading camera and model…' : 'Start camera'}
              </ThemedText>
            </ThemedView>
          </Pressable>
        ) : (
          <Pressable onPress={toggleRecording}>
            <ThemedView type="backgroundSelected" style={styles.button}>
              <ThemedText type="smallBold">
                {status === 'recording' ? `Stop and save (${frameCount} frames)` : 'Record'}
              </ThemedText>
            </ThemedView>
          </Pressable>
        )}
      </View>

      {message && (
        <ThemedText type="small" themeColor="textSecondary">
          {message}
        </ThemedText>
      )}
    </View>
  );
}

function download(name: string, content: Uint8Array | string, type: string) {
  const part = typeof content === 'string' ? content : new Uint8Array(content);
  const url = URL.createObjectURL(new Blob([part], { type }));
  const link = document.createElement('a');
  link.href = url;
  link.download = name;
  link.click();
  URL.revokeObjectURL(url);
}

const mediaStyle = {
  position: 'absolute',
  inset: 0,
  width: '100%',
  height: '100%',
  objectFit: 'contain',
} as const;

const styles = StyleSheet.create({
  container: {
    alignSelf: 'stretch',
    gap: Spacing.three,
  },
  stage: {
    aspectRatio: 16 / 9,
    backgroundColor: '#000000',
    borderRadius: Spacing.three,
    overflow: 'hidden',
  },
  row: {
    flexDirection: 'row',
    flexWrap: 'wrap',
    gap: Spacing.two,
  },
  button: {
    paddingVertical: Spacing.two,
    paddingHorizontal: Spacing.three,
    borderRadius: Spacing.three,
  },
});
