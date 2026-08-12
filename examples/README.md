# Examples

## `sample_rgb_plot.png`

Synthetic white-background engineering plot with red / green / blue curves on linear axes. Safe to commit; no project data.

### Try it

```bash
python -m pip install -e .
# optional: install Tesseract and ensure it is on PATH
python -m curve_extractor.cli examples/sample_rgb_plot.png --output /tmp/extracted.csv
```

`sample_rgb_plot.expected.csv` is an analytical reference for the three series (not bit-identical to OCR-based extraction). Always review the tool’s overlay / side-by-side outputs for real runs.
