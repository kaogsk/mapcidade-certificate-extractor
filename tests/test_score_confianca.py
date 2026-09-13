import pytest
from src.scoreConfianca import score_image_type


def test_qrcode_classifica_correto():
    bbox = {"x": 10, "y": 50, "width": 25, "height": 25}
    result = score_image_type(bbox)
    assert result["type"] == "qrcode"
    assert result["confidence"] >= 0.85


def test_logo_y_36_pct_nao_vira_image():
    # Regression: y=107mm = 36% of 297mm
    # Old code returned "image" because 36% > 35% threshold
    bbox = {"x": 5, "y": 107, "width": 30, "height": 25}
    result = score_image_type(bbox)
    assert result["type"] == "logo"


def test_map_grande_retangular_meio():
    bbox = {"x": 20, "y": 120, "width": 160, "height": 80}
    result = score_image_type(bbox)
    assert result["type"] == "map"
    assert result["confidence"] >= 0.80


def test_header_largo_topo():
    bbox = {"x": 0, "y": 30, "width": 170, "height": 15}
    result = score_image_type(bbox)
    assert result["type"] == "header"


def test_footer_inferior():
    bbox = {"x": 10, "y": 270, "width": 100, "height": 15}
    result = score_image_type(bbox)
    assert result["type"] == "footer"


def test_line_fina_larga():
    bbox = {"x": 0, "y": 100, "width": 150, "height": 2}
    result = score_image_type(bbox)
    assert result["type"] == "line"


def test_ambiguo_retorna_flag():
    bbox = {"x": 80, "y": 150, "width": 20, "height": 20}
    result = score_image_type(bbox)
    if result["confidence"] < 0.65:
        assert "ambiguous_class" in result["flags"]


def test_retorna_scores_dict():
    bbox = {"x": 10, "y": 50, "width": 25, "height": 25}
    result = score_image_type(bbox)
    assert "scores" in result
    assert set(result["scores"].keys()) == {"qrcode", "logo", "map", "header", "footer", "line", "image"}


def test_confidence_proporcional_a_margem():
    bbox_qr = {"x": 10, "y": 50, "width": 25, "height": 25}
    result_qr = score_image_type(bbox_qr)
    bbox_ambig = {"x": 80, "y": 150, "width": 20, "height": 20}
    result_ambig = score_image_type(bbox_ambig)
    assert result_qr["confidence"] >= result_ambig["confidence"]
