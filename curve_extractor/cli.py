from __future__ import annotations

import argparse
from pathlib import Path

from curve_extractor.app.image_io import load_image_rgb
from curve_extractor.core.auto_bind import auto_bind_series
from curve_extractor.core.auto_calibration import auto_calibrate_from_ocr, run_tesseract_ocr
from curve_extractor.core.color_cluster import find_color_candidates
from curve_extractor.core.extraction import SeriesConfig, extract_series
from curve_extractor.core.export import export_csv
from curve_extractor.core.pipeline import process_docx_batch


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="Automatically extract colored curves from a plot image or docx summary.")
    parser.add_argument("image", type=Path, help="Input plot image or DOCX report")
    parser.add_argument("--output", type=Path, default=Path("extracted.csv"), help="Output CSV path")
    parser.add_argument("--output-dir", type=Path, default=Path("outputs"), help="Output directory for docx batch mode")
    parser.add_argument(
        "--series",
        action="append",
        default=[],
        metavar="NAME:UNIT:R,G,B:TOLERANCE:Y_AXIS",
        help="Series binding. Example: power:MW:0,255,0:45:right_1",
    )
    parser.add_argument("--max-colors", type=int, default=6, help="Number of color candidates to print")
    args = parser.parse_args(argv)

    if args.image.suffix.lower() == ".docx":
        results = process_docx_batch(args.image, args.output_dir)
        ok_count = sum(1 for result in results if result.status == "ok")
        skipped_count = sum(1 for result in results if result.status == "skipped")
        failed_count = sum(1 for result in results if result.status == "failed")
        print(f"Processed {len(results)} plot images from {args.image}")
        print(f"Successful: {ok_count}; skipped: {skipped_count}; failed: {failed_count}")
        print("Wrote batch outputs to:", args.output_dir)
        print("Summary:", args.output_dir / "batch_summary.csv")
        return 0 if failed_count == 0 else 2

    image = load_image_rgb(args.image)
    ocr = run_tesseract_ocr(image)
    auto = auto_calibrate_from_ocr(image, ocr)

    print("Detected plot area:", (auto.calibration.left, auto.calibration.top, auto.calibration.right, auto.calibration.bottom))
    print("Detected x range:", f"{auto.calibration.x_min:.6g}", "to", f"{auto.calibration.x_max:.6g}")
    print("Detected y axes:")
    for name, axis in auto.calibration.y_axes.items():
        print(f"  {name}: {axis.y_min:.6g} to {axis.y_max:.6g}")

    candidates = find_color_candidates(image, auto.calibration, max_colors=args.max_colors)
    print("Color candidates:")
    for index, candidate in enumerate(candidates, start=1):
        print(f"  {index}: rgb={candidate.rgb} pixels={candidate.pixel_count} fraction={candidate.fraction:.2%}")

    if args.series:
        configs = [_parse_series(value) for value in args.series]
    else:
        configs = auto_bind_series(candidates, auto.calibration)
        if not configs:
            print("No --series binding supplied and automatic binding found no usable red/green/blue series.")
            return 1
        print("Automatic series bindings:")
        for config in configs:
            print(f"  {config.name}_{config.unit}: rgb={config.rgb} tolerance={config.tolerance:g} y_axis={config.y_axis}")

    result = extract_series(image, auto.calibration, configs, max_interpolation_gap=4)
    export_csv(result, args.output)
    print("Wrote:", args.output)
    return 0


def _parse_series(value: str) -> SeriesConfig:
    try:
        name, unit, rgb_text, tolerance, y_axis = value.split(":", 4)
        rgb = tuple(int(part) for part in rgb_text.split(","))
    except ValueError as exc:
        raise SystemExit(f"invalid --series value: {value}") from exc
    if len(rgb) != 3:
        raise SystemExit(f"invalid RGB value: {rgb_text}")
    return SeriesConfig(name=name, unit=unit, rgb=rgb, tolerance=float(tolerance), y_axis=y_axis)


if __name__ == "__main__":
    raise SystemExit(main())
