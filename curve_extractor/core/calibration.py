from __future__ import annotations

from dataclasses import dataclass
from typing import Mapping

import numpy as np


@dataclass(frozen=True)
class YAxisConfig:
    name: str
    unit: str
    y_min: float
    y_max: float

    def __post_init__(self) -> None:
        if not self.name:
            raise ValueError("y axis name is required")
        if self.y_max <= self.y_min:
            raise ValueError("y axis max must be greater than min")


@dataclass(frozen=True)
class PlotCalibration:
    left: int
    top: int
    right: int
    bottom: int
    x_min: float
    x_max: float
    y_axes: Mapping[str, YAxisConfig]

    def __post_init__(self) -> None:
        if self.right <= self.left or self.bottom <= self.top:
            raise ValueError("plot area must have positive width and height")
        if self.x_max <= self.x_min:
            raise ValueError("x axis max must be greater than min")
        if not self.y_axes:
            raise ValueError("at least one y axis is required")
        missing = [key for key, axis in self.y_axes.items() if key != axis.name]
        if missing:
            raise ValueError(f"y axis mapping keys must match axis names: {missing}")

    @property
    def width(self) -> int:
        return self.right - self.left + 1

    @property
    def height(self) -> int:
        return self.bottom - self.top + 1

    def roi_slices(self) -> tuple[slice, slice]:
        return slice(self.top, self.bottom + 1), slice(self.left, self.right + 1)

    def plot_x_pixels(self) -> np.ndarray:
        return np.arange(self.left, self.right + 1, dtype=float)

    def pixel_x_to_value(self, pixel_x: float) -> float:
        ratio = (float(pixel_x) - self.left) / (self.right - self.left)
        return self.x_min + ratio * (self.x_max - self.x_min)

    def pixel_y_to_value(self, pixel_y: float, y_axis: str) -> float:
        axis = self.y_axes[y_axis]
        ratio = (float(pixel_y) - self.top) / (self.bottom - self.top)
        return axis.y_max - ratio * (axis.y_max - axis.y_min)

    def x_values(self) -> np.ndarray:
        return np.array([self.pixel_x_to_value(x) for x in self.plot_x_pixels()], dtype=float)

    def y_values(self, pixel_y_values: np.ndarray, y_axis: str) -> np.ndarray:
        values = np.full(pixel_y_values.shape, np.nan, dtype=float)
        valid = ~np.isnan(pixel_y_values)
        if np.any(valid):
            axis = self.y_axes[y_axis]
            ratio = (pixel_y_values[valid] - self.top) / (self.bottom - self.top)
            values[valid] = axis.y_max - ratio * (axis.y_max - axis.y_min)
        return values
