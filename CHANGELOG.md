# Changelog

All notable changes to this project will be documented in this file.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.1.0/),
and this project adheres to [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

## [0.2.0] - 2026-09-13

### Added
- Windows desktop packaging: `scripts/build_windows.bat` and `CurveExtractor.spec` produce a windowed `CurveExtractor.exe` (same GUI as `python -m curve_extractor`).
- GUI first-run banner when Tesseract is not on `PATH` / `TESSERACT_CMD`. The banner does not claim OCR works without Tesseract. Manual plot-box and axis-range entry still works.
- README Windows executable section. Tesseract remains a separate install (axis tick OCR only; not bundled in the exe).

### Changed
- Package version `0.1.0` → `0.2.0`.
- Tesseract lookup also checks `tesseract.exe` and the usual Windows install folders so a default UB Mannheim install can be found without `PATH`.

### Notes
- CLI is unchanged: `python -m curve_extractor.cli`.
- Local-only MIT tool. Linear axes, white-background RGB plots. No web version. No accuracy guarantees.

## [0.1.0] - 2026-08-12

### Added
- First public release: PySide6 GUI, CLI (`python -m curve_extractor.cli`), and DOCX batch extraction.
- Color-curve extraction for white-background RGB plots with linear axes.
- Optional Tesseract OCR for axis tick labels only.

[0.2.0]: https://github.com/AL-LIN-S/DataExtracker/compare/v0.1.0...HEAD
[0.1.0]: https://github.com/AL-LIN-S/DataExtracker/releases/tag/v0.1.0
