import pytest
from unittest.mock import MagicMock
from src.extrairFontes import _get_run_info, _get_paragraph_style_with_runs


def _make_run(text, bold=False, italic=False, font_name="Calibri", font_size_pt=None):
    run = MagicMock()
    run.text = text
    run.font = MagicMock()
    run.font.bold = bold
    run.font.italic = italic
    run.font.name = font_name
    run.font.size = MagicMock()
    run.font.size.pt = font_size_pt
    return run


def test_get_run_info_basico():
    run = _make_run("texto simples", bold=False, italic=False, font_name="Arial", font_size_pt=10.0)
    result = _get_run_info(run)
    assert result["text"] == "texto simples"
    assert result["bold"] is False
    assert result["italic"] is False
    assert result["font_name"] == "Arial"


def test_get_run_info_negrito():
    run = _make_run("TÍTULO", bold=True, font_name="Calibri", font_size_pt=12.0)
    result = _get_run_info(run)
    assert result["bold"] is True
    assert result["font_name"] == "Calibri"


def test_get_paragraph_style_with_runs_captura_runs():
    para = MagicMock()
    run1 = _make_run("Área do lote: ", bold=False, font_name="Calibri", font_size_pt=10.0)
    run2 = _make_run("250m²", bold=True, font_name="Calibri", font_size_pt=10.0)
    para.runs = [run1, run2]
    para.text = "Área do lote: 250m²"
    para.style = MagicMock()
    para.style.font = MagicMock()
    para.style.font.size = None

    result = _get_paragraph_style_with_runs(para)
    assert "runs" in result
    assert len(result["runs"]) == 2
    assert result["runs"][0]["bold"] is False
    assert result["runs"][1]["bold"] is True


def test_get_paragraph_style_with_runs_sem_runs():
    para = MagicMock()
    para.runs = []
    para.text = ""
    para.style = MagicMock()
    para.style.font = MagicMock()
    para.style.font.size = MagicMock()
    para.style.font.size.pt = 11.0

    result = _get_paragraph_style_with_runs(para)
    assert result["runs"] == []
    assert result["font_size_pt"] == 11.0
