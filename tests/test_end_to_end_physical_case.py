import numpy as np
import pytest

from curve_extractor.core.auto_calibration import OCRText, auto_calibrate_from_ocr
from curve_extractor.core.extraction import SeriesConfig, extract_series


def test_power_curve_matches_primary_frequency_validation_points():
    image = np.full((470, 720, 3), 255, dtype=np.uint8)
    left, top, right, bottom = 122, 55, 676, 375
    _draw_frame(image, left, top, right, bottom)
    for x in range(left, right + 1, 55):
        image[top : bottom + 1, x] = 190
    for y in range(top, bottom + 1, 32):
        image[y, left : right + 1] = 190
    _draw_frame(image, left, top, right, bottom)

    x_min, x_max = 0.0, 147.0
    power_min, power_max = 70.0, 110.0
    power_points = [
        (0.0, 91.29),
        (10.0, 91.29),
        (18.0, 87.44),
        (60.0, 87.44),
        (72.0, 80.76),
        (103.0, 80.83),
        (110.0, 83.83),
        (147.0, 83.83),
    ]
    _draw_series(image, left, top, right, bottom, x_min, x_max, power_min, power_max, power_points, (0, 235, 0))

    ocr = [
        OCRText("0.00", (102, 385, 142, 399)),
        OCRText("73.50", (380, 385, 420, 399)),
        OCRText("147.00", (653, 385, 699, 399)),
        OCRText("110.0", (685, 48, 718, 62)),
        OCRText("90.0", (685, 208, 718, 222)),
        OCRText("70.0", (685, 368, 718, 382)),
    ]
    auto = auto_calibrate_from_ocr(image, ocr)
    result = extract_series(
        image,
        auto.calibration,
        [SeriesConfig(name="power", unit="MW", rgb=(0, 235, 0), tolerance=35, y_axis="right_1")],
        max_interpolation_gap=4,
    )
    x = result.x
    power = result.series["power_MW"]

    assert _value_at(x, power, 0.0) == pytest.approx(91.29, abs=0.35)
    assert _value_at(x, power, 50.0) == pytest.approx(87.44, abs=0.35)
    assert _value_at(x, power, 90.0) == pytest.approx(80.76, abs=0.45)
    assert _value_at(x, power, 125.0) == pytest.approx(83.83, abs=0.35)
    assert (_value_at(x, power, 50.0) - _value_at(x, power, 0.0)) == pytest.approx(-3.85, abs=0.5)
    assert (_value_at(x, power, 125.0) - _value_at(x, power, 90.0)) == pytest.approx(3.0, abs=0.55)


def _draw_frame(image: np.ndarray, left: int, top: int, right: int, bottom: int) -> None:
    image[top : bottom + 1, left] = 0
    image[top : bottom + 1, right] = 0
    image[top, left : right + 1] = 0
    image[bottom, left : right + 1] = 0


def _draw_series(
    image: np.ndarray,
    left: int,
    top: int,
    right: int,
    bottom: int,
    x_min: float,
    x_max: float,
    y_min: float,
    y_max: float,
    points: list[tuple[float, float]],
    color: tuple[int, int, int],
) -> None:
    for (x1, y1), (x2, y2) in zip(points[:-1], points[1:]):
        px1 = _x_to_pixel(x1, left, right, x_min, x_max)
        px2 = _x_to_pixel(x2, left, right, x_min, x_max)
        steps = max(1, abs(px2 - px1))
        for step in range(steps + 1):
            ratio = step / steps
            x_value = x1 + ratio * (x2 - x1)
            y_value = y1 + ratio * (y2 - y1)
            px = _x_to_pixel(x_value, left, right, x_min, x_max)
            py = _y_to_pixel(y_value, top, bottom, y_min, y_max)
            image[max(top, py - 1) : min(bottom + 1, py + 2), px] = color


def _x_to_pixel(value: float, left: int, right: int, x_min: float, x_max: float) -> int:
    return int(round(left + (value - x_min) / (x_max - x_min) * (right - left)))


def _y_to_pixel(value: float, top: int, bottom: int, y_min: float, y_max: float) -> int:
    return int(round(top + (y_max - value) / (y_max - y_min) * (bottom - top)))


def _value_at(x: np.ndarray, values: np.ndarray, target: float) -> float:
    index = int(np.nanargmin(np.abs(x - target)))
    return float(values[index])
