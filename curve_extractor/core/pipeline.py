from __future__ import annotations

from dataclasses import dataclass
from dataclasses import replace
from pathlib import Path
from typing import Callable, Iterable

import numpy as np
import pandas as pd

from curve_extractor.core.auto_bind import auto_bind_series
from curve_extractor.core.auto_calibration import auto_calibrate_from_ocr, run_tesseract_ocr
from curve_extractor.core.color_cluster import find_color_candidates
from curve_extractor.core.comparison import build_comparison_artifacts
from curve_extractor.core.docx_batch import DocxPlotImage, iter_docx_plot_images
from curve_extractor.core.extraction import extract_series
from curve_extractor.core.export import export_csv
from curve_extractor.core.image_kind import has_curve_color_signal
from curve_extractor.core.statement import parse_statement_hints, validate_result_with_statement


class NonPlotImageError(ValueError):
    pass


@dataclass(frozen=True)
class BatchExtractionResult:
    output_stem: str
    pic_number: int
    image_index: int
    status: str
    statement_assistance: str
    csv_path: Path | None = None
    overlay_path: Path | None = None
    side_by_side_path: Path | None = None
    color_fit_path: Path | None = None
    metrics_path: Path | None = None
    source_coverage_min: float | None = None
    path_on_source_min: float | None = None
    missing_fraction_max: float | None = None
    error: str = ""
    statement_validation: str = ""
    warnings: str = ""
    statement_image_count: int = 0
    statement_image_media_names: tuple[str, ...] = ()


Extractor = Callable[[DocxPlotImage, Path], BatchExtractionResult]


def process_docx_batch(
    source: str | Path | Iterable[DocxPlotImage],
    output_dir: str | Path,
    *,
    extractor: Extractor | None = None,
) -> list[BatchExtractionResult]:
    output_path = Path(output_dir)
    output_path.mkdir(parents=True, exist_ok=True)
    items = iter_docx_plot_images(source) if isinstance(source, (str, Path)) else list(source)
    active_extractor = extractor or extract_docx_plot_image
    results: list[BatchExtractionResult] = []
    for item in items:
        prefix = output_path / item.output_stem
        try:
            result = active_extractor(item, prefix)
            results.append(_attach_statement_image_metadata(result, item))
        except NonPlotImageError as exc:
            results.append(
                BatchExtractionResult(
                    output_stem=item.output_stem,
                    pic_number=item.pic_number,
                    image_index=item.image_index,
                    status="skipped",
                    statement_assistance=parse_statement_hints(item.statement).assistance_note,
                    error=str(exc),
                    statement_image_count=item.statement_image_count,
                    statement_image_media_names=item.statement_image_media_names,
                )
            )
        except Exception as exc:  # noqa: BLE001 - batch processing records per-image failures.
            results.append(
                BatchExtractionResult(
                    output_stem=item.output_stem,
                    pic_number=item.pic_number,
                    image_index=item.image_index,
                    status="failed",
                    statement_assistance=parse_statement_hints(item.statement).assistance_note,
                    error=str(exc),
                    statement_image_count=item.statement_image_count,
                    statement_image_media_names=item.statement_image_media_names,
                )
            )
    _write_batch_summary(results, output_path)
    return results


def extract_docx_plot_image(item: DocxPlotImage, output_prefix: str | Path) -> BatchExtractionResult:
    prefix = Path(output_prefix)
    prefix.parent.mkdir(parents=True, exist_ok=True)
    hints = parse_statement_hints(item.statement)
    if not has_curve_color_signal(item.image_rgb):
        raise NonPlotImageError("skipped non-plot image: no red/green/blue curve signal")
    ocr_texts = run_tesseract_ocr(item.image_rgb)
    auto = auto_calibrate_from_ocr(item.image_rgb, ocr_texts)
    calibration = auto.calibration
    candidates = find_color_candidates(item.image_rgb, calibration, max_colors=8, min_pixels=20)
    configs = auto_bind_series(candidates, calibration)
    if not configs:
        raise ValueError("automatic binding found no usable red/green/blue series")

    result = extract_series(item.image_rgb, calibration, configs, max_interpolation_gap=4)
    csv_path = export_csv(result, prefix.with_suffix(".csv"))
    artifacts = build_comparison_artifacts(item.image_rgb, calibration, result, configs, prefix)
    metrics = list(artifacts.metrics.values())
    statement_validation = validate_result_with_statement(result, hints)
    warnings = "; ".join(auto.warnings)
    return BatchExtractionResult(
        output_stem=item.output_stem,
        pic_number=item.pic_number,
        image_index=item.image_index,
        status="ok",
        statement_assistance=hints.assistance_note,
        csv_path=csv_path,
        overlay_path=artifacts.overlay_path,
        side_by_side_path=artifacts.side_by_side_path,
        color_fit_path=artifacts.color_fit_path,
        metrics_path=artifacts.metrics_path,
        source_coverage_min=_minimum_metric(metrics, "source_coverage_fraction"),
        path_on_source_min=_minimum_metric(metrics, "path_on_source_fraction"),
        missing_fraction_max=_maximum_metric(metrics, "missing_fraction"),
        statement_validation=statement_validation,
        warnings=warnings,
        statement_image_count=item.statement_image_count,
        statement_image_media_names=item.statement_image_media_names,
    )


def _write_batch_summary(results: list[BatchExtractionResult], output_dir: Path) -> None:
    rows = []
    for result in results:
        rows.append(
            {
                "output_stem": result.output_stem,
                "pic_number": result.pic_number,
                "image_index": result.image_index,
                "status": result.status,
                "statement_assistance": result.statement_assistance,
                "statement_validation": result.statement_validation,
                "source_coverage_min": result.source_coverage_min,
                "path_on_source_min": result.path_on_source_min,
                "missing_fraction_max": result.missing_fraction_max,
                "csv_path": _path_text(result.csv_path),
                "overlay_path": _path_text(result.overlay_path),
                "side_by_side_path": _path_text(result.side_by_side_path),
                "color_fit_path": _path_text(result.color_fit_path),
                "metrics_path": _path_text(result.metrics_path),
                "warnings": result.warnings,
                "error": result.error,
                "statement_image_count": result.statement_image_count,
                "statement_image_media_names": ";".join(result.statement_image_media_names),
            }
        )
    pd.DataFrame(rows).to_csv(output_dir / "batch_summary.csv", index=False, encoding="utf-8-sig")
    lines = []
    for result in results:
        if result.status == "ok":
            lines.append(
                f"{result.output_stem}: ok - coverage_min={_format_optional(result.source_coverage_min)}, "
                f"path_on_source_min={_format_optional(result.path_on_source_min)}, "
                f"missing_max={_format_optional(result.missing_fraction_max)}, "
                f"{result.statement_validation or result.statement_assistance}"
            )
        elif result.status == "skipped":
            lines.append(f"{result.output_stem}: skipped - {result.error}")
        else:
            lines.append(f"{result.output_stem}: failed - {result.error}")
    (output_dir / "batch_summary.txt").write_text("\n".join(lines) + "\n", encoding="utf-8")


def _attach_statement_image_metadata(result: BatchExtractionResult, item: DocxPlotImage) -> BatchExtractionResult:
    if result.statement_image_count or not item.statement_image_count:
        return result
    return replace(
        result,
        statement_image_count=item.statement_image_count,
        statement_image_media_names=item.statement_image_media_names,
    )


def _minimum_metric(metrics: list[object], attribute: str) -> float | None:
    values = [float(getattr(metric, attribute)) for metric in metrics]
    return min(values) if values else None


def _maximum_metric(metrics: list[object], attribute: str) -> float | None:
    values = [float(getattr(metric, attribute)) for metric in metrics]
    return max(values) if values else None


def _format_optional(value: float | None) -> str:
    return "" if value is None or not np.isfinite(value) else f"{value:.3f}"


def _path_text(path: Path | None) -> str:
    return "" if path is None else str(path)
