import numpy as np
import pytest

from curve_extractor.core.auto_calibration import OCRText, auto_calibrate_from_ocr, detect_plot_area


def test_detect_plot_area_finds_dark_rectangular_frame():
    image = np.full((180, 260, 3), 255, dtype=np.uint8)
    left, top, right, bottom = 42, 25, 230, 150
    image[top : bottom + 1 : 25, left : right + 1] = 180
    image[top : bottom + 1, left : right + 1 : 31] = 180
    image[top : bottom + 1, left] = 0
    image[top : bottom + 1, right] = 0
    image[top, left : right + 1] = 0
    image[bottom, left : right + 1] = 0

    assert detect_plot_area(image) == (left, top, right, bottom)


def test_auto_calibrate_groups_x_ticks_and_multiple_y_axes_from_ocr_boxes():
    image = np.full((220, 320, 3), 255, dtype=np.uint8)
    left, top, right, bottom = 80, 30, 280, 170
    image[top : bottom + 1, left] = 0
    image[top : bottom + 1, right] = 0
    image[top, left : right + 1] = 0
    image[bottom, left : right + 1] = 0
    ocr = [
        OCRText("0.00", (68, 178, 92, 190)),
        OCRText("50.00", (163, 178, 197, 190)),
        OCRText("100.00", (260, 178, 300, 190)),
        OCRText("62.0", (16, 24, 42, 36)),
        OCRText("52.0", (16, 94, 42, 106)),
        OCRText("42.0", (16, 164, 42, 176)),
        OCRText("50.20", (45, 24, 76, 36)),
        OCRText("50.00", (45, 94, 76, 106)),
        OCRText("49.80", (45, 164, 76, 176)),
        OCRText("110.0", (286, 24, 318, 36)),
        OCRText("90.0", (286, 94, 318, 106)),
        OCRText("70.0", (286, 164, 318, 176)),
    ]

    result = auto_calibrate_from_ocr(image, ocr)

    assert result.calibration.left == left
    assert result.calibration.right == right
    assert result.calibration.x_min == pytest.approx(0.0, abs=0.2)
    assert result.calibration.x_max == pytest.approx(100.0, abs=0.2)
    assert result.calibration.y_axes["left_1"].y_min == pytest.approx(42.0, abs=0.2)
    assert result.calibration.y_axes["left_1"].y_max == pytest.approx(62.0, abs=0.2)
    assert result.calibration.y_axes["left_2"].y_min == pytest.approx(49.80, abs=0.01)
    assert result.calibration.y_axes["left_2"].y_max == pytest.approx(50.20, abs=0.01)
    assert result.calibration.y_axes["right_1"].y_min == pytest.approx(70.0, abs=0.2)
    assert result.calibration.y_axes["right_1"].y_max == pytest.approx(110.0, abs=0.2)


def test_auto_calibrate_ignores_single_ocr_tick_outlier_in_linear_y_axis():
    image = np.full((220, 320, 3), 255, dtype=np.uint8)
    left, top, right, bottom = 80, 30, 280, 170
    image[top : bottom + 1, left] = 0
    image[top : bottom + 1, right] = 0
    image[top, left : right + 1] = 0
    image[bottom, left : right + 1] = 0
    ocr = [
        OCRText("0.00", (68, 178, 92, 190)),
        OCRText("100.00", (260, 178, 300, 190)),
        OCRText("62.0", (16, 24, 42, 36)),
        OCRText("60.0", (16, 52, 42, 64)),
        OCRText("58.0", (16, 80, 42, 92)),
        OCRText("440", (16, 108, 42, 120)),
        OCRText("54.0", (16, 136, 42, 148)),
        OCRText("52.0", (16, 164, 42, 176)),
    ]

    result = auto_calibrate_from_ocr(image, ocr)

    assert result.calibration.y_axes["left_1"].y_min == pytest.approx(52.0, abs=0.3)
    assert result.calibration.y_axes["left_1"].y_max == pytest.approx(62.0, abs=0.3)
