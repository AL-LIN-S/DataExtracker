from __future__ import annotations

from curve_extractor.core.statement import parse_statement_hints


def test_parse_statement_hints_extracts_unit_values_and_keywords():
    text = (
        "\u5728\u989d\u5b9a\u9891\u738750Hz \u57fa\u7840\u4e0a\u65bd\u52a00.1Hz "
        "\u9636\u8dc3\u9891\u7387\u504f\u5dee\u4fe1\u53f7\uff0c"
        "\u6709\u529f\u529f\u7387\u4ece91.29MW \u964d\u81f387.44MW\uff0c"
        "\u55b7\u9488\u5f00\u5ea6\u53d8\u5316\u3002"
    )

    hints = parse_statement_hints(text)

    assert [value.value for value in hints.values_by_unit("Hz")] == [50.0, 0.1]
    assert [value.value for value in hints.values_by_unit("MW")] == [91.29, 87.44]
    assert hints.has_frequency_hint
    assert hints.has_power_hint
    assert hints.has_needle_hint
    assert hints.assistance_note == "statement parsed"


def test_parse_statement_hints_allows_missing_statement():
    hints = parse_statement_hints("")

    assert hints.measurements == []
    assert not hints.has_frequency_hint
    assert not hints.has_power_hint
    assert not hints.has_needle_hint
    assert hints.assistance_note == "no statement assistance"


def test_parse_statement_hints_uses_table_image_numeric_references():
    text = "[table image word/media/image7.png OCR]\n0.25 119.62 108.19 -11.43 70.05 64.54 -5.51"

    hints = parse_statement_hints(text)

    assert hints.has_table_image_hint
    assert [value.value for value in hints.table_numeric_values[:3]] == [0.25, 119.62, 108.19]
    assert hints.assistance_note == "statement parsed with table image"


def test_parse_statement_hints_prefers_clean_table_cell_values_over_noisy_ocr():
    text = "[table image word/media/image7.png OCR]\nnoisy OCR 999 888\nTable cell values: 0.25 119.62 108.19"

    hints = parse_statement_hints(text)

    assert [value.value for value in hints.table_numeric_values] == [0.25, 119.62, 108.19]
