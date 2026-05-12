from __future__ import annotations

import numpy as np

try:
    from PySide6.QtCore import QPoint, QRect, Qt, Signal
    from PySide6.QtGui import QColor, QImage, QMouseEvent, QPainter, QPen, QPixmap
    from PySide6.QtWidgets import QLabel
except ImportError as exc:  # pragma: no cover - exercised when launching GUI without dependencies.
    raise RuntimeError("PySide6 is required for the desktop GUI. Install with: pip install PySide6") from exc


class ImageView(QLabel):
    point_selected = Signal(int, int)
    rectangle_selected = Signal(tuple)

    def __init__(self) -> None:
        super().__init__()
        self.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.setMinimumSize(640, 420)
        self.setMouseTracking(True)
        self._base_pixmap: QPixmap | None = None
        self._display_pixmap: QPixmap | None = None
        self._image_size: tuple[int, int] | None = None
        self._display_rect = QRect()
        self._selecting_rectangle = False
        self._drag_start: QPoint | None = None
        self._drag_current: QPoint | None = None

    def set_image(self, image_rgb: np.ndarray) -> None:
        self._base_pixmap = pixmap_from_rgb(image_rgb)
        self._image_size = (image_rgb.shape[1], image_rgb.shape[0])
        self._display_pixmap = self._base_pixmap
        self._refresh_pixmap()

    def set_overlay_pixmap(self, pixmap: QPixmap) -> None:
        self._display_pixmap = pixmap
        self._refresh_pixmap()

    def enable_rectangle_selection(self) -> None:
        self._selecting_rectangle = True
        self.setCursor(Qt.CursorShape.CrossCursor)

    def resizeEvent(self, event) -> None:  # noqa: N802 - Qt API
        super().resizeEvent(event)
        self._refresh_pixmap()

    def mousePressEvent(self, event: QMouseEvent) -> None:  # noqa: N802 - Qt API
        if event.button() != Qt.MouseButton.LeftButton:
            return
        if self._selecting_rectangle:
            self._drag_start = event.position().toPoint()
            self._drag_current = self._drag_start
            self.update()
            return
        point = self._widget_to_image(event.position().toPoint())
        if point is not None:
            self.point_selected.emit(point[0], point[1])

    def mouseMoveEvent(self, event: QMouseEvent) -> None:  # noqa: N802 - Qt API
        if self._selecting_rectangle and self._drag_start is not None:
            self._drag_current = event.position().toPoint()
            self.update()

    def mouseReleaseEvent(self, event: QMouseEvent) -> None:  # noqa: N802 - Qt API
        if not self._selecting_rectangle or event.button() != Qt.MouseButton.LeftButton:
            return
        end = event.position().toPoint()
        start_image = self._widget_to_image(self._drag_start) if self._drag_start else None
        end_image = self._widget_to_image(end)
        self._selecting_rectangle = False
        self._drag_start = None
        self._drag_current = None
        self.unsetCursor()
        self.update()
        if start_image and end_image:
            x1, y1 = start_image
            x2, y2 = end_image
            if abs(x2 - x1) >= 2 and abs(y2 - y1) >= 2:
                self.rectangle_selected.emit((x1, y1, x2, y2))

    def paintEvent(self, event) -> None:  # noqa: N802 - Qt API
        super().paintEvent(event)
        if self._selecting_rectangle and self._drag_start and self._drag_current:
            painter = QPainter(self)
            painter.setPen(QPen(QColor(255, 180, 0), 2, Qt.PenStyle.DashLine))
            painter.drawRect(QRect(self._drag_start, self._drag_current).normalized())

    def _refresh_pixmap(self) -> None:
        if self._display_pixmap is None:
            self.clear()
            self._display_rect = QRect()
            return
        scaled = self._display_pixmap.scaled(
            self.size(),
            Qt.AspectRatioMode.KeepAspectRatio,
            Qt.TransformationMode.SmoothTransformation,
        )
        self.setPixmap(scaled)
        x = (self.width() - scaled.width()) // 2
        y = (self.height() - scaled.height()) // 2
        self._display_rect = QRect(x, y, scaled.width(), scaled.height())

    def _widget_to_image(self, point: QPoint | None) -> tuple[int, int] | None:
        if point is None or self._image_size is None or self._display_rect.isNull():
            return None
        if not self._display_rect.contains(point):
            return None
        image_width, image_height = self._image_size
        x_ratio = (point.x() - self._display_rect.left()) / max(1, self._display_rect.width() - 1)
        y_ratio = (point.y() - self._display_rect.top()) / max(1, self._display_rect.height() - 1)
        image_x = int(round(x_ratio * (image_width - 1)))
        image_y = int(round(y_ratio * (image_height - 1)))
        return image_x, image_y


def pixmap_from_rgb(image_rgb: np.ndarray) -> QPixmap:
    contiguous = np.ascontiguousarray(image_rgb)
    height, width, channels = contiguous.shape
    if channels != 3:
        raise ValueError("image_rgb must have three channels")
    bytes_per_line = channels * width
    image = QImage(contiguous.data, width, height, bytes_per_line, QImage.Format.Format_RGB888)
    return QPixmap.fromImage(image.copy())
