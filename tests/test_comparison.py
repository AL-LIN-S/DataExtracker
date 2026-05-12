from __future__ import annotations

from pathlib import Path

import numpy as np

from curve_extractor.core.calibration import PlotCalibration, YAxisConfig
from curve_extractor.core.comparison import _path_segments, build_comparison_artifacts
from curve_extractor.core.extraction import ExtractionResult, SeriesConfig


def test_build_comparison_artifacts_writes_images_and_metrics(tmp_path: Path):
    image = np.full((40, 50, 3), 255, dtype=np.uint8)
    for x in range(5, 46):
        image[20, x] = (230, 20, 20)
    calibration = PlotCalibration(
        left=5,
        top=5,
        right=45,
        bottom=35,
        x_min=0,
        x_max=40,
        y_axes={"left_1": YAxisConfig("left_1", "", 0, 30)},
    )
    result = ExtractionResult(
        x=calibration.x_values(),
        series={"frequency_Hz": np.full(calibration.width, 15.0)},
        missing={"frequency_Hz": np.zeros(calibration.width, dtype=bool)},
        preview_paths={"frequency_Hz": [(x, 20) for x in range(5, 46)]},
    )
    configs = [SeriesConfig("frequency", "Hz", (230, 20, 20), 35, "left_1")]

    artifacts = build_comparison_artifacts(image, calibration, result, configs, tmp_path / "pic_001")

    assert artifacts.overlay_path.exists()
    assert artifacts.side_by_side_path.exists()
    assert artifacts.color_fit_path.exists()
    assert artifacts.metrics_path.exists()
    metric = artifacts.metrics["frequency_Hz"]
    assert metric.source_pixel_count == 41
    assert metric.source_coverage_fraction == 1.0
    assert metric.path_on_source_fraction == 1.0
    assert metric.missing_fraction == 0.0


def test_path_segments_do_not_connect_across_missing_x_columns():
    path = [(5, 20), (6, 20), (12, 10), (13, 10)]

    assert _path_segments(path) == [[(5, 20), (6, 20)], [(12, 10), (13, 10)]]
