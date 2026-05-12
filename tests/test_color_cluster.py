import numpy as np

from curve_extractor.core.calibration import PlotCalibration, YAxisConfig
from curve_extractor.core.color_cluster import find_color_candidates


def test_color_candidates_ignore_grid_and_return_dominant_colored_curves():
    image = np.full((80, 100, 3), 255, dtype=np.uint8)
    image[:, 10::20] = (40, 40, 40)
    image[10::20, :] = (40, 40, 40)
    image[20:24, 15:85] = (240, 20, 20)
    image[40:44, 15:85] = (20, 230, 20)
    image[60:64, 15:85] = (20, 20, 240)
    calibration = PlotCalibration(
        left=0,
        top=0,
        right=99,
        bottom=79,
        x_min=0.0,
        x_max=99.0,
        y_axes={"value": YAxisConfig(name="value", unit="", y_min=0.0, y_max=1.0)},
    )

    candidates = find_color_candidates(image, calibration, max_colors=3, min_pixels=20)
    candidate_colors = np.array([candidate.rgb for candidate in candidates])

    assert len(candidates) == 3
    assert np.min(np.linalg.norm(candidate_colors - np.array((240, 20, 20)), axis=1)) < 30
    assert np.min(np.linalg.norm(candidate_colors - np.array((20, 230, 20)), axis=1)) < 30
    assert np.min(np.linalg.norm(candidate_colors - np.array((20, 20, 240)), axis=1)) < 30
