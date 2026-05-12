from __future__ import annotations

from pathlib import Path

import pandas as pd

from curve_extractor.core.extraction import ExtractionResult


def export_csv(result: ExtractionResult, output_path: str | Path) -> Path:
    path = Path(output_path)
    data = {"x": result.x}
    data.update(result.series)
    dataframe = pd.DataFrame(data)
    dataframe.to_csv(path, index=False, encoding="utf-8-sig")
    return path
