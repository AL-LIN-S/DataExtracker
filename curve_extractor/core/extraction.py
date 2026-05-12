from __future__ import annotations

from dataclasses import dataclass
from typing import Mapping, Sequence

import numpy as np

from curve_extractor.core.calibration import PlotCalibration


@dataclass(frozen=True)
class SeriesConfig:
    name: str
    unit: str
    rgb: tuple[int, int, int]
    tolerance: float
    y_axis: str

    @property
    def column_name(self) -> str:
        return f"{self.name}_{self.unit}" if self.unit else self.name


@dataclass(frozen=True)
class ExtractionResult:
    x: np.ndarray
    series: Mapping[str, np.ndarray]
    missing: Mapping[str, np.ndarray]
    preview_paths: Mapping[str, list[tuple[int, int]]]


def extract_series(
    image_rgb: np.ndarray,
    calibration: PlotCalibration,
    series_configs: Sequence[SeriesConfig],
    *,
    exclusion_regions: Sequence[tuple[int, int, int, int]] | None = None,
    max_interpolation_gap: int = 3,
    outlier_jump_pixels: float = 25.0,
) -> ExtractionResult:
    if image_rgb.ndim != 3 or image_rgb.shape[2] != 3:
        raise ValueError("image_rgb must be an RGB image with shape (height, width, 3)")
    if not series_configs:
        raise ValueError("at least one series is required")

    exclusion_mask = _build_exclusion_mask(image_rgb.shape[:2], exclusion_regions or [])
    x_values = calibration.x_values()
    series_values: dict[str, np.ndarray] = {}
    missing_masks: dict[str, np.ndarray] = {}
    preview_paths: dict[str, list[tuple[int, int]]] = {}

    for config in series_configs:
        if config.y_axis not in calibration.y_axes:
            raise ValueError(f"unknown y axis for series {config.name}: {config.y_axis}")
        mask = _color_mask(image_rgb, config.rgb, config.tolerance)
        mask &= ~exclusion_mask
        pixel_y = _sample_pixel_y_by_column(mask, calibration)
        pixel_y = _remove_large_jumps(pixel_y, max_jump=outlier_jump_pixels)
        pixel_y = _interpolate_short_gaps(pixel_y, max_gap=max_interpolation_gap)
        values = calibration.y_values(pixel_y, config.y_axis)
        missing = np.isnan(values)
        column_name = config.column_name
        series_values[column_name] = values
        missing_masks[column_name] = missing
        preview_paths[column_name] = _preview_path(calibration, pixel_y)

    return ExtractionResult(
        x=x_values,
        series=series_values,
        missing=missing_masks,
        preview_paths=preview_paths,
    )


def _color_mask(image_rgb: np.ndarray, rgb: tuple[int, int, int], tolerance: float) -> np.ndarray:
    target = np.array(rgb, dtype=float)
    distance = np.linalg.norm(image_rgb.astype(float) - target, axis=2)
    return distance <= tolerance


def _build_exclusion_mask(
    image_shape: tuple[int, int],
    regions: Sequence[tuple[int, int, int, int]],
) -> np.ndarray:
    mask = np.zeros(image_shape, dtype=bool)
    height, width = image_shape
    for x1, y1, x2, y2 in regions:
        left, right = sorted((int(round(x1)), int(round(x2))))
        top, bottom = sorted((int(round(y1)), int(round(y2))))
        left = max(0, min(width - 1, left))
        right = max(0, min(width - 1, right))
        top = max(0, min(height - 1, top))
        bottom = max(0, min(height - 1, bottom))
        mask[top : bottom + 1, left : right + 1] = True
    return mask


def _sample_pixel_y_by_column(mask: np.ndarray, calibration: PlotCalibration) -> np.ndarray:
    pixel_y = np.full(calibration.width, np.nan, dtype=float)
    for output_index, pixel_x in enumerate(range(calibration.left, calibration.right + 1)):
        column = mask[calibration.top : calibration.bottom + 1, pixel_x]
        local_y = np.flatnonzero(column)
        if local_y.size:
            pixel_y[output_index] = calibration.top + float(np.median(local_y))
    return pixel_y


def _remove_large_jumps(pixel_y: np.ndarray, *, max_jump: float) -> np.ndarray:
    filtered = pixel_y.copy()
    valid_indices = np.flatnonzero(~np.isnan(filtered))
    if valid_indices.size < 3:
        return filtered

    previous_index = valid_indices[0]
    for index in valid_indices[1:]:
        if index - previous_index <= 3 and abs(filtered[index] - filtered[previous_index]) > max_jump:
            filtered[index] = np.nan
            continue
        previous_index = index
    return filtered


def _interpolate_short_gaps(pixel_y: np.ndarray, *, max_gap: int) -> np.ndarray:
    interpolated = pixel_y.copy()
    valid = ~np.isnan(interpolated)
    if valid.sum() < 2:
        return interpolated

    index = 0
    while index < len(interpolated):
        if valid[index]:
            index += 1
            continue
        gap_start = index
        while index < len(interpolated) and not valid[index]:
            index += 1
        gap_end = index - 1
        gap_length = gap_end - gap_start + 1
        left = gap_start - 1
        right = gap_end + 1
        if left >= 0 and right < len(interpolated) and gap_length <= max_gap:
            interpolated[gap_start : gap_end + 1] = np.linspace(
                interpolated[left],
                interpolated[right],
                gap_length + 2,
            )[1:-1]
    return interpolated


def _preview_path(calibration: PlotCalibration, pixel_y: np.ndarray) -> list[tuple[int, int]]:
    path: list[tuple[int, int]] = []
    for offset, y in enumerate(pixel_y):
        if not np.isnan(y):
            path.append((calibration.left + offset, int(round(float(y)))))
    return path
