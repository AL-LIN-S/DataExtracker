from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
from typing import Mapping

import numpy as np
from PIL import Image, ImageDraw

from curve_extractor.core.calibration import PlotCalibration
from curve_extractor.core.extraction import ExtractionResult, SeriesConfig


@dataclass(frozen=True)
class ComparisonMetric:
    source_pixel_count: int
    path_pixel_count: int
    source_coverage_fraction: float
    path_on_source_fraction: float
    missing_fraction: float


@dataclass(frozen=True)
class ComparisonArtifacts:
    overlay_path: Path
    side_by_side_path: Path
    color_fit_path: Path
    metrics_path: Path
    metrics: Mapping[str, ComparisonMetric]


def build_comparison_artifacts(
    image_rgb: np.ndarray,
    calibration: PlotCalibration,
    result: ExtractionResult,
    configs: list[SeriesConfig],
    output_prefix: str | Path,
    *,
    match_radius: int = 3,
) -> ComparisonArtifacts:
    prefix = Path(output_prefix)
    prefix.parent.mkdir(parents=True, exist_ok=True)
    overlay_path = prefix.with_name(prefix.name + "_overlay.png")
    side_by_side_path = prefix.with_name(prefix.name + "_side_by_side.png")
    color_fit_path = prefix.with_name(prefix.name + "_color_fit.png")
    metrics_path = prefix.with_name(prefix.name + "_metrics.csv")

    metrics = _comparison_metrics(image_rgb, calibration, result, configs, match_radius=match_radius)
    _write_overlay(image_rgb, calibration, result, configs, overlay_path)
    _write_side_by_side(image_rgb, calibration, result, configs, side_by_side_path)
    _write_color_fit(image_rgb, calibration, result, configs, color_fit_path, match_radius=match_radius)
    _write_metrics(metrics_path, metrics)

    return ComparisonArtifacts(
        overlay_path=overlay_path,
        side_by_side_path=side_by_side_path,
        color_fit_path=color_fit_path,
        metrics_path=metrics_path,
        metrics=metrics,
    )


def _comparison_metrics(
    image_rgb: np.ndarray,
    calibration: PlotCalibration,
    result: ExtractionResult,
    configs: list[SeriesConfig],
    *,
    match_radius: int,
) -> dict[str, ComparisonMetric]:
    metrics: dict[str, ComparisonMetric] = {}
    for config in configs:
        column = config.column_name
        path = result.preview_paths.get(column, [])
        source = _source_mask(image_rgb, calibration, config)
        path_mask = _path_mask(image_rgb.shape[:2], path)
        source_near_path = _dilate(path_mask, match_radius)
        path_near_source = _dilate(source, match_radius)
        source_count = int(source.sum())
        path_count = int(path_mask.sum())
        source_coverage = _fraction((source & source_near_path).sum(), source_count)
        path_on_source = _fraction((path_mask & path_near_source).sum(), path_count)
        missing = result.missing.get(column)
        missing_fraction = float(np.mean(missing)) if missing is not None and missing.size else 1.0
        metrics[column] = ComparisonMetric(
            source_pixel_count=source_count,
            path_pixel_count=path_count,
            source_coverage_fraction=source_coverage,
            path_on_source_fraction=path_on_source,
            missing_fraction=missing_fraction,
        )
    return metrics


def _write_overlay(
    image_rgb: np.ndarray,
    calibration: PlotCalibration,
    result: ExtractionResult,
    configs: list[SeriesConfig],
    output_path: Path,
) -> None:
    image = Image.fromarray(image_rgb).convert("RGB")
    draw = ImageDraw.Draw(image)
    draw.rectangle((calibration.left, calibration.top, calibration.right, calibration.bottom), outline=(255, 180, 0), width=2)
    for config in configs:
        path = result.preview_paths.get(config.column_name, [])
        _draw_path(draw, path, config.rgb, width=2)
    image.save(output_path)


def _write_side_by_side(
    image_rgb: np.ndarray,
    calibration: PlotCalibration,
    result: ExtractionResult,
    configs: list[SeriesConfig],
    output_path: Path,
) -> None:
    original = Image.fromarray(image_rgb).convert("RGB")
    redrawn = Image.new("RGB", original.size, "white")
    draw = ImageDraw.Draw(redrawn)
    draw.rectangle((calibration.left, calibration.top, calibration.right, calibration.bottom), outline=(0, 0, 0), width=1)
    _draw_grid(draw, calibration)
    for config in configs:
        _draw_path(draw, result.preview_paths.get(config.column_name, []), config.rgb, width=2)
    canvas = Image.new("RGB", (original.width * 2, original.height + 28), "white")
    canvas.paste(original, (0, 28))
    canvas.paste(redrawn, (original.width, 28))
    labels = ImageDraw.Draw(canvas)
    labels.text((8, 8), "Original image", fill=(0, 0, 0))
    labels.text((original.width + 8, 8), "Redrawn from extracted CSV", fill=(0, 0, 0))
    canvas.save(output_path)


def _write_color_fit(
    image_rgb: np.ndarray,
    calibration: PlotCalibration,
    result: ExtractionResult,
    configs: list[SeriesConfig],
    output_path: Path,
    *,
    match_radius: int,
) -> None:
    fit = np.full_like(image_rgb, 255)
    fit[calibration.top : calibration.bottom + 1, calibration.left : calibration.right + 1] = 245
    for config in configs:
        source = _source_mask(image_rgb, calibration, config)
        path_mask = _path_mask(image_rgb.shape[:2], result.preview_paths.get(config.column_name, []))
        near_path = _dilate(path_mask, match_radius)
        color = np.array(config.rgb, dtype=np.uint8)
        fit[source] = color
        fit[source & near_path] = np.array([0, 0, 0], dtype=np.uint8)
        fit[path_mask] = np.array([255, 255, 0], dtype=np.uint8)
    image = Image.fromarray(fit).convert("RGB")
    draw = ImageDraw.Draw(image)
    draw.rectangle((calibration.left, calibration.top, calibration.right, calibration.bottom), outline=(0, 0, 0), width=1)
    draw.text((8, 8), "Color-fit check: color pixels and extracted paths", fill=(0, 0, 0))
    image.save(output_path)


def _write_metrics(path: Path, metrics: Mapping[str, ComparisonMetric]) -> None:
    lines = [
        "series,source_pixel_count,path_pixel_count,source_coverage_fraction,path_on_source_fraction,missing_fraction"
    ]
    for name, metric in metrics.items():
        lines.append(
            f"{name},{metric.source_pixel_count},{metric.path_pixel_count},"
            f"{metric.source_coverage_fraction:.6f},{metric.path_on_source_fraction:.6f},"
            f"{metric.missing_fraction:.6f}"
        )
    path.write_text("\n".join(lines) + "\n", encoding="utf-8")


def _source_mask(image_rgb: np.ndarray, calibration: PlotCalibration, config: SeriesConfig) -> np.ndarray:
    target = np.array(config.rgb, dtype=float)
    distance = np.linalg.norm(image_rgb.astype(float) - target, axis=2)
    mask = distance <= config.tolerance
    outside = np.ones(mask.shape, dtype=bool)
    outside[calibration.top : calibration.bottom + 1, calibration.left : calibration.right + 1] = False
    mask[outside] = False
    return mask


def _path_mask(shape: tuple[int, int], path: list[tuple[int, int]]) -> np.ndarray:
    mask = np.zeros(shape, dtype=bool)
    height, width = shape
    for x, y in path:
        if 0 <= x < width and 0 <= y < height:
            mask[y, x] = True
    return mask


def _dilate(mask: np.ndarray, radius: int) -> np.ndarray:
    if radius <= 0:
        return mask.copy()
    try:
        import cv2

        kernel = cv2.getStructuringElement(cv2.MORPH_ELLIPSE, (radius * 2 + 1, radius * 2 + 1))
        return cv2.dilate(mask.astype(np.uint8), kernel).astype(bool)
    except ImportError:
        padded = np.pad(mask, radius, constant_values=False)
        dilated = np.zeros_like(mask, dtype=bool)
        for dy in range(radius * 2 + 1):
            for dx in range(radius * 2 + 1):
                dilated |= padded[dy : dy + mask.shape[0], dx : dx + mask.shape[1]]
        return dilated


def _fraction(numerator: int | np.integer, denominator: int) -> float:
    if denominator <= 0:
        return 0.0
    return float(numerator) / float(denominator)


def _draw_path(draw: ImageDraw.ImageDraw, path: list[tuple[int, int]], color: tuple[int, int, int], *, width: int) -> None:
    for segment in _path_segments(path):
        if len(segment) > 1:
            draw.line(segment, fill=color, width=width)
    for x, y in path[:: max(1, len(path) // 150 or 1)]:
        draw.ellipse((x - 1, y - 1, x + 1, y + 1), fill=color)


def _path_segments(path: list[tuple[int, int]]) -> list[list[tuple[int, int]]]:
    if not path:
        return []
    segments: list[list[tuple[int, int]]] = [[path[0]]]
    for point in path[1:]:
        previous = segments[-1][-1]
        if point[0] - previous[0] <= 1:
            segments[-1].append(point)
        else:
            segments.append([point])
    return segments


def _draw_grid(draw: ImageDraw.ImageDraw, calibration: PlotCalibration) -> None:
    for index in range(1, 10):
        x = int(round(calibration.left + index * (calibration.right - calibration.left) / 10))
        y = int(round(calibration.top + index * (calibration.bottom - calibration.top) / 10))
        draw.line((x, calibration.top, x, calibration.bottom), fill=(210, 210, 210), width=1)
        draw.line((calibration.left, y, calibration.right, y), fill=(210, 210, 210), width=1)
