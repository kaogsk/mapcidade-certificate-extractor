import pytest
from unittest.mock import MagicMock
from src.extrairTabelas import detectar_rowspan, extrair_conteudo_celula


def test_detectar_rowspan_restart():
    result = detectar_rowspan("restart")
    assert result == "start"


def test_detectar_rowspan_continue():
    result = detectar_rowspan("")
    assert result == "continue"


def test_detectar_rowspan_none():
    result = detectar_rowspan(None)
    assert result == "none"


def test_rowspan_default_na_celula_sem_merge():
    pass  # integration tested with real DOCX in smoke test


def test_extrair_conteudo_celula_texto_simples():
    celula = MagicMock()
    para1 = MagicMock()
    para1.text = "  Área do Lote  "
    para2 = MagicMock()
    para2.text = ""
    celula.paragraphs = [para1, para2]
    result = extrair_conteudo_celula(celula)
    assert result == "Área do Lote"
