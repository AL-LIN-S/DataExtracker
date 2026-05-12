from __future__ import annotations

from pathlib import Path

import numpy as np

try:
    from PySide6.QtCore import Qt
    from PySide6.QtGui import QColor, QPainter, QPen
    from PySide6.QtWidgets import (
        QApplication,
        QAbstractItemView,
        QFileDialog,
        QGridLayout,
        QGroupBox,
        QHBoxLayout,
        QHeaderView,
        QLabel,
        QLineEdit,
        QMainWindow,
        QMessageBox,
        QPushButton,
        QTableWidget,
        QTableWidgetItem,
        QVBoxLayout,
        QWidget,
    )
except ImportError as exc:  # pragma: no cover - exercised when launching GUI without dependencies.
    raise RuntimeError("PySide6 is required for the desktop GUI. Install with: pip install PySide6") from exc

from curve_extractor.app.image_io import load_image_rgb
from curve_extractor.app.image_view import ImageView, pixmap_from_rgb
from curve_extractor.core.auto_calibration import auto_calibrate_from_ocr, run_tesseract_ocr
from curve_extractor.core.calibration import PlotCalibration, YAxisConfig
from curve_extractor.core.color_cluster import ColorCandidate, find_color_candidates
from curve_extractor.core.extraction import ExtractionResult, SeriesConfig, extract_series
from curve_extractor.core.export import export_csv


class MainWindow(QMainWindow):
    def __init__(self) -> None:
        super().__init__()
        self.setWindowTitle("彩色曲线图数据提取")
        self.resize(1180, 760)
        self.image_rgb: np.ndarray | None = None
        self.image_path: Path | None = None
        self.candidates: list[ColorCandidate] = []
        self.exclusion_regions: list[tuple[int, int, int, int]] = []
        self.last_result: ExtractionResult | None = None
        self.pick_mode: str | None = None
        self.plot_left_top: tuple[int, int] | None = None
        self.plot_right_bottom: tuple[int, int] | None = None
        self._build_ui()

    def _build_ui(self) -> None:
        central = QWidget()
        layout = QHBoxLayout(central)
        self.image_view = ImageView()
        self.image_view.point_selected.connect(self._handle_point_selected)
        self.image_view.rectangle_selected.connect(self._handle_rectangle_selected)
        layout.addWidget(self.image_view, 2)
        layout.addWidget(self._build_controls(), 1)
        self.setCentralWidget(central)
        self.statusBar().showMessage("导入图片后开始校准")

    def _build_controls(self) -> QWidget:
        panel = QWidget()
        layout = QVBoxLayout(panel)
        layout.addWidget(self._build_image_group())
        layout.addWidget(self._build_calibration_group())
        layout.addWidget(self._build_y_axis_group())
        layout.addWidget(self._build_color_group())
        layout.addWidget(self._build_series_group())
        layout.addWidget(self._build_result_group())
        layout.addStretch(1)
        return panel

    def _build_image_group(self) -> QGroupBox:
        group = QGroupBox("图片")
        layout = QVBoxLayout(group)
        open_button = QPushButton("导入图片")
        open_button.clicked.connect(self.open_image)
        layout.addWidget(open_button)
        self.image_label = QLabel("未导入")
        layout.addWidget(self.image_label)
        return group

    def _build_calibration_group(self) -> QGroupBox:
        group = QGroupBox("绘图区与 X 轴")
        layout = QGridLayout(group)
        self.top_left_label = QLabel("左上: 未选择")
        self.bottom_right_label = QLabel("右下: 未选择")
        top_left_button = QPushButton("点选左上")
        bottom_right_button = QPushButton("点选右下")
        auto_button = QPushButton("自动识别坐标轴")
        top_left_button.clicked.connect(lambda: self._set_pick_mode("top_left"))
        bottom_right_button.clicked.connect(lambda: self._set_pick_mode("bottom_right"))
        auto_button.clicked.connect(self.auto_detect_axes)
        self.x_min_edit = QLineEdit("0")
        self.x_max_edit = QLineEdit("1")
        layout.addWidget(top_left_button, 0, 0)
        layout.addWidget(self.top_left_label, 0, 1)
        layout.addWidget(bottom_right_button, 1, 0)
        layout.addWidget(self.bottom_right_label, 1, 1)
        layout.addWidget(auto_button, 2, 0, 1, 2)
        layout.addWidget(QLabel("X min"), 3, 0)
        layout.addWidget(self.x_min_edit, 3, 1)
        layout.addWidget(QLabel("X max"), 4, 0)
        layout.addWidget(self.x_max_edit, 4, 1)
        return group

    def _build_y_axis_group(self) -> QGroupBox:
        group = QGroupBox("Y 轴")
        layout = QVBoxLayout(group)
        self.y_axis_table = QTableWidget(0, 4)
        self.y_axis_table.setHorizontalHeaderLabels(["名称", "单位", "最小值", "最大值"])
        self.y_axis_table.horizontalHeader().setSectionResizeMode(QHeaderView.ResizeMode.Stretch)
        layout.addWidget(self.y_axis_table)
        buttons = QHBoxLayout()
        add_button = QPushButton("添加 Y 轴")
        remove_button = QPushButton("删除选中")
        add_button.clicked.connect(self.add_y_axis_row)
        remove_button.clicked.connect(lambda: self._remove_selected_rows(self.y_axis_table))
        buttons.addWidget(add_button)
        buttons.addWidget(remove_button)
        layout.addLayout(buttons)
        self.add_y_axis_row("value", "", "0", "1")
        return group

    def _build_color_group(self) -> QGroupBox:
        group = QGroupBox("自动颜色候选")
        layout = QVBoxLayout(group)
        detect_button = QPushButton("识别候选颜色")
        detect_button.clicked.connect(self.detect_colors)
        layout.addWidget(detect_button)
        self.color_table = QTableWidget(0, 4)
        self.color_table.setHorizontalHeaderLabels(["颜色", "RGB", "像素数", "占比"])
        self.color_table.horizontalHeader().setSectionResizeMode(QHeaderView.ResizeMode.Stretch)
        self.color_table.setSelectionBehavior(QAbstractItemView.SelectionBehavior.SelectRows)
        layout.addWidget(self.color_table)
        add_button = QPushButton("添加为曲线")
        add_button.clicked.connect(self.add_selected_candidate_as_series)
        layout.addWidget(add_button)
        return group

    def _build_series_group(self) -> QGroupBox:
        group = QGroupBox("曲线绑定")
        layout = QVBoxLayout(group)
        self.series_table = QTableWidget(0, 7)
        self.series_table.setHorizontalHeaderLabels(["名称", "单位", "R", "G", "B", "容差", "Y轴"])
        self.series_table.horizontalHeader().setSectionResizeMode(QHeaderView.ResizeMode.Stretch)
        layout.addWidget(self.series_table)
        buttons = QHBoxLayout()
        add_button = QPushButton("手动添加")
        remove_button = QPushButton("删除选中")
        add_button.clicked.connect(lambda: self.add_series_row("series", "", (255, 0, 0), "45", "value"))
        remove_button.clicked.connect(lambda: self._remove_selected_rows(self.series_table))
        buttons.addWidget(add_button)
        buttons.addWidget(remove_button)
        layout.addLayout(buttons)
        return group

    def _build_result_group(self) -> QGroupBox:
        group = QGroupBox("提取与导出")
        layout = QVBoxLayout(group)
        extract_button = QPushButton("提取并预览")
        exclude_button = QPushButton("框选排除区域")
        clear_exclude_button = QPushButton("清空排除区域")
        export_button = QPushButton("导出 CSV")
        extract_button.clicked.connect(self.extract_and_preview)
        exclude_button.clicked.connect(self.start_exclusion_selection)
        clear_exclude_button.clicked.connect(self.clear_exclusions)
        export_button.clicked.connect(self.export_result)
        layout.addWidget(extract_button)
        layout.addWidget(exclude_button)
        layout.addWidget(clear_exclude_button)
        layout.addWidget(export_button)
        self.exclusion_label = QLabel("排除区域: 0")
        layout.addWidget(self.exclusion_label)
        return group

    def open_image(self) -> None:
        file_path, _ = QFileDialog.getOpenFileName(
            self,
            "选择图片",
            "",
            "Images (*.png *.jpg *.jpeg *.bmp *.tif *.tiff)",
        )
        if not file_path:
            return
        try:
            self.image_rgb = load_image_rgb(file_path)
        except Exception as exc:  # noqa: BLE001 - GUI should surface any load failure.
            QMessageBox.critical(self, "导入失败", str(exc))
            return
        self.image_path = Path(file_path)
        self.image_view.set_image(self.image_rgb)
        self.image_label.setText(self.image_path.name)
        self.plot_left_top = None
        self.plot_right_bottom = None
        self.exclusion_regions.clear()
        self._update_plot_labels()
        self._update_exclusion_label()
        self.statusBar().showMessage("图片已导入，请点选绘图区左上和右下")

    def add_y_axis_row(self, name: str = "value", unit: str = "", y_min: str = "0", y_max: str = "1") -> None:
        row = self.y_axis_table.rowCount()
        self.y_axis_table.insertRow(row)
        for column, value in enumerate([name, unit, y_min, y_max]):
            self.y_axis_table.setItem(row, column, QTableWidgetItem(str(value)))

    def add_series_row(
        self,
        name: str,
        unit: str,
        rgb: tuple[int, int, int],
        tolerance: str,
        y_axis: str,
    ) -> None:
        row = self.series_table.rowCount()
        self.series_table.insertRow(row)
        values = [name, unit, str(rgb[0]), str(rgb[1]), str(rgb[2]), str(tolerance), y_axis]
        for column, value in enumerate(values):
            self.series_table.setItem(row, column, QTableWidgetItem(value))

    def detect_colors(self) -> None:
        try:
            calibration = self._calibration()
            if self.image_rgb is None:
                raise ValueError("请先导入图片")
            self.candidates = find_color_candidates(self.image_rgb, calibration, max_colors=8, min_pixels=20)
        except Exception as exc:  # noqa: BLE001
            QMessageBox.warning(self, "无法识别颜色", str(exc))
            return
        self.color_table.setRowCount(0)
        for candidate in self.candidates:
            row = self.color_table.rowCount()
            self.color_table.insertRow(row)
            swatch = QTableWidgetItem("")
            swatch.setBackground(QColor(*candidate.rgb))
            self.color_table.setItem(row, 0, swatch)
            self.color_table.setItem(row, 1, QTableWidgetItem(str(candidate.rgb)))
            self.color_table.setItem(row, 2, QTableWidgetItem(str(candidate.pixel_count)))
            self.color_table.setItem(row, 3, QTableWidgetItem(f"{candidate.fraction:.2%}"))
        self.statusBar().showMessage(f"识别到 {len(self.candidates)} 个候选颜色")

    def auto_detect_axes(self) -> None:
        if self.image_rgb is None:
            QMessageBox.information(self, "未导入图片", "请先导入图片")
            return
        try:
            ocr_texts = run_tesseract_ocr(self.image_rgb)
            result = auto_calibrate_from_ocr(self.image_rgb, ocr_texts)
        except Exception as exc:  # noqa: BLE001
            QMessageBox.warning(
                self,
                "自动识别失败",
                f"{exc}\n\n请安装 Tesseract OCR 后重试，或继续使用手动校准。",
            )
            return
        calibration = result.calibration
        self.plot_left_top = (calibration.left, calibration.top)
        self.plot_right_bottom = (calibration.right, calibration.bottom)
        self.x_min_edit.setText(f"{calibration.x_min:.6g}")
        self.x_max_edit.setText(f"{calibration.x_max:.6g}")
        self.y_axis_table.setRowCount(0)
        for axis in calibration.y_axes.values():
            self.add_y_axis_row(axis.name, axis.unit, f"{axis.y_min:.6g}", f"{axis.y_max:.6g}")
        self._update_plot_labels()
        self.statusBar().showMessage(
            f"自动识别完成: X={calibration.x_min:.3g}..{calibration.x_max:.3g}, "
            f"Y轴={len(calibration.y_axes)}"
        )

    def add_selected_candidate_as_series(self) -> None:
        selected = self.color_table.selectionModel().selectedRows()
        if not selected:
            QMessageBox.information(self, "未选择颜色", "请先在候选颜色表中选择一行")
            return
        row = selected[0].row()
        candidate = self.candidates[row]
        default_axis = next(iter(self._y_axis_names()), "value")
        self.add_series_row(f"series_{self.series_table.rowCount() + 1}", "", candidate.rgb, "45", default_axis)

    def extract_and_preview(self) -> None:
        try:
            if self.image_rgb is None:
                raise ValueError("请先导入图片")
            calibration = self._calibration()
            series_configs = self._series_configs()
            self.last_result = extract_series(
                self.image_rgb,
                calibration,
                series_configs,
                exclusion_regions=self.exclusion_regions,
                max_interpolation_gap=4,
            )
        except Exception as exc:  # noqa: BLE001
            QMessageBox.warning(self, "提取失败", str(exc))
            return
        self.image_view.set_overlay_pixmap(self._build_preview_pixmap(self.last_result, calibration))
        self.statusBar().showMessage("提取完成，可检查叠加预览或导出 CSV")

    def start_exclusion_selection(self) -> None:
        if self.image_rgb is None:
            QMessageBox.information(self, "未导入图片", "请先导入图片")
            return
        self.image_view.enable_rectangle_selection()
        self.statusBar().showMessage("在图片上拖拽框选需要排除的区域")

    def clear_exclusions(self) -> None:
        self.exclusion_regions.clear()
        self._update_exclusion_label()
        if self.image_rgb is not None:
            self.image_view.set_image(self.image_rgb)
        self.statusBar().showMessage("排除区域已清空")

    def export_result(self) -> None:
        if self.last_result is None:
            QMessageBox.information(self, "没有结果", "请先提取并预览")
            return
        file_path, _ = QFileDialog.getSaveFileName(self, "导出 CSV", "extracted.csv", "CSV (*.csv)")
        if not file_path:
            return
        try:
            export_csv(self.last_result, file_path)
        except Exception as exc:  # noqa: BLE001
            QMessageBox.critical(self, "导出失败", str(exc))
            return
        self.statusBar().showMessage(f"已导出: {file_path}")

    def _set_pick_mode(self, mode: str) -> None:
        if self.image_rgb is None:
            QMessageBox.information(self, "未导入图片", "请先导入图片")
            return
        self.pick_mode = mode
        self.statusBar().showMessage("请在图片上点击对应绘图区角点")

    def _handle_point_selected(self, x: int, y: int) -> None:
        if self.pick_mode == "top_left":
            self.plot_left_top = (x, y)
        elif self.pick_mode == "bottom_right":
            self.plot_right_bottom = (x, y)
        else:
            self.statusBar().showMessage(f"像素: ({x}, {y})")
            return
        self.pick_mode = None
        self._update_plot_labels()
        self.statusBar().showMessage("角点已记录")

    def _handle_rectangle_selected(self, region: tuple[int, int, int, int]) -> None:
        self.exclusion_regions.append(region)
        self._update_exclusion_label()
        self.statusBar().showMessage("已添加排除区域，请重新提取预览")

    def _update_plot_labels(self) -> None:
        self.top_left_label.setText(f"左上: {self.plot_left_top}" if self.plot_left_top else "左上: 未选择")
        self.bottom_right_label.setText(
            f"右下: {self.plot_right_bottom}" if self.plot_right_bottom else "右下: 未选择"
        )

    def _update_exclusion_label(self) -> None:
        self.exclusion_label.setText(f"排除区域: {len(self.exclusion_regions)}")

    def _calibration(self) -> PlotCalibration:
        if self.plot_left_top is None or self.plot_right_bottom is None:
            raise ValueError("请先点选绘图区左上和右下")
        x1, y1 = self.plot_left_top
        x2, y2 = self.plot_right_bottom
        left, right = sorted((x1, x2))
        top, bottom = sorted((y1, y2))
        y_axes = self._y_axes()
        return PlotCalibration(
            left=left,
            top=top,
            right=right,
            bottom=bottom,
            x_min=float(self.x_min_edit.text()),
            x_max=float(self.x_max_edit.text()),
            y_axes=y_axes,
        )

    def _y_axes(self) -> dict[str, YAxisConfig]:
        axes: dict[str, YAxisConfig] = {}
        for row in range(self.y_axis_table.rowCount()):
            name = self._table_text(self.y_axis_table, row, 0)
            unit = self._table_text(self.y_axis_table, row, 1)
            if not name:
                continue
            axes[name] = YAxisConfig(
                name=name,
                unit=unit,
                y_min=float(self._table_text(self.y_axis_table, row, 2)),
                y_max=float(self._table_text(self.y_axis_table, row, 3)),
            )
        if not axes:
            raise ValueError("请至少配置一个 Y 轴")
        return axes

    def _series_configs(self) -> list[SeriesConfig]:
        configs: list[SeriesConfig] = []
        for row in range(self.series_table.rowCount()):
            name = self._table_text(self.series_table, row, 0)
            if not name:
                continue
            rgb = (
                int(self._table_text(self.series_table, row, 2)),
                int(self._table_text(self.series_table, row, 3)),
                int(self._table_text(self.series_table, row, 4)),
            )
            configs.append(
                SeriesConfig(
                    name=name,
                    unit=self._table_text(self.series_table, row, 1),
                    rgb=rgb,
                    tolerance=float(self._table_text(self.series_table, row, 5)),
                    y_axis=self._table_text(self.series_table, row, 6),
                )
            )
        if not configs:
            raise ValueError("请至少添加一条曲线")
        return configs

    def _y_axis_names(self) -> list[str]:
        return [self._table_text(self.y_axis_table, row, 0) for row in range(self.y_axis_table.rowCount())]

    def _build_preview_pixmap(self, result: ExtractionResult, calibration: PlotCalibration):
        if self.image_rgb is None:
            raise ValueError("no image loaded")
        pixmap = pixmap_from_rgb(self.image_rgb)
        painter = QPainter(pixmap)
        painter.setPen(QPen(QColor(0, 0, 0), 1, Qt.PenStyle.DashLine))
        painter.drawRect(calibration.left, calibration.top, calibration.width - 1, calibration.height - 1)
        palette = [
            QColor(255, 0, 0),
            QColor(0, 190, 0),
            QColor(0, 70, 255),
            QColor(230, 120, 0),
            QColor(170, 0, 200),
        ]
        for index, (name, path) in enumerate(result.preview_paths.items()):
            painter.setPen(QPen(palette[index % len(palette)], 2))
            if len(path) > 1:
                for start, end in zip(path[:-1], path[1:]):
                    painter.drawLine(start[0], start[1], end[0], end[1])
            for x, y in path[:: max(1, len(path) // 150 or 1)]:
                painter.drawEllipse(x - 1, y - 1, 2, 2)
        painter.setPen(QPen(QColor(255, 180, 0), 2, Qt.PenStyle.DashLine))
        for x1, y1, x2, y2 in self.exclusion_regions:
            left, right = sorted((x1, x2))
            top, bottom = sorted((y1, y2))
            painter.drawRect(left, top, right - left, bottom - top)
        painter.end()
        return pixmap

    @staticmethod
    def _table_text(table: QTableWidget, row: int, column: int) -> str:
        item = table.item(row, column)
        return item.text().strip() if item else ""

    @staticmethod
    def _remove_selected_rows(table: QTableWidget) -> None:
        rows = sorted({index.row() for index in table.selectionModel().selectedRows()}, reverse=True)
        for row in rows:
            table.removeRow(row)


def run() -> int:
    app = QApplication([])
    window = MainWindow()
    window.show()
    return app.exec()
