from __future__ import annotations

from dataclasses import dataclass
from typing import Iterable

import numpy as np

from curve_extractor.core.calibration import PlotCalibration


@dataclass(frozen=True)
class ColorCandidate:
    rgb: tuple[int, int, int]
    pixel_count: int
    fraction: float


def find_color_candidates(
    image_rgb: np.ndarray,
    calibration: PlotCalibration,
    *,
    max_colors: int = 6,
    min_pixels: int = 30,
    saturation_threshold: int = 60,
    brightness_threshold: int = 30,
    quantization_step: int = 32,
) -> list[ColorCandidate]:
    """Find dominant saturated colors inside the calibrated plot area."""
    roi = _plot_roi(image_rgb, calibration)
    pixels = roi.reshape(-1, 3).astype(np.int16)
    chroma = pixels.max(axis=1) - pixels.min(axis=1)
    brightness = pixels.max(axis=1)
    colored = pixels[(chroma >= saturation_threshold) & (brightness >= brightness_threshold)]
    if colored.size == 0:
        return []

    bins = colored // quantization_step
    unique_bins, inverse, counts = np.unique(bins, axis=0, return_inverse=True, return_counts=True)
    order = np.argsort(counts)[::-1]
    total_colored = len(colored)

    candidates: list[ColorCandidate] = []
    for bin_index in order:
        count = int(counts[bin_index])
        if count < min_pixels:
            continue
        bucket_pixels = colored[inverse == bin_index]
        rgb = tuple(int(round(channel)) for channel in bucket_pixels.mean(axis=0))
        candidates = _append_or_merge(candidates, rgb, count, total_colored)
        if len(candidates) >= max_colors:
            break

    return sorted(candidates, key=lambda candidate: candidate.pixel_count, reverse=True)[:max_colors]


def _plot_roi(image_rgb: np.ndarray, calibration: PlotCalibration) -> np.ndarray:
    if image_rgb.ndim != 3 or image_rgb.shape[2] != 3:
        raise ValueError("image_rgb must be an RGB image with shape (height, width, 3)")
    y_slice, x_slice = calibration.roi_slices()
    return image_rgb[y_slice, x_slice]


def _append_or_merge(
    candidates: list[ColorCandidate],
    rgb: tuple[int, int, int],
    count: int,
    total_colored: int,
    *,
    merge_distance: float = 45.0,
) -> list[ColorCandidate]:
    rgb_array = np.array(rgb, dtype=float)
    for index, existing in enumerate(candidates):
        existing_array = np.array(existing.rgb, dtype=float)
        if np.linalg.norm(rgb_array - existing_array) <= merge_distance:
            merged_count = existing.pixel_count + count
            merged_rgb = tuple(
                int(round(value))
                for value in ((existing_array * existing.pixel_count + rgb_array * count) / merged_count)
            )
            candidates[index] = ColorCandidate(
                rgb=merged_rgb,
                pixel_count=merged_count,
                fraction=merged_count / total_colored,
            )
            return candidates
    candidates.append(ColorCandidate(rgb=rgb, pixel_count=count, fraction=count / total_colored))
    return candidates
