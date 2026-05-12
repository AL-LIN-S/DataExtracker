from __future__ import annotations

from curve_extractor.core.calibration import PlotCalibration, YAxisConfig
from curve_extractor.core.color_cluster import ColorCandidate
from curve_extractor.core.extraction import SeriesConfig


def auto_bind_series(
    candidates: list[ColorCandidate],
    calibration: PlotCalibration,
    *,
    tolerance: float = 55.0,
) -> list[SeriesConfig]:
    by_hue: dict[str, ColorCandidate] = {}
    for candidate in candidates[:8]:
        hue = _dominant_hue(candidate.rgb)
        if hue not in by_hue:
            by_hue[hue] = candidate
    configs: list[SeriesConfig] = []

    frequency_axis = _frequency_axis(calibration)
    power_axis = _power_axis(calibration)
    needle_axis = _needle_axis(calibration, exclude={frequency_axis, power_axis})

    if "red" in by_hue and frequency_axis:
        configs.append(SeriesConfig("frequency", "Hz", by_hue["red"].rgb, tolerance, frequency_axis))
    if "green" in by_hue and power_axis:
        configs.append(SeriesConfig("power", "MW", by_hue["green"].rgb, tolerance, power_axis))
    if "blue" in by_hue and needle_axis:
        configs.append(SeriesConfig("needle", "%", by_hue["blue"].rgb, tolerance, needle_axis))
    return configs


def _dominant_hue(rgb: tuple[int, int, int]) -> str:
    red, green, blue = rgb
    if red >= green and red >= blue:
        return "red"
    if green >= red and green >= blue:
        return "green"
    return "blue"


def _frequency_axis(calibration: PlotCalibration) -> str | None:
    best_name = None
    best_span = float("inf")
    for name, axis in calibration.y_axes.items():
        span = axis.y_max - axis.y_min
        if axis.y_min <= 50.0 <= axis.y_max and span < best_span:
            best_name = name
            best_span = span
    return best_name


def _power_axis(calibration: PlotCalibration) -> str | None:
    right_axes = [(name, axis) for name, axis in calibration.y_axes.items() if name.startswith("right")]
    if right_axes:
        return max(right_axes, key=lambda pair: pair[1].y_max - pair[1].y_min)[0]
    return _largest_span_axis(calibration.y_axes)


def _needle_axis(calibration: PlotCalibration, *, exclude: set[str | None]) -> str | None:
    axes = {name: axis for name, axis in calibration.y_axes.items() if name not in exclude}
    return _largest_span_axis(axes)


def _largest_span_axis(axes: dict[str, YAxisConfig]) -> str | None:
    if not axes:
        return None
    return max(axes.items(), key=lambda pair: pair[1].y_max - pair[1].y_min)[0]
