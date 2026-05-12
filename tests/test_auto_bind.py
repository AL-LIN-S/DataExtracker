from curve_extractor.core.auto_bind import auto_bind_series
from curve_extractor.core.calibration import PlotCalibration, YAxisConfig
from curve_extractor.core.color_cluster import ColorCandidate


def test_auto_bind_series_maps_red_green_blue_to_frequency_power_needle_axes():
    calibration = PlotCalibration(
        left=0,
        top=0,
        right=100,
        bottom=100,
        x_min=0.0,
        x_max=147.0,
        y_axes={
            "left_1": YAxisConfig("left_1", "", 42.0, 62.0),
            "left_2": YAxisConfig("left_2", "", 49.8, 50.2),
            "right_1": YAxisConfig("right_1", "", 70.0, 110.0),
        },
    )
    candidates = [
        ColorCandidate(rgb=(10, 7, 212), pixel_count=3000, fraction=0.3),
        ColorCandidate(rgb=(229, 67, 65), pixel_count=2800, fraction=0.2),
        ColorCandidate(rgb=(26, 242, 84), pixel_count=2500, fraction=0.2),
    ]

    configs = auto_bind_series(candidates, calibration)

    assert [(config.name, config.unit, config.y_axis) for config in configs] == [
        ("frequency", "Hz", "left_2"),
        ("power", "MW", "right_1"),
        ("needle", "%", "left_1"),
    ]
