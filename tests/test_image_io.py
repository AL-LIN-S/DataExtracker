from pathlib import Path

import numpy as np
from PIL import Image

from curve_extractor.app.image_io import load_image_rgb


def test_load_image_rgb_reads_unicode_windows_paths(tmp_path: Path):
    path = tmp_path / "中文图像.jpeg"
    expected = np.zeros((8, 10, 3), dtype=np.uint8)
    expected[:, :] = (10, 120, 230)
    Image.fromarray(expected).save(path)

    actual = load_image_rgb(path)

    assert actual.shape == expected.shape
    assert np.abs(actual.astype(int) - expected.astype(int)).mean() < 5
