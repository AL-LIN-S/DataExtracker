# Curve Extractor

[English](README.md) | [中文](README.zh-CN.md)

**Digitize colored engineering plots to CSV** — CLI + PySide6 GUI, with automatic overlay verification.

Built for white-background plots with saturated red / green / blue curves, black or gray grids, and linear axes. Optional statement or table images in a DOCX can be used as validation hints.

![Input plot → overlay preview](docs/images/03_side_by_side.png)

## Why this tool

Compared with typical plot digitizers, Curve Extractor focuses on:

- **Colored multi-curve** extraction (R/G/B candidates + binding)
- **Multiple Y-axes** with automatic or manual series binding
- **DOCX batch** mode (`Pic n` / `Statement n` layout)
- **Review artifacts** every run: overlay, side-by-side redraw, color-fit check, metrics

## Try in 30 seconds

Python 3.10+ required. From the repo root:

```bash
python -m venv .venv
# Windows PowerShell: .\.venv\Scripts\Activate.ps1
# macOS / Linux:
source .venv/bin/activate

python -m pip install -U pip
python -m pip install -e .
python -m curve_extractor.cli examples/sample_rgb_plot.png --output extracted.csv
```

You should get a wide CSV (`x`, then one column per series). For DOCX batch mode, pass a `.docx` and `--output-dir`.

**GUI:**

```bash
python -m curve_extractor
# or: curve-extractor
```

### Tesseract (for automatic axis OCR)

Install the Tesseract executable separately and put it on `PATH`, or set `TESSERACT_CMD`.

| OS | Typical install |
|---|---|
| Windows | [UB Mannheim installer](https://github.com/UB-Mannheim/tesseract/wiki) then `$env:TESSERACT_CMD = "C:\Program Files\Tesseract-OCR\tesseract.exe"` |
| macOS | `brew install tesseract` |
| Linux | `sudo apt install tesseract-ocr` (or your distro equivalent) |


## First success on Windows

If auto axis detection fails, it is usually Tesseract. Use this path:

![Windows first run](docs/images/04_windows_first_run.png)

1. Install Python 3.10+.
2. Install [Tesseract for Windows](https://github.com/UB-Mannheim/tesseract/wiki) and add `tesseract.exe` to `PATH` **or** set:

```powershell
$env:TESSERACT_CMD = "C:\Program Files\Tesseract-OCR\tesseract.exe"
```

3. `python -m pip install -e .`
4. Open the GUI (`python -m curve_extractor`) and calibrate the plot area manually if OCR misses ticks — you can still extract after manual axis setup.
5. Or run the sample: `python -m curve_extractor.cli examples/sample_rgb_plot.png --output extracted.csv`

Demo flow (input → overlay → side-by-side):

![Demo flow](docs/images/demo_flow.gif)

## Screenshots

| Input | Overlay preview |
|---|---|
| ![input](docs/images/01_input_plot.png) | ![overlay](docs/images/02_overlay_preview.png) |

Synthetic demo images live under [`examples/`](examples/) (safe sample data, no private reports).

## Features

- Detects the plot area and axis tick labels with OCR
- Finds saturated colored curve candidates inside the plot area
- Extracts one value per x-pixel column and exports a wide CSV
- Supports multiple y-axes and automatic red / green / blue series binding
- Review artifacts: overlay, side-by-side, color-fit image, per-series metrics
- DOCX batch: `Pic n` + `Statement n`; table-like images treated as statement/validation input
- PySide6 desktop GUI for manual calibration and review

## Command-line usage

Console script (after install): `curve-extractor-cli`  
Module form: `python -m curve_extractor.cli`

Single image:

```bash
python -m curve_extractor.cli path/to/plot.png --output extracted.csv
```

Explicit series binding when auto-bind is wrong:

```bash
python -m curve_extractor.cli path/to/plot.png \
  --output extracted.csv \
  --series "power:MW:0,235,0:45:right_1"
```

`--series` format: `NAME:UNIT:R,G,B:TOLERANCE:Y_AXIS`

DOCX batch:

```bash
python -m curve_extractor.cli path/to/summary.docx --output-dir outputs
```

Expected DOCX shape:

```text
Pic 1:
[plot image]
Statement 1:
[optional validation text]

Pic 2:
[plot image]
[optional table image]
Statement 2:
[optional validation text]
```

## GUI workflow

1. Open an image  
2. Run automatic axis detection, or select the plot area manually  
3. Review or edit x/y axis ranges  
4. Detect curve colors  
5. Bind series to y-axes  
6. Extract and preview the overlay  
7. Add exclusion rectangles if needed  
8. Export CSV  

## Output files

Single-image mode writes the requested CSV.

DOCX batch mode writes under the output directory:

- `pic_001.csv`, `pic_001_overlay.png`, `pic_001_side_by_side.png`, `pic_001_color_fit.png`, `pic_001_metrics.csv`
- `batch_summary.csv` / `batch_summary.txt`

CSV is wide-format (`x,frequency_Hz,power_MW,...`); missing values are blank.

## Testing

```bash
python -m pip install -e ".[dev]"
python -m pytest -q
python -m compileall curve_extractor tests
```

## Project layout

```text
curve_extractor/
  app/       PySide6 GUI
  core/      calibration, OCR, color detection, extraction, DOCX batch
  cli.py     command-line entry point
examples/    sample plots (synthetic)
docs/images/ README figures
tests/
```

Package name on PyPI-style metadata: `curve-extractor` (see `pyproject.toml`). Entry points: `curve-extractor` (GUI), `curve-extractor-cli` (CLI).

## Privacy

This repository does not include private input images, DOCX reports, generated extraction outputs, local OCR binaries, or local dependency mirrors. Keep project-specific documents and results outside version control.

## Limitations

- Linear axes only
- Best on white-background engineering plots
- OCR quality depends on resolution and the installed Tesseract model
- Automatic R/G/B binding is heuristic — always review comparison images

## License

MIT
