from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path

import numpy as np

from curve_extractor.core.docx_batch import DocxPlotImage
from curve_extractor.core.pipeline import BatchExtractionResult, has_curve_color_signal, process_docx_batch


def test_process_docx_batch_writes_outputs_and_keeps_going_after_failure(tmp_path: Path):
    items = [
        DocxPlotImage(
            pic_number=1,
            image_index=1,
            output_stem="pic_001",
            statement="Power is 91.29MW.",
            media_name="word/media/image1.png",
            image_rgb=np.full((10, 12, 3), 255, dtype=np.uint8),
            statement_image_count=1,
            statement_image_media_names=("word/media/table1.png",),
        ),
        DocxPlotImage(
            pic_number=2,
            image_index=1,
            output_stem="pic_002",
            statement="",
            media_name="word/media/image2.png",
            image_rgb=np.full((10, 12, 3), 255, dtype=np.uint8),
        ),
    ]

    def extractor(item: DocxPlotImage, output_prefix: Path) -> BatchExtractionResult:
        if item.pic_number == 2:
            raise ValueError("synthetic failure")
        csv_path = output_prefix.with_suffix(".csv")
        csv_path.write_text("x,power_MW\n0,91.29\n", encoding="utf-8-sig")
        for suffix in ["_overlay.png", "_side_by_side.png", "_color_fit.png"]:
            output_prefix.with_name(output_prefix.name + suffix).write_bytes(b"png")
        return BatchExtractionResult(
            output_stem=item.output_stem,
            pic_number=item.pic_number,
            image_index=item.image_index,
            status="ok",
            statement_assistance="statement parsed",
            csv_path=csv_path,
            overlay_path=output_prefix.with_name(output_prefix.name + "_overlay.png"),
            side_by_side_path=output_prefix.with_name(output_prefix.name + "_side_by_side.png"),
            color_fit_path=output_prefix.with_name(output_prefix.name + "_color_fit.png"),
            metrics_path=output_prefix.with_name(output_prefix.name + "_metrics.csv"),
            source_coverage_min=0.95,
            path_on_source_min=0.96,
            missing_fraction_max=0.01,
            error="",
        )

    results = process_docx_batch(items, tmp_path / "outputs", extractor=extractor)

    assert [result.status for result in results] == ["ok", "failed"]
    assert (tmp_path / "outputs" / "pic_001.csv").exists()
    assert (tmp_path / "outputs" / "batch_summary.csv").exists()
    summary = (tmp_path / "outputs" / "batch_summary.txt").read_text(encoding="utf-8")
    assert "pic_001: ok" in summary
    assert "pic_002: failed - synthetic failure" in summary
    csv_summary = (tmp_path / "outputs" / "batch_summary.csv").read_text(encoding="utf-8-sig")
    assert "statement_image_count" in csv_summary
    assert "word/media/table1.png" in csv_summary


def test_has_curve_color_signal_rejects_table_like_image_without_rgb_curves():
    table = np.full((80, 100, 3), 255, dtype=np.uint8)
    table[20:50, 20:60] = (255, 255, 0)
    table[25:27, 15:45] = (230, 20, 20)
    table[45:47, 15:45] = (20, 20, 230)
    table[::10, :] = 0
    table[:, ::10] = 0
    plot = np.full((80, 100, 3), 255, dtype=np.uint8)
    plot[20, 10:90] = (230, 20, 20)
    plot[40, 10:90] = (20, 230, 20)
    plot[60, 10:90] = (20, 20, 230)

    assert not has_curve_color_signal(table)
    assert has_curve_color_signal(plot)
