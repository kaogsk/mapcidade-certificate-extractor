import pytest
from src.mergerTexto import should_merge_blocks, merge_text_items


def _item(text, x, y_bottom, width, height, font_name="Arial", font_size=12.0, page=1):
    return {
        "type": "text",
        "page": page,
        "text": text,
        "bounding_box_mm": {"x": x, "y": y_bottom, "width": width, "height": height},
        "_y0_mm": y_bottom - height,
        "font": {"name": font_name, "size_pt": font_size},
        "confidence": 0.95,
        "confidence_flags": [],
    }


def test_merge_mesma_linha_mesma_fonte():
    a = _item("PREFEITURA", x=20, y_bottom=15, width=30, height=5)
    b = _item("MUNICIPAL",  x=53, y_bottom=15, width=25, height=5)
    assert should_merge_blocks(a, b) is True


def test_nao_merge_fonte_diferente():
    a = _item("Título",    x=20, y_bottom=15, width=20, height=5, font_name="Arial")
    b = _item("subtítulo", x=43, y_bottom=15, width=20, height=5, font_name="Calibri")
    assert should_merge_blocks(a, b) is False


def test_nao_merge_paginas_diferentes():
    a = _item("texto A", x=20, y_bottom=15, width=30, height=5, page=1)
    b = _item("texto B", x=53, y_bottom=15, width=25, height=5, page=2)
    assert should_merge_blocks(a, b) is False


def test_nao_merge_gap_x_grande():
    a = _item("texto A", x=20, y_bottom=15, width=30, height=5)
    b = _item("texto B", x=65, y_bottom=15, width=25, height=5)  # gap = 65-(20+30) = 15mm > 8mm
    assert should_merge_blocks(a, b) is False


def test_nao_merge_gap_y_grande():
    a = _item("linha 1", x=20, y_bottom=15, width=80, height=5)
    b = _item("linha 2", x=20, y_bottom=25, width=80, height=5)  # gap y = 25-15 = 10mm > 2mm
    assert should_merge_blocks(a, b) is False


def test_merge_tamanho_fonte_dentro_tolerancia():
    a = _item("A", x=20, y_bottom=15, width=10, height=5, font_size=12.0)
    b = _item("B", x=33, y_bottom=15, width=10, height=5, font_size=12.4)  # diff = 0.4 < 0.5
    assert should_merge_blocks(a, b) is True


def test_merge_items_combina_texto():
    items = [
        _item("PREFEITURA", x=20, y_bottom=15, width=30, height=5),
        _item("MUNICIPAL",  x=53, y_bottom=15, width=25, height=5),
    ]
    plumber_words = [
        {"text": "PREFEITURA", "x0": 20, "y0": 10, "x1": 50, "y1": 15, "page": 1},
        {"text": "MUNICIPAL",  "x0": 53, "y0": 10, "x1": 78, "y1": 15, "page": 1},
    ]
    result = merge_text_items(items, plumber_words)
    assert len(result) == 1
    assert "PREFEITURA" in result[0]["text"]
    assert "MUNICIPAL" in result[0]["text"]
    assert result[0]["confidence"] >= 0.85


def test_sem_merge_quando_nao_deve():
    items = [
        _item("Título",    x=20, y_bottom=15, width=20, height=5, font_name="Arial", font_size=14.0),
        _item("parágrafo", x=20, y_bottom=35, width=80, height=5, font_name="Calibri", font_size=10.0),
    ]
    result = merge_text_items(items, [])
    assert len(result) == 2


def test_split_conflict_baixa_confianca():
    items = [
        {
            "type": "text", "page": 1,
            "text": "A B",
            "bounding_box_mm": {"x": 20, "y": 15, "width": 15, "height": 5},
            "_y0_mm": 10.0,
            "font": {"name": "Arial", "size_pt": 10.0},
            "confidence": 0.95,
            "confidence_flags": [],
        }
    ]
    plumber_words = [
        {"text": "A", "x0": 20, "y0": 10, "x1": 25, "y1": 15, "page": 1},
        {"text": "B", "x0": 28, "y0": 10, "x1": 35, "y1": 15, "page": 1},
    ]
    result = merge_text_items(items, plumber_words)
    assert len(result) == 1
    assert result[0]["confidence"] <= 0.75 or "split_conflict" in result[0]["confidence_flags"]


def test_merge_expande_bounding_box():
    items = [
        _item("PREFEITURA", x=20, y_bottom=15, width=30, height=5),
        _item("MUNICIPAL",  x=53, y_bottom=15, width=25, height=5),
    ]
    result = merge_text_items(items, [])
    bb = result[0]["bounding_box_mm"]
    assert bb["x"] == 20
    assert bb["width"] >= 58  # 53 + 25 - 20
