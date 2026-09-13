import pytest
from src.extrairFormulario import parse_pdftk_fields, parse_pdftk_metadata


def test_parse_fields_vazio():
    result = parse_pdftk_fields("")
    assert result == []


def test_parse_fields_com_campo():
    output = """FieldType: Text
FieldName: inscricao
FieldValue: 12345-6
---
FieldType: Text
FieldName: proprietario
FieldValue: João Silva
---"""
    result = parse_pdftk_fields(output)
    assert len(result) == 2
    assert result[0]["name"] == "inscricao"
    assert result[0]["value"] == "12345-6"
    assert result[0]["confidence"] == 0.98
    assert result[1]["name"] == "proprietario"
    assert result[1]["value"] == "João Silva"


def test_parse_fields_campo_sem_valor():
    output = """FieldType: Text
FieldName: campo_vazio
FieldValue:
---"""
    result = parse_pdftk_fields(output)
    assert len(result) == 0


def test_parse_metadata_titulo():
    output = """InfoKey: Title
InfoValue: Certidão de Uso e Ocupação do Solo
InfoKey: Author
InfoValue: Prefeitura Municipal
InfoKey: CreationDate
InfoValue: D:20240315120000"""
    result = parse_pdftk_metadata(output)
    assert result["title"] == "Certidão de Uso e Ocupação do Solo"
    assert result["author"] == "Prefeitura Municipal"
    assert "creation_date" in result


def test_parse_metadata_vazio():
    result = parse_pdftk_metadata("")
    assert result == {}
