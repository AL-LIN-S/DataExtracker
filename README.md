# Curve Extractor

Curve Extractor is a local Python tool for extracting numeric data from colored engineering plots. It supports both an interactive desktop workflow and a command-line workflow for single images or DOCX files that contain multiple plot images.

The project is designed for white-background plots with colored red, green, and blue curves, black or gray grid lines, linear axes, and optional text statements or table images that can be used as validation hints.

## Features

- Detects the plot area and axis tick labels with OCR.
- Finds saturated colored curve candidates inside the plot area.
- Extracts one value per x-pixel column and exports a wide CSV table.
- Supports multiple y-axes and automatic red, green, and blue series binding.
- Generates review artifacts for each extraction:
  - overlay image
  - side-by-side redrawn comparison
  - color-fit check image
  - per-series fit metrics
- Reads DOCX files organized as `Pic n` and `Statement n`.
- Treats table images inside a DOCX as statement/validation input instead of curve plots.
- Provides a PySide6 desktop GUI for manual calibration and review.

## Installation

Python 3.10 or newer is required.

```powershell
python -m venv .venv
.\.venv\Scripts\Activate.ps1
python -m pip install -U pip
python -m pip install -r requirements-dev.txt
```

Automatic axis detection depends on the Tesseract OCR executable. Install Tesseract separately and make sure `tesseract` is available on `PATH`, or set `TESSERACT_CMD` to the executable path.

Example on Windows:

```powershell
$env:TESSERACT_CMD = "C:\Program Files\Tesseract-OCR\tesseract.exe"
```

## Command-Line Usage

Extract a single image:

```powershell
python -m curve_extractor.cli path\to\plot.png --output extracted.csv
```

If automatic color and y-axis binding is not suitable, pass explicit series bindings:

```powershell
python -m curve_extractor.cli path\to\plot.png `
  --output extracted.csv `
  --series "power:MW:0,235,0:45:right_1"
```

Batch extract from a DOCX file:

```powershell
python -m curve_extractor.cli path\to\summary.docx --output-dir outputs
```

The DOCX batch mode expects a simple structure:

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

If a `Pic` section contains more than one plot image, outputs are named with suffixes such as `pic_003_01.csv` and `pic_003_02.csv`. Table-like images are OCR-processed and appended to the statement hints for validation.

## GUI Usage

Start the desktop application:

```powershell
python -m curve_extractor
```

Typical workflow:

1. Open an image.
2. Run automatic axis detection, or manually select the plot area.
3. Review or edit x/y axis ranges.
4. Detect curve colors.
5. Bind series to y-axes.
6. Extract and preview the overlay.
7. Add exclusion rectangles if needed.
8. Export CSV.

## Output Files

Single-image mode writes the requested CSV file.

DOCX batch mode writes files under the selected output directory:

- `pic_001.csv`
- `pic_001_overlay.png`
- `pic_001_side_by_side.png`
- `pic_001_color_fit.png`
- `pic_001_metrics.csv`
- `batch_summary.csv`
- `batch_summary.txt`

CSV output uses a wide format:

```text
x,frequency_Hz,power_MW,needle_%
...
```

Missing values are left blank.

## Testing

```powershell
python -m pytest -q
python -m compileall curve_extractor tests
```

## Project Layout

```text
curve_extractor/
  app/                 PySide6 GUI
  core/                calibration, OCR, color detection, extraction, DOCX batch processing
  cli.py               command-line entry point
tests/                 unit and integration tests
```

## Privacy and Data

This repository does not include private input images, DOCX reports, generated extraction outputs, local OCR binaries, or local dependency mirrors. Keep project-specific documents and generated results outside version control.

## Limitations

- Linear axes only.
- Best suited to white-background engineering plots.
- OCR quality depends on image resolution and the installed Tesseract model.
- Automatic red/green/blue binding is heuristic and should be reviewed with the generated comparison images.
