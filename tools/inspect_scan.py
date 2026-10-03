"""Print capture quality and metrics for a `.kqk.gz` scan.

    uv run python tools/inspect_scan.py path/to/scan.kqk.gz

Angles are shown in degrees for reading; stored values stay in radians.
"""

import math
import sys
from pathlib import Path

from kinetiq_contracts import decode_kqk
from kinetiq_core import angles, assess_quality, metrics, prepare

SIDED = (
    metrics.knee_flexion_peak,
    metrics.knee_extension_deficit,
    metrics.hip_flexion_peak,
    metrics.shoulder_abduction_peak,
    metrics.knee_valgus_peak,
)


def main(path: Path) -> None:
    scan = decode_kqk(path.read_bytes())
    header = scan.header
    quality = assess_quality(scan.t_ms, scan.keypoints)
    print(f"scan       {header.scan_id}")
    print(
        f"model      {header.pose_model.id} {header.pose_model.version} ({header.device.platform})"
    )
    print(f"view       {header.camera.view}, gravity {header.camera.gravity}")
    print(
        f"frames     {quality.frame_count} over {quality.duration_s:.1f} s "
        f"({quality.frame_rate_hz:.1f} Hz, longest gap {quality.max_gap_ms:.0f} ms)"
    )
    print(f"quality    {quality.score:.2f} (mean confidence {quality.mean_confidence:.2f})")

    pose = prepare(scan.t_ms, scan.keypoints)
    vertical = angles.vertical_from_gravity(header.camera.gravity)
    found = [metric(pose.xyz, side) for metric in SIDED for side in ("left", "right")]
    found.append(metrics.trunk_lean_peak(pose.xyz, vertical))

    print()
    for measurement in found:
        if measurement is None:
            continue
        side = "" if measurement.side == "none" else f" ({measurement.side})"
        print(f"{measurement.metric_code + side:36s}{math.degrees(measurement.value):7.1f} deg")
    if all(measurement is None for measurement in found):
        print("no metrics: the joints needed were never visible with enough confidence")


if __name__ == "__main__":
    if len(sys.argv) != 2:
        sys.exit(__doc__)
    main(Path(sys.argv[1]))
