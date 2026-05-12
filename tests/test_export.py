from pathlib import Path

import numpy as np
import pandas as pd

from curve_extractor.core.extraction import ExtractionResult
from curve_extractor.core.export import export_csv


def test_export_csv_writes_wide_table_with_blank_missing_values(tmp_path: Path):
    result = ExtractionResult(
        x=np.array([0.0, 1.0, 2.0]),
        series={"power_MW": np.array([90.0, np.nan, 92.0])},
        missing={"power_MW": np.array([False, True, False])},
        preview_paths={"power_MW": [(0, 10), (2, 8)]},
    )

    output_path = tmp_path / "extracted.csv"
    export_csv(result, output_path)

    dataframe = pd.read_csv(output_path)
    assert list(dataframe.columns) == ["x", "power_MW"]
    assert dataframe.loc[0, "power_MW"] == 90.0
    assert pd.isna(dataframe.loc[1, "power_MW"])
