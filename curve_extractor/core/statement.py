from __future__ import annotations

from dataclasses import dataclass
import re
from typing import Iterable

import numpy as np

from curve_extractor.core.extraction import ExtractionResult


_MEASUREMENT_RE = re.compile(r"([-+]?(?:\d+(?:\.\d*)?|\.\d+))\s*(Hz|MW|%|％)", re.IGNORECASE)
_NUMBER_RE = re.compile(r"[-+]?(?:\d+(?:\.\d*)?|\.\d+)")
_FREQUENCY_KEYWORDS = ("\u9891\u7387", "\u9891\u5dee")
_POWER_KEYWORDS = ("\u529f\u7387", "\u6709\u529f")
_NEEDLE_KEYWORDS = ("\u55b7\u9488", "\u5f00\u5ea6")


@dataclass(frozen=True)
class StatementMeasurement:
    value: float
    unit: str
    raw: str


@dataclass(frozen=True)
class StatementHints:
    text: str
    measurements: list[StatementMeasurement]
    table_numeric_values: list[StatementMeasurement]
    has_frequency_hint: bool
    has_power_hint: bool
    has_needle_hint: bool
    has_table_image_hint: bool
    assistance_note: str

    def values_by_unit(self, unit: str) -> list[StatementMeasurement]:
        normalized = _normalize_unit(unit)
        return [measurement for measurement in self.measurements if measurement.unit == normalized]


def parse_statement_hints(text: str | None) -> StatementHints:
    statement = (text or "").strip()
    if not statement:
        return StatementHints(
            text="",
            measurements=[],
            table_numeric_values=[],
            has_frequency_hint=False,
            has_power_hint=False,
            has_needle_hint=False,
            has_table_image_hint=False,
            assistance_note="no statement assistance",
        )

    has_table_image = "[table image" in statement.lower() and "ocr]" in statement.lower()
    measurements = [
        StatementMeasurement(value=float(match.group(1)), unit=_normalize_unit(match.group(2)), raw=match.group(0))
        for match in _MEASUREMENT_RE.finditer(statement)
    ]
    table_text_for_numbers = _table_numeric_source_text(statement)
    table_numeric_values = [
        StatementMeasurement(value=float(match.group(0)), unit="", raw=match.group(0))
        for match in _NUMBER_RE.finditer(table_text_for_numbers)
    ] if has_table_image else []
    has_frequency = _contains_any(statement, _FREQUENCY_KEYWORDS) or any(item.unit == "Hz" for item in measurements)
    has_power = _contains_any(statement, _POWER_KEYWORDS) or any(item.unit == "MW" for item in measurements)
    has_needle = _contains_any(statement, _NEEDLE_KEYWORDS)
    if has_table_image:
        note = "statement parsed with table image"
    elif measurements or has_frequency or has_power or has_needle:
        note = "statement parsed"
    else:
        note = "statement present without parseable hints"
    return StatementHints(
        text=statement,
        measurements=measurements,
        table_numeric_values=table_numeric_values,
        has_frequency_hint=has_frequency,
        has_power_hint=has_power,
        has_needle_hint=has_needle,
        has_table_image_hint=has_table_image,
        assistance_note=note,
    )


def validate_result_with_statement(result: ExtractionResult, hints: StatementHints) -> str:
    if hints.assistance_note == "no statement assistance":
        return hints.assistance_note
    power_refs = [measurement.value for measurement in hints.values_by_unit("MW")]
    power = result.series.get("power_MW")
    parts: list[str] = []
    if power_refs and power is not None:
        finite = power[np.isfinite(power)]
        if finite.size == 0:
            parts.append("power_MW extracted no finite values")
        else:
            lower = float(np.nanmin(finite)) - 2.0
            upper = float(np.nanmax(finite)) + 2.0
            matched = sum(1 for value in power_refs if lower <= value <= upper)
            parts.append(f"absolute MW references in extracted range {matched}/{len(power_refs)}")
    if hints.table_numeric_values:
        matched = _count_numeric_values_in_series_ranges(result, [item.value for item in hints.table_numeric_values])
        parts.append(f"table numeric references in extracted ranges {matched}/{len(hints.table_numeric_values)}")
    if parts:
        return f"{hints.assistance_note}; " + "; ".join(parts)
    return hints.assistance_note


def _normalize_unit(unit: str) -> str:
    normalized = unit.strip().replace("％", "%")
    if normalized.lower() == "hz":
        return "Hz"
    if normalized.lower() == "mw":
        return "MW"
    return normalized


def _contains_any(text: str, keywords: Iterable[str]) -> bool:
    return any(keyword in text for keyword in keywords)


def _table_numeric_source_text(statement: str) -> str:
    cell_value_blocks = re.findall(r"Table cell values:\s*(.*?)(?=\[table image|\Z)", statement, flags=re.IGNORECASE | re.DOTALL)
    if cell_value_blocks:
        return " ".join(cell_value_blocks)
    return re.sub(r"\[table image[^\]]+\]", " ", statement, flags=re.IGNORECASE)


def _count_numeric_values_in_series_ranges(result: ExtractionResult, values: list[float]) -> int:
    ranges: list[tuple[float, float]] = []
    for series_values in result.series.values():
        finite = series_values[np.isfinite(series_values)]
        if finite.size:
            ranges.append((float(np.nanmin(finite)) - 2.0, float(np.nanmax(finite)) + 2.0))
    return sum(1 for value in values if any(lower <= value <= upper for lower, upper in ranges))
