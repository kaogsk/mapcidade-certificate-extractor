#!/usr/bin/env python3
"""
Gera um PDF e um DOCX sinteticos ("fixtures") para exercitar o pipeline de
extracao de ponta a ponta, sem usar nenhum dado real de cliente.

Uso:
    python scripts/generate_fixtures.py

Gera:
    fixtures/sample_certificate.pdf
    fixtures/sample_certificate.docx
"""
import io
from pathlib import Path

import fitz  # PyMuPDF
from PIL import Image, ImageDraw
from docx import Document
from docx.shared import Pt, Mm
from docx.oxml.ns import qn
from docx.oxml import OxmlElement

FIXTURES_DIR = Path(__file__).resolve().parent.parent / "fixtures"

PT_PER_MM = 72.0 / 25.4


def mm_to_pt(v: float) -> float:
    return v * PT_PER_MM


def _make_png_bytes(width_px: int, height_px: int, color: str, shape: str = "rect") -> bytes:
    """Gera uma imagem PNG sintetica simples em memoria (sem asset externo)."""
    img = Image.new("RGB", (width_px, height_px), "white")
    draw = ImageDraw.Draw(img)
    if shape == "rect":
        draw.rectangle([2, 2, width_px - 3, height_px - 3], fill=color, outline="black")
    elif shape == "qr":
        # padrao xadrez grosseiro para simular um QR code
        cell = max(width_px // 6, 1)
        for i in range(6):
            for j in range(6):
                if (i + j) % 2 == 0:
                    draw.rectangle(
                        [i * cell, j * cell, (i + 1) * cell, (j + 1) * cell], fill="black"
                    )
    buf = io.BytesIO()
    img.save(buf, format="PNG")
    return buf.getvalue()


def build_pdf(out_path: Path) -> None:
    doc = fitz.open()

    # ---- Pagina 1: cabecalho, corpo de texto e um "logo" ----
    page = doc.new_page(width=595, height=842)  # A4 em pontos (72dpi)

    # Logo fictício no topo (pequeno, canto superior esquerdo)
    logo_bytes = _make_png_bytes(160, 90, "steelblue", shape="rect")
    logo_rect = fitz.Rect(mm_to_pt(12), mm_to_pt(10), mm_to_pt(12 + 30), mm_to_pt(10 + 17))
    page.insert_image(logo_rect, stream=logo_bytes)

    # Cabecalho (texto largo no topo)
    page.insert_text(
        fitz.Point(mm_to_pt(50), mm_to_pt(18)),
        "PREFEITURA MUNICIPAL DE RIVERMEADOW",
        fontsize=14,
        fontname="helv",
    )

    # Titulo do documento
    page.insert_text(
        fitz.Point(mm_to_pt(12), mm_to_pt(40)),
        "CERTIDAO DE USO E OCUPACAO DO SOLO",
        fontsize=16,
        fontname="helv",
    )

    # Corpo: paragrafo de identificacao (dados fictícios)
    body_lines = [
        "Endereco: RUA DAS ACACIAS, 123 - BAIRRO JARDIM DAS FLORES",
        "Inscricao Municipal: 00000-00-00-0000-00-000",
        "CTM: 00000-00-00-0000",
        "Coordenadas: X: 500000.00m; Y: 7500000.00m; EPSG: 31983",
        "Zona: ZR-2 (Zona Residencial 2)",
        "Coeficiente de Aproveitamento Basico: 1,0 | Maximo: 4,0",
        "Taxa de Ocupacao: 70% | Taxa de Permeabilidade: 15%",
    ]
    y = 60
    for line in body_lines:
        page.insert_text(fitz.Point(mm_to_pt(12), mm_to_pt(y)), line, fontsize=10, fontname="helv")
        y += 7

    # Mapa fictício (imagem grande, retangular, no meio da pagina)
    map_bytes = _make_png_bytes(500, 220, "darkseagreen", shape="rect")
    map_rect = fitz.Rect(mm_to_pt(20), mm_to_pt(140), mm_to_pt(20 + 160), mm_to_pt(140 + 70))
    page.insert_image(map_rect, stream=map_bytes)

    # QR code fictício no rodape
    qr_bytes = _make_png_bytes(120, 120, "black", shape="qr")
    qr_rect = fitz.Rect(mm_to_pt(175), mm_to_pt(33), mm_to_pt(175 + 18), mm_to_pt(33 + 18))
    page.insert_image(qr_rect, stream=qr_bytes)

    # Comentario/anotacao de revisao (highlight com texto)
    highlight_rect = fitz.Rect(
        mm_to_pt(12), mm_to_pt(58), mm_to_pt(12 + 90), mm_to_pt(58 + 5)
    )
    annot = page.add_highlight_annot(highlight_rect)
    annot.set_info(content="Confirmar zoneamento com a equipe tecnica antes de emitir.")
    annot.update()

    # ---- Pagina 2: rodape e texto adicional ----
    page2 = doc.new_page(width=595, height=842)
    page2.insert_text(
        fitz.Point(mm_to_pt(12), mm_to_pt(30)),
        "ATIVIDADES PERMITIDAS NA ZONA ZR-2",
        fontsize=14,
        fontname="helv",
    )
    activities = [
        "CNAE 4618-4/03 - Comercio varejista - Categoria Cm-1 - Permitido",
        "CNAE 0000-0/00 - Uso residencial unifamiliar - Categoria R1 - Permitido",
    ]
    y = 45
    for line in activities:
        page2.insert_text(fitz.Point(mm_to_pt(12), mm_to_pt(y)), line, fontsize=10, fontname="helv")
        y += 7

    # Rodape largo na parte inferior
    page2.insert_text(
        fitz.Point(mm_to_pt(12), mm_to_pt(285)),
        "Documento gerado para fins de demonstracao - sem validade juridica",
        fontsize=8,
        fontname="helv",
    )

    FIXTURES_DIR.mkdir(parents=True, exist_ok=True)
    doc.save(str(out_path))
    doc.close()
    print(f"[OK] PDF sintetico gerado: {out_path}")


def _set_vmerge(cell, val):
    """Define w:vMerge na celula: 'restart' inicia rowspan, '' continua."""
    tc = cell._tc
    tcPr = tc.get_or_add_tcPr()
    vmerge = OxmlElement("w:vMerge")
    if val is not None:
        vmerge.set(qn("w:val"), val)
    tcPr.append(vmerge)


def build_docx(out_path: Path) -> None:
    doc = Document()

    # Cabecalho/rodape simples
    section = doc.sections[0]
    header = section.header
    header.paragraphs[0].text = "Prefeitura Municipal de Rivermeadow"
    footer = section.footer
    footer.paragraphs[0].text = "Documento sintetico de teste - mapcidade-certificate-extractor"

    # Titulo com runs de formatacao mista
    p = doc.add_paragraph()
    run_bold = p.add_run("CERTIDAO DE USO E OCUPACAO DO SOLO")
    run_bold.bold = True
    run_bold.font.size = Pt(14)
    run_bold.font.name = "Calibri"

    doc.add_paragraph(
        "Endereco: Rua das Acacias, 123 - Bairro Jardim das Flores. "
        "Inscricao Municipal: 00000-00-00-0000-00-000."
    )

    # Tabela com rowspan (vMerge) para exercitar extrairTabelas
    table = doc.add_table(rows=4, cols=3)
    table.style = "Table Grid"

    # Cabecalho
    hdr_cells = table.rows[0].cells
    hdr_cells[0].text = "Parametro"
    hdr_cells[1].text = "Zona"
    hdr_cells[2].text = "Valor"

    # Linha 1-2: rowspan na coluna 0 ("Coeficiente de Aproveitamento")
    r1 = table.rows[1].cells
    r1[0].text = "Coeficiente de Aproveitamento"
    r1[1].text = "ZR-2"
    r1[2].text = "1,0 (basico)"

    r2 = table.rows[2].cells
    r2[1].text = "ZR-2"
    r2[2].text = "4,0 (maximo)"

    # Aplica vMerge: r1[0] inicia, r2[0] continua (mesmo texto de celula)
    r2_cells = table.rows[2].cells
    _set_vmerge(r1[0], "restart")
    _set_vmerge(r2_cells[0], None)  # placeholder, sera sobrescrito abaixo
    # Remover o vMerge vazio criado acima e usar o valor correto ("")
    tc = r2_cells[0]._tc
    tcPr = tc.get_or_add_tcPr()
    for el in tcPr.findall(qn("w:vMerge")):
        tcPr.remove(el)
    vmerge_continue = OxmlElement("w:vMerge")
    tcPr.append(vmerge_continue)  # sem w:val => "continue"

    r3 = table.rows[3].cells
    r3[0].text = "Taxa de Ocupacao"
    r3[1].text = "ZR-2"
    r3[2].text = "70%"

    doc.add_paragraph()
    p2 = doc.add_paragraph()
    run_plain = p2.add_run("Area do lote: ")
    run_plain.font.size = Pt(10)
    run_bold2 = p2.add_run("250m²")
    run_bold2.bold = True
    run_bold2.font.size = Pt(10)

    FIXTURES_DIR.mkdir(parents=True, exist_ok=True)
    doc.save(str(out_path))
    print(f"[OK] DOCX sintetico gerado: {out_path}")


def main():
    build_pdf(FIXTURES_DIR / "sample_certificate.pdf")
    build_docx(FIXTURES_DIR / "sample_certificate.docx")


if __name__ == "__main__":
    main()
