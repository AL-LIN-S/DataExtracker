from __future__ import annotations

from dataclasses import dataclass
import os
from pathlib import Path
import re
import shutil
from typing import Iterable, Sequence

import numpy as np

from curve_extractor.core.calibration import PlotCalibration, YAxisConfig

_NUMBER_RE = re.compile(r"[-+]?(?:\d+(?:\.\d*)?|\.\d+)")


@dataclass(frozen=True)
class OCRText:
    text: str
    bbox: tuple[int, int, int, int]
    confidence: float = 1.0

    @property
    def center(self) -> tuple[float, float]:
        x1, y1, x2, y2 = self.bbox
        return (x1 + x2) / 2, (y1 + y2) / 2


@dataclass(frozen=True)
class AxisTick:
    value: float
    pixel: float
    text: str


@dataclass(frozen=True)
class AutoCalibrationResult:
    calibration: PlotCalibration
    x_ticks: list[AxisTick]
    y_ticks: dict[str, list[AxisTick]]
    warnings: list[str]


def detect_plot_area(image_rgb: np.ndarray) -> tuple[int, int, int, int]:
    """Detect the main plot frame in white-background engineering plots."""
    if image_rgb.ndim != 3 or image_rgb.shape[2] != 3:
        raise ValueError("image_rgb must be an RGB image with shape (height, width, 3)")

    gray = image_rgb.astype(np.float32).mean(axis=2)
    dark = gray < 90
    height, width = dark.shape
    min_vertical = max(20, int(height * 0.30))
    min_horizontal = max(20, int(width * 0.30))

    vertical_counts = dark.sum(axis=0)
    horizontal_counts = dark.sum(axis=1)
    vertical_lines = np.flatnonzero(vertical_counts >= min_vertical)
    horizontal_lines = np.flatnonzero(horizontal_counts >= min_horizontal)

    if vertical_lines.size >= 2 and horizontal_lines.size >= 2:
        left = int(vertical_lines[0])
        right = int(vertical_lines[-1])
        top = int(horizontal_lines[0])
        bottom = int(horizontal_lines[-1])
        if right - left > width * 0.25 and bottom - top > height * 0.25:
            return left, top, right, bottom

    # Fallback: find the largest dark-pixel bounding box after ignoring page margins.
    y_indices, x_indices = np.nonzero(dark)
    if x_indices.size == 0:
        raise ValueError("could not detect plot area: no dark frame pixels found")
    left, right = int(np.percentile(x_indices, 5)), int(np.percentile(x_indices, 95))
    top, bottom = int(np.percentile(y_indices, 5)), int(np.percentile(y_indices, 95))
    if right <= left or bottom <= top:
        raise ValueError("could not detect plot area")
    return left, top, right, bottom


def auto_calibrate_from_ocr(
    image_rgb: np.ndarray,
    ocr_texts: Sequence[OCRText],
    *,
    plot_area: tuple[int, int, int, int] | None = None,
) -> AutoCalibrationResult:
    area = plot_area or detect_plot_area(image_rgb)
    left, top, right, bottom = area
    numeric_texts = [(item, _parse_number(item.text)) for item in ocr_texts]
    numeric_texts = [(item, value) for item, value in numeric_texts if value is not None and item.confidence >= 0.25]
    if len(numeric_texts) < 4:
        raise ValueError("not enough OCR numeric labels to calibrate axes")

    x_labels = _x_axis_labels(numeric_texts, left, top, right, bottom)
    if len(x_labels) < 2:
        raise ValueError("not enough x-axis tick labels detected")
    x_grid, y_grid = _detect_grid_line_positions(image_rgb, area)
    x_snap_distance = max(20.0, (right - left) * 0.04)
    y_snap_distance = max(20.0, (bottom - top) * 0.04)
    x_ticks = [
        AxisTick(value=value, pixel=_snap_to_nearest(item.center[0], x_grid, x_snap_distance), text=item.text)
        for item, value in x_labels
    ]
    x_min, x_max = _axis_value_at_bounds([(tick.pixel, tick.value) for tick in x_ticks], left, right)

    grouped_y = _group_y_axis_labels(numeric_texts, left, top, right, bottom)
    if not grouped_y:
        raise ValueError("not enough y-axis tick labels detected")

    y_axes: dict[str, YAxisConfig] = {}
    y_ticks: dict[str, list[AxisTick]] = {}
    warnings: list[str] = []
    for axis_name, labels in grouped_y.items():
        labels = _filter_linear_tick_outliers(labels, pixel_axis="y")
        ticks = [
            AxisTick(value=value, pixel=_snap_to_nearest(item.center[1], y_grid, y_snap_distance), text=item.text)
            for item, value in labels
        ]
        if len(ticks) < 2:
            warnings.append(f"ignored {axis_name}: fewer than two tick labels")
            continue
        value_top, value_bottom = _axis_value_at_bounds([(tick.pixel, tick.value) for tick in ticks], top, bottom)
        y_min = min(value_bottom, value_top)
        y_max = max(value_bottom, value_top)
        y_axes[axis_name] = YAxisConfig(name=axis_name, unit="", y_min=y_min, y_max=y_max)
        y_ticks[axis_name] = ticks

    if not y_axes:
        raise ValueError("not enough y-axis tick labels detected")

    return AutoCalibrationResult(
        calibration=PlotCalibration(
            left=left,
            top=top,
            right=right,
            bottom=bottom,
            x_min=x_min,
            x_max=x_max,
            y_axes=y_axes,
        ),
        x_ticks=x_ticks,
        y_ticks=y_ticks,
        warnings=warnings,
    )


TESSERACT_MISSING_BANNER = (
    "未检测到 Tesseract，轴刻度自动识别现在不可用（不会假装已经 OCR）。"
    "请安装 Tesseract OCR，把 tesseract.exe 加入 PATH，或设置环境变量 TESSERACT_CMD "
    r"（常见路径：C:\Program Files\Tesseract-OCR\tesseract.exe）。"
    "Tesseract 只读轴上的数字，不是「AI 识曲线」，也不包含在本程序里。"
    "仍可手动点选图区、填写 X/Y 范围后提取。"
)


def first_run_tesseract_banner() -> str | None:
    """Return GUI first-run copy when Tesseract is missing; None if a binary was found."""
    if resolve_tesseract_command():
        return None
    return TESSERACT_MISSING_BANNER


def run_tesseract_ocr(image_rgb: np.ndarray) -> list[OCRText]:
    """Run Tesseract OCR when both pytesseract and the tesseract binary are installed."""
    try:
        import pytesseract
        from PIL import Image
    except ImportError as exc:
        raise RuntimeError(
            "Automatic digit OCR requires pytesseract and Tesseract. "
            "Install the Python package and the Tesseract executable first."
        ) from exc

    tesseract_cmd = resolve_tesseract_command()
    if tesseract_cmd:
        pytesseract.pytesseract.tesseract_cmd = tesseract_cmd

    image = Image.fromarray(image_rgb)
    try:
        texts = _run_tesseract_region(pytesseract, image, origin=(0, 0), psm=6)
        try:
            left, top, right, bottom = detect_plot_area(image_rgb)
        except ValueError:
            left = top = right = bottom = 0
        if right > left and bottom > top:
            regions = [
                (image.crop((max(0, left - 40), bottom + 5, min(image.width, right + 55), min(image.height, bottom + 75))), (max(0, left - 40), bottom + 5), 11),
                (image.crop((0, max(0, top - 20), max(0, left - 5), min(image.height, bottom + 25))), (0, max(0, top - 20)), 11),
                (image.crop((right + 5, max(0, top - 20), min(image.width, right + 125), min(image.height, bottom + 25))), (right + 5, max(0, top - 20)), 11),
            ]
            for crop, origin, psm in regions:
                texts.extend(_run_tesseract_region(pytesseract, crop, origin=origin, psm=psm))
    except pytesseract.TesseractNotFoundError as exc:
        raise RuntimeError(
            "Tesseract executable was not found. Install Tesseract OCR and add "
            "tesseract.exe to PATH, or set TESSERACT_CMD to that executable. "
            "Axis OCR is optional; you can still calibrate the plot box and ranges by hand."
        ) from exc
    return _deduplicate_ocr_texts(texts)


def _run_tesseract_region(pytesseract, image, *, origin: tuple[int, int], psm: int) -> list[OCRText]:
    data = pytesseract.image_to_data(
        image,
        config=f"--psm {psm} -c tessedit_char_whitelist=0123456789.-+",
        output_type=pytesseract.Output.DICT,
    )
    texts: list[OCRText] = []
    for index, text in enumerate(data.get("text", [])):
        parsed = _parse_number(text)
        if parsed is None:
            continue
        try:
            confidence = float(data["conf"][index]) / 100
        except (ValueError, TypeError):
            confidence = 0.0
        if confidence < 0.25:
            continue
        x = int(data["left"][index]) + origin[0]
        y = int(data["top"][index]) + origin[1]
        width = int(data["width"][index])
        height = int(data["height"][index])
        texts.append(OCRText(text=text, bbox=(x, y, x + width, y + height), confidence=confidence))
    return texts


def resolve_tesseract_command() -> str | None:
    """Return a usable Tesseract executable path, or None if it is not installed."""
    candidates: list[str | None] = [
        os.environ.get("TESSERACT_CMD"),
        shutil.which("tesseract"),
        shutil.which("tesseract.exe"),
    ]
    if os.name == "nt":
        program_files = os.environ.get("ProgramFiles", r"C:\Program Files")
        program_files_x86 = os.environ.get("ProgramFiles(x86)", r"C:\Program Files (x86)")
        local_app = os.environ.get("LOCALAPPDATA", "")
        candidates.extend(
            [
                str(Path(program_files) / "Tesseract-OCR" / "tesseract.exe"),
                str(Path(program_files_x86) / "Tesseract-OCR" / "tesseract.exe"),
            ]
        )
        if local_app:
            candidates.append(str(Path(local_app) / "Programs" / "Tesseract-OCR" / "tesseract.exe"))
    seen: set[str] = set()
    for candidate in candidates:
        if not candidate:
            continue
        path = Path(candidate.strip().strip('"'))
        key = str(path).lower()
        if key in seen:
            continue
        seen.add(key)
        if path.is_file():
            return str(path)
    return None


def _resolve_tesseract_command() -> str | None:
    return resolve_tesseract_command()


def _parse_number(text: str) -> float | None:
    normalized = text.strip().replace(",", ".")
    match = _NUMBER_RE.search(normalized)
    if not match:
        return None
    try:
        return float(match.group(0))
    except ValueError:
        return None


def _deduplicate_ocr_texts(texts: Sequence[OCRText]) -> list[OCRText]:
    kept: list[OCRText] = []
    for item in sorted(texts, key=lambda text: text.confidence, reverse=True):
        duplicate = False
        for existing in kept:
            if item.text == existing.text and abs(item.center[0] - existing.center[0]) < 8 and abs(item.center[1] - existing.center[1]) < 8:
                duplicate = True
                break
        if not duplicate:
            kept.append(item)
    return kept


def _filter_linear_tick_outliers(
    labels: Sequence[tuple[OCRText, float]],
    *,
    pixel_axis: str,
) -> list[tuple[OCRText, float]]:
    if len(labels) < 5:
        return list(labels)
    pixel_index = 1 if pixel_axis == "y" else 0
    ordered = sorted(labels, key=lambda pair: pair[0].center[pixel_index])
    values = np.array([value for _, value in ordered], dtype=float)
    diffs = np.diff(values)
    non_zero = np.abs(diffs[np.abs(diffs) > 1e-9])
    if non_zero.size == 0:
        return ordered
    median_step = float(np.median(non_zero))
    if median_step == 0:
        return ordered
    large = np.abs(diffs) > abs(median_step) * 5
    remove_indices: set[int] = set()
    for index in range(1, len(ordered) - 1):
        if large[index - 1] and large[index]:
            remove_indices.add(index)
    if not remove_indices:
        return ordered
    filtered = [label for index, label in enumerate(ordered) if index not in remove_indices]
    return filtered if len(filtered) >= 2 else ordered


def _detect_grid_line_positions(
    image_rgb: np.ndarray,
    area: tuple[int, int, int, int],
) -> tuple[np.ndarray, np.ndarray]:
    left, top, right, bottom = area
    roi_rgb = image_rgb[top : bottom + 1, left : right + 1].astype(np.float32)
    gray = roi_rgb.mean(axis=2)
    chroma = roi_rgb.max(axis=2) - roi_rgb.min(axis=2)
    line_pixels = (gray < 150) & (chroma < 35)
    height, width = line_pixels.shape
    x_candidates = np.flatnonzero(line_pixels.sum(axis=0) >= max(8, height * 0.08)) + left
    y_candidates = np.flatnonzero(line_pixels.sum(axis=1) >= max(8, width * 0.08)) + top
    return _group_line_positions(x_candidates), _group_line_positions(y_candidates)


def _group_line_positions(candidates: np.ndarray) -> np.ndarray:
    if candidates.size == 0:
        return np.array([], dtype=float)
    groups: list[tuple[int, int]] = []
    start = int(candidates[0])
    previous = int(candidates[0])
    for value in candidates[1:]:
        value = int(value)
        if value <= previous + 2:
            previous = value
        else:
            groups.append((start, previous))
            start = previous = value
    groups.append((start, previous))
    return np.array([(start + end) / 2 for start, end in groups], dtype=float)


def _snap_to_nearest(value: float, candidates: np.ndarray, max_distance: float) -> float:
    if candidates.size == 0:
        return float(value)
    distances = np.abs(candidates - value)
    index = int(np.argmin(distances))
    if distances[index] <= max_distance:
        return float(candidates[index])
    return float(value)


def _x_axis_labels(
    numeric_texts: Sequence[tuple[OCRText, float]],
    left: int,
    top: int,
    right: int,
    bottom: int,
) -> list[tuple[OCRText, float]]:
    plot_width = right - left
    below_top = bottom + 2
    below_bottom = bottom + max(18, int(plot_width * 0.16))
    labels = [
        (item, value)
        for item, value in numeric_texts
        if below_top <= item.center[1] <= below_bottom and left - 8 <= item.center[0] <= right + 45
    ]
    return sorted(labels, key=lambda pair: pair[0].center[0])


def _group_y_axis_labels(
    numeric_texts: Sequence[tuple[OCRText, float]],
    left: int,
    top: int,
    right: int,
    bottom: int,
) -> dict[str, list[tuple[OCRText, float]]]:
    labels = [
        (item, value)
        for item, value in numeric_texts
        if top - 12 <= item.center[1] <= bottom + 12
        and (item.center[0] < left - 2 or item.center[0] > right + 2)
    ]
    left_labels = [(item, value) for item, value in labels if item.center[0] < left]
    right_labels = [(item, value) for item, value in labels if item.center[0] > right]
    groups: dict[str, list[tuple[OCRText, float]]] = {}
    for prefix, side_labels, reverse in [("left", left_labels, False), ("right", right_labels, False)]:
        for index, group in enumerate(_cluster_by_x(side_labels), start=1):
            if len(group) >= 2:
                groups[f"{prefix}_{index}"] = sorted(group, key=lambda pair: pair[0].center[1])
    return groups


def _cluster_by_x(labels: Sequence[tuple[OCRText, float]], *, max_gap: float = 24.0) -> list[list[tuple[OCRText, float]]]:
    if not labels:
        return []
    sorted_labels = sorted(labels, key=lambda pair: pair[0].center[0])
    clusters: list[list[tuple[OCRText, float]]] = [[sorted_labels[0]]]
    for item in sorted_labels[1:]:
        current_mean = float(np.mean([entry[0].center[0] for entry in clusters[-1]]))
        if abs(item[0].center[0] - current_mean) <= max_gap:
            clusters[-1].append(item)
        else:
            clusters.append([item])
    return clusters


def _axis_value_at_bounds(samples: Sequence[tuple[float, float]], lower_pixel: float, upper_pixel: float) -> tuple[float, float]:
    pixels = np.array([sample[0] for sample in samples], dtype=float)
    values = np.array([sample[1] for sample in samples], dtype=float)
    slope, intercept = np.polyfit(pixels, values, deg=1)
    return float(slope * lower_pixel + intercept), float(slope * upper_pixel + intercept)
