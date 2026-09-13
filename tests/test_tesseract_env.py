from curve_extractor.cli import main
from curve_extractor.core.auto_calibration import first_run_tesseract_banner


def test_banner_hidden_when_tesseract_is_resolved(monkeypatch):
    monkeypatch.setattr(
        "curve_extractor.core.auto_calibration.resolve_tesseract_command",
        lambda: r"C:\Program Files\Tesseract-OCR\tesseract.exe",
    )
    assert first_run_tesseract_banner() is None


def test_banner_mentions_path_and_tesseract_cmd_when_missing(monkeypatch):
    monkeypatch.setattr(
        "curve_extractor.core.auto_calibration.resolve_tesseract_command",
        lambda: None,
    )
    text = first_run_tesseract_banner()
    assert text is not None
    assert "PATH" in text
    assert "TESSERACT_CMD" in text
    assert "Tesseract" in text
    assert "OCR" in text


def test_cli_help_still_available():
    try:
        main(["-h"])
    except SystemExit as exc:
        assert exc.code == 0
    else:
        raise AssertionError("CLI -h should exit")
