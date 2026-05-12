import pytest

from curve_extractor.core.calibration import PlotCalibration, YAxisConfig


def test_pixel_to_value_maps_x_and_reverses_y_axis():
    calibration = PlotCalibration(
        left=10,
        top=20,
        right=110,
        bottom=220,
        x_min=0.0,
        x_max=10.0,
        y_axes={"power": YAxisConfig(name="power", unit="MW", y_min=80.0, y_max=100.0)},
    )

    assert calibration.pixel_x_to_value(60) == pytest.approx(5.0)
    assert calibration.pixel_y_to_value(20, "power") == pytest.approx(100.0)
    assert calibration.pixel_y_to_value(220, "power") == pytest.approx(80.0)
    assert calibration.pixel_y_to_value(120, "power") == pytest.approx(90.0)


def test_same_pixel_y_can_map_to_multiple_y_axes():
    calibration = PlotCalibration(
        left=0,
        top=0,
        right=100,
        bottom=100,
        x_min=0.0,
        x_max=1.0,
        y_axes={
            "frequency": YAxisConfig(name="frequency", unit="Hz", y_min=49.88, y_max=50.09),
            "needle": YAxisConfig(name="needle", unit="%", y_min=43.0, y_max=57.0),
        },
    )

    assert calibration.pixel_y_to_value(50, "frequency") == pytest.approx(49.985)
    assert calibration.pixel_y_to_value(50, "needle") == pytest.approx(50.0)


def test_invalid_calibration_rejects_degenerate_plot_area():
    with pytest.raises(ValueError, match="plot area"):
        PlotCalibration(
            left=10,
            top=20,
            right=10,
            bottom=220,
            x_min=0.0,
            x_max=10.0,
            y_axes={"power": YAxisConfig(name="power", unit="MW", y_min=0.0, y_max=1.0)},
        )
