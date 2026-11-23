"""Finding the person in a frame: a mask (white = person) and the face box.

On a Mac this uses Apple Vision through the two small Swift tools in tools/ (fast, built into macOS).
Everywhere else, or with MONTI_VISION=mediapipe, it uses MediaPipe (pip install mediapipe).
"""
import os
import subprocess
import sys
from pathlib import Path

HERE = Path(__file__).resolve().parent
TOOLS = HERE / "tools"


def _apple():
    return (sys.platform == "darwin" and os.environ.get("MONTI_VISION") != "mediapipe"
            and (TOOLS / "personmask").exists() and (TOOLS / "faces").exists())


def masks(frames, out_dir):
    """Writes out_dir/<frame name>: a grayscale mask the size of the frame."""
    if _apple():
        subprocess.run([str(TOOLS / "personmask"), str(out_dir), *map(str, frames)], check=True, capture_output=True)
        return
    import mediapipe as mp
    import numpy as np
    from PIL import Image
    with mp.solutions.selfie_segmentation.SelfieSegmentation(model_selection=1) as seg:
        for f in frames:
            rgb = np.asarray(Image.open(f).convert("RGB"))
            m = seg.process(rgb).segmentation_mask
            Image.fromarray((np.clip(m, 0, 1) * 255).astype("uint8"), "L").save(Path(out_dir) / Path(f).name)


def faces(frames):
    """(centre x, centre y, size) in pixels of the largest face per frame, or None where there is none."""
    if _apple():
        out = subprocess.run([str(TOOLS / "faces"), *map(str, frames)], check=True, capture_output=True, text=True)
        return [None if ln.endswith("none") else tuple(int(v) for v in ln.split()[1:4]) for ln in out.stdout.splitlines()]
    import mediapipe as mp
    import numpy as np
    from PIL import Image
    boxes = []
    with mp.solutions.face_detection.FaceDetection(model_selection=1, min_detection_confidence=0.5) as fd:
        for f in frames:
            img = Image.open(f).convert("RGB")
            w, h = img.size
            res = fd.process(np.asarray(img))
            if not res.detections:
                boxes.append(None)
                continue
            b = max((d.location_data.relative_bounding_box for d in res.detections), key=lambda b: b.width)
            boxes.append((int((b.xmin + b.width / 2) * w), int((b.ymin + b.height / 2) * h), int(max(b.width * w, b.height * h))))
    return boxes
