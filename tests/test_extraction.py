import numpy as np
import pytest

from curve_extractor.core.calibration import PlotCalibration, YAxisConfig
from curve_extractor.core.extraction import SeriesConfig, extract_series


def _calibration() -> PlotCalibration:
    return PlotCalibration(
        left=0,
        top=0,
        right=99,
        bottom=99,
        x_min=0.0,
        x_max=9.9,
        y_axes={"value": YAxisConfig(name="value", unit="", y_min=0.0, y_max=99.0)},
    )


def test_extract_series_samples_median_pixel_in_each_x_column():
    image = np.full((100, 100, 3), 255, dtype=np.uint8)
    for x in range(100):
        y = 80 - x // 2
        image[max(0, y - 1) : min(100, y + 2), x] = (255, 0, 0)

    result = extract_series(
        image,
        _calibration(),
        [SeriesConfig(name="red", unit="", rgb=(255, 0, 0), tolerance=35, y_axis="value")],
    )

    assert result.x[0] == pytest.approx(0.0)
    assert result.x[-1] == pytest.approx(9.9)
    assert result.series["red"][0] == pytest.approx(19.0, abs=1.5)
    assert result.series["red"][50] == pytest.approx(44.0, abs=1.5)
    assert not result.missing["red"][50]


def test_short_gaps_are_interpolated_and_long_gaps_remain_missing():
    image = np.full((100, 100, 3), 255, dtype=np.uint8)
    for x in range(100):
        if 20 <= x <= 22 or 60 <= x <= 75:
            continue
        image[50, x] = (0, 0, 255)

    result = extract_series(
        image,
        _calibration(),
        [SeriesConfig(name="blue", unit="", rgb=(0, 0, 255), tolerance=35, y_axis="value")],
        max_interpolation_gap=4,
    )

    assert result.series["blue"][21] == pytest.approx(49.0)
    assert not result.missing["blue"][21]
    assert np.isnan(result.series["blue"][68])
    assert result.missing["blue"][68]


def test_exclusion_regions_are_not_sampled():
    image = np.full((100, 100, 3), 255, dtype=np.uint8)
    image[50, :] = (0, 255, 0)

    result = extract_series(
        image,
        _calibration(),
        [SeriesConfig(name="green", unit="", rgb=(0, 255, 0), tolerance=35, y_axis="value")],
        exclusion_regions=[(40, 0, 60, 99)],
    )

    assert np.isnan(result.series["green"][50])
    assert result.missing["green"][50]
    assert result.series["green"][20] == pytest.approx(49.0)
