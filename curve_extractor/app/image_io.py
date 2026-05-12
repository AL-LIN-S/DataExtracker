from __future__ import annotations

from pathlib import Path

import numpy as np


def load_image_rgb(path: str | Path) -> np.ndarray:
    path = Path(path)
    try:
        import cv2
    except ImportError:
        from PIL import Image

        return np.array(Image.open(path).convert("RGB"))

    image_bytes = np.fromfile(path, dtype=np.uint8)
    image_bgr = cv2.imdecode(image_bytes, cv2.IMREAD_COLOR)
    if image_bgr is None:
        raise ValueError(f"failed to read image: {path}")
    return cv2.cvtColor(image_bgr, cv2.COLOR_BGR2RGB)
