import { ThemedText } from './themed-text';

// Native capture (VisionCamera + on-device pose) is not built yet; see pose-capture.web.tsx.
export default function PoseCapture() {
  return (
    <ThemedText themeColor="textSecondary">
      Pose capture is not available on iOS and Android yet. Open the web build to try it.
    </ThemedText>
  );
}
