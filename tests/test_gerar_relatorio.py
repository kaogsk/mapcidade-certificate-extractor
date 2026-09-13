import pytest
from src.gerarRelatorio import (
    coletar_itens_baixa_confianca,
    formatar_relatorio,
    CONFIDENCE_THRESHOLD,
)


ITEMS_MOCK = [
    {"type": "text",  "page": 1, "text": "TÍTULO OK",      "confidence": 0.95, "confidence_flags": [], "bounding_box_mm": {"x": 20, "y": 10, "width": 80, "height": 5}},
    {"type": "text",  "page": 1, "text": "ÁREA DO LOTE",   "confidence": 0.61, "confidence_flags": ["split_conflict"], "bounding_box_mm": {"x": 20, "y": 45, "width": 50, "height": 5}},
    {"type": "image", "page": 1, "element_type": "qrcode",  "confidence": 0.63, "confidence_flags": ["ambiguous_class"], "bounding_box_mm": {"x": 150, "y": 38, "width": 22, "height": 22}},
    {"type": "text",  "page": 2, "text": "Texto confiante","confidence": 0.90, "confidence_flags": [], "bounding_box_mm": {"x": 10, "y": 20, "width": 60, "height": 5}},
]


def test_threshold_valor():
    assert CONFIDENCE_THRESHOLD == 0.70


def test_coletar_filtra_abaixo_threshold():
    baixos = coletar_itens_baixa_confianca(ITEMS_MOCK)
    assert len(baixos) == 2
    for item in baixos:
        assert item["confidence"] < CONFIDENCE_THRESHOLD


def test_coletar_nenhum_item_ruim():
    items = [{"type": "text", "page": 1, "text": "OK", "confidence": 0.95, "confidence_flags": [], "bounding_box_mm": {"x": 0, "y": 0, "width": 10, "height": 5}}]
    baixos = coletar_itens_baixa_confianca(items)
    assert baixos == []


def test_formatar_relatorio_com_itens():
    baixos = coletar_itens_baixa_confianca(ITEMS_MOCK)
    md = formatar_relatorio(baixos, total_items=len(ITEMS_MOCK), source_name="certidao.pdf")
    assert "# Revisão necessária" in md
    assert "certidao.pdf" in md
    assert "ÁREA DO LOTE" in md
    assert "split_conflict" in md
    assert "qrcode" in md
    assert "ambiguous_class" in md


def test_formatar_relatorio_limpo():
    md = formatar_relatorio([], total_items=10, source_name="certidao.pdf")
    assert "Extração limpa" in md
    assert "nenhum item" in md.lower()


def test_formatar_relatorio_percentual():
    baixos = coletar_itens_baixa_confianca(ITEMS_MOCK)
    md = formatar_relatorio(baixos, total_items=len(ITEMS_MOCK), source_name="certidao.pdf")
    assert "50.0%" in md or "50%" in md
