from __future__ import annotations

import numpy as np


def has_curve_color_signal(image_rgb: np.ndarray, *, min_pixels_per_color: int = 20, min_color_count: int = 2) -> bool:
    if image_rgb.ndim != 3 or image_rgb.shape[2] != 3:
        return False
    if is_probably_table_image(image_rgb):
        return False
    red = image_rgb[:, :, 0].astype(int)
    green = image_rgb[:, :, 1].astype(int)
    blue = image_rgb[:, :, 2].astype(int)
    color_masks = [
        (red > 170) & (green < 140) & (blue < 140),
        (green > 150) & (red < 150) & (blue < 180),
        (blue > 150) & (red < 150) & (green < 150),
    ]
    return sum(int(mask.sum()) >= min_pixels_per_color for mask in color_masks) >= min_color_count


def is_probably_table_image(image_rgb: np.ndarray) -> bool:
    if image_rgb.ndim != 3 or image_rgb.shape[2] != 3:
        return False
    gray = image_rgb.astype(np.float32).mean(axis=2)
    dark = gray < 80
    height, width = dark.shape
    vertical = _line_groups(np.flatnonzero(dark.sum(axis=0) >= height * 0.35))
    horizontal = _line_groups(np.flatnonzero(dark.sum(axis=1) >= width * 0.35))
    return len(vertical) >= 8 and len(horizontal) >= 3


def _line_groups(candidates: np.ndarray) -> list[tuple[int, int]]:
    if candidates.size == 0:
        return []
    groups: list[tuple[int, int]] = []
    start = previous = int(candidates[0])
    for value in candidates[1:]:
        current = int(value)
        if current <= previous + 2:
            previous = current
            continue
        groups.append((start, previous))
        start = previous = current
    groups.append((start, previous))
    return groups
