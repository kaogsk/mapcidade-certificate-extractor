import sys
import json
from pathlib import Path
from typing import List, Dict, Optional

sys.path.insert(0, str(Path(__file__).parent.parent))

try:
    import fitz
except ImportError:
    print(
        "Dependência ausente: PyMuPDF (pymupdf).\n"
        "Instale com: py -m pip install pymupdf"
    )
    sys.exit(1)


DPI = 400
PT_TO_MM = 25.4 / 72.0


def convert_pdf_to_pngs(pdf_path: Path, output_dir: Path) -> List[Path]:
    output_dir.mkdir(parents=True, exist_ok=True)

    doc = fitz.open(pdf_path)
    saved_paths: List[Path] = []
    try:
        scale = DPI / 72.0
        matrix = fitz.Matrix(scale, scale)

        num_pages = len(doc)
        for page_index in range(num_pages):
            page = doc.load_page(page_index)
            pix = page.get_pixmap(matrix=matrix, alpha=False, colorspace=fitz.csRGB, annots=False)
            out_path = output_dir / f"pagina{page_index + 1}.png"
            pix.save(str(out_path))
            saved_paths.append(out_path)
    finally:
        doc.close()

    return saved_paths


def extract_annotations_to_txt(pdf_path: Path, out_txt: Path) -> int:
    doc = fitz.open(pdf_path)
    count = 0
    lines: List[str] = []
    try:
        num_pages = len(doc)
        for page_index in range(num_pages):
            page = doc.load_page(page_index)

            annot = page.first_annot
            while annot is not None:
                atype = annot.type[1] if isinstance(annot.type, tuple) else str(annot.type)
                info = annot.info or {}
                comment = (info.get("content") or "").strip()
                author = (info.get("title") or "").strip()

                selected_text = ""
                if atype in ("Highlight", "Underline", "Squiggly", "StrikeOut"):
                    collected: List[str] = []
                    verts = getattr(annot, "vertices", None)
                    if verts:
                        
                        limit = (len(verts) // 8) * 8
                        for i in range(0, limit, 8):
                            chunk = verts[i : i + 8]
                            try:
                                quad = fitz.Quad(chunk)
                                rect = quad.rect
                            except Exception:
                                continue
                            t = page.get_text("text", clip=rect).strip()
                            if t:
                                collected.append(t)
                    
                    try:
                        if not collected and getattr(annot, "rect", None) is not None:
                            t = page.get_text("text", clip=annot.rect).strip()
                            if t:
                                collected.append(t)
                    except Exception:
                        pass
                    selected_text = " ".join(collected)

                line = (
                    f"[Página {page_index + 1}] {atype} | "
                    f"Selecionado: {selected_text if selected_text else '-'} | "
                    f"Comentário: {comment if comment else '-'}"
                )
                if author:
                    line += f" | Autor: {author}"
                lines.append(line)
                count += 1

                annot = annot.next
    finally:
        doc.close()

    out_txt.parent.mkdir(parents=True, exist_ok=True)
    with out_txt.open("w", encoding="utf-8") as f:
        f.write(f"Anotações extraídas de: {pdf_path}\n")
        for ln in lines:
            f.write(ln + "\n")

    return count

def pt_to_mm(v: float) -> float:
    return v * PT_TO_MM


def round4(v: float) -> float:
    return round(v, 2)


def smart_round_font_size(v: float) -> float:
    eps = 5e-4
    for d in (0, 1, 2):
        r = round(v, d)
        if abs(v - r) < eps:
            return float(r)
    return float(round(v, 2))


def mm_bbox_from_pt_bbox(bbox) -> Dict[str, float]:
    x0, y0, x1, y1 = bbox
    x_mm = round4(pt_to_mm(x0))
    width_mm = round4(pt_to_mm(x1 - x0))
    height_mm = round4(pt_to_mm(y1 - y0))
    
    y_mm = round4(pt_to_mm(y1))
    return {
        "x": x_mm,
        "y": y_mm,
        "width": width_mm,
        "height": height_mm,
    }


def classify_image_type(bbox_mm: Dict[str, float], page: int) -> str:
    """
    Classifica o tipo de imagem baseado em tamanho e proporções.
    Retorna: 'qrcode', 'map', 'header', 'footer', 'line', 'logo' ou 'image'
    
    Heurísticas genéricas que se adaptam a diferentes layouts.
    """
    x = bbox_mm["x"]
    y = bbox_mm["y"]
    width = bbox_mm["width"]
    height = bbox_mm["height"]
    
    aspect_ratio = width / height if height > 0 else 0
    area = width * height
    
    # Página A4: 210mm x 297mm
    PAGE_WIDTH = 210
    PAGE_HEIGHT = 297
    
    # Linha decorativa: muito fina e larga (altura < 5mm, largura > 50% da página)
    if height < 5 and width > PAGE_WIDTH * 0.5:
        return "line"
    
    # QR Code: pequeno (15-35mm), aproximadamente quadrado (ratio 0.7-1.4)
    # Independente de posição
    if (15 < width < 35 and 15 < height < 35 and 0.7 < aspect_ratio < 1.4):
        return "qrcode"
    
    # Map/Mapa: grande (área > 4000mm²), retangular (ratio 1.5-4.0)
    # Normalmente no meio vertical da página (y entre 20% e 80% da altura)
    is_large = area > 4000
    is_rectangular = 1.5 < aspect_ratio < 4.0
    is_middle_vertical = (PAGE_HEIGHT * 0.2) < y < (PAGE_HEIGHT * 0.8)
    
    if is_large and is_rectangular and is_middle_vertical:
        return "map"
    
    # Cabeçalho: largo (> 60% da largura), relativamente fino, no topo (y < 20% da altura)
    if width > PAGE_WIDTH * 0.6 and y < PAGE_HEIGHT * 0.2 and height < 50:
        return "header"
    
    # Rodapé: largo (> 30% da largura), na parte inferior (y > 85% da altura)
    if width > PAGE_WIDTH * 0.3 and y > PAGE_HEIGHT * 0.85:
        return "footer"
    
    # Logo: pequeno/médio (área < 1500mm²), no topo da página (y < 35% da altura)
    if area < 1500 and y < PAGE_HEIGHT * 0.35:
        return "logo"
    
    # Caso padrão
    return "image"


WEIGHT_KEYWORDS = [
    ("Thin", "thin"),
    ("Hairline", "thin"),
    ("ExtraLight", "extralight"),
    ("UltraLight", "extralight"),
    ("Light", "light"),
    ("Book", "book"),
    ("Regular", "regular"),
    ("Normal", "regular"),
    ("Medium", "medium"),
    ("DemiBold", "semibold"),
    ("SemiBold", "semibold"),
    ("Bold", "bold"),
    ("ExtraBold", "extrabold"),
    ("UltraBold", "extrabold"),
    ("Black", "black"),
    ("Heavy", "heavy"),
]


def infer_weight_from_font_name(font_name: Optional[str]) -> Optional[str]:
    if not font_name:
        return None
    for key, value in WEIGHT_KEYWORDS:
        if key.lower() in font_name.lower():
            return value
    return None


def _aggregate_block(block: dict, page_num: int) -> Optional[Dict]:
    """Agrega todos os spans de um bloco pymupdf em um único item de texto."""
    lines = block.get("lines", [])
    all_spans = []
    lines_texts = []

    for line in lines:
        spans = line.get("spans", [])
        line_text = "".join(s.get("text", "") for s in spans).strip()
        if line_text:
            lines_texts.append(line_text)
        all_spans.extend(spans)

    all_spans = [s for s in all_spans if s.get("text", "").strip()]
    if not all_spans:
        return None

    merged_text = "\n".join(lines_texts)
    if not merged_text.strip():
        return None

    all_bboxes = [s["bbox"] for s in all_spans if s.get("bbox")]
    if not all_bboxes:
        return None
    x0 = min(b[0] for b in all_bboxes)
    y0 = min(b[1] for b in all_bboxes)
    x1 = max(b[2] for b in all_bboxes)
    y1 = max(b[3] for b in all_bboxes)

    dominant = max(all_spans, key=lambda s: len(s.get("text", "")))
    font_name = dominant.get("font")
    font_size = dominant.get("size")

    font_obj: Dict[str, object] = {}
    if font_name:
        font_obj["name"] = font_name
    if font_size:
        font_obj["size_pt"] = smart_round_font_size(float(font_size))
    weight = infer_weight_from_font_name(font_name)
    if weight:
        font_obj["weight"] = weight

    n_spans = len(all_spans)
    flags = [f"block_merged_{n_spans}_spans"] if n_spans > 1 else []

    return {
        "type": "text",
        "page": page_num,
        "text": merged_text,
        "bounding_box_mm": mm_bbox_from_pt_bbox((x0, y0, x1, y1)),
        "_y0_mm": round4(pt_to_mm(y0)),
        "font": font_obj,
        "confidence": 0.95,
        "confidence_flags": flags,
    }


def _extract_pdfplumber_words(pdf_path: Path) -> Dict[int, List[Dict]]:
    """Extrai palavras via pdfplumber por página (em mm). Retorna {} se pdfplumber indisponível."""
    try:
        import pdfplumber
    except ImportError:
        return {}
    result: Dict[int, List[Dict]] = {}
    try:
        with pdfplumber.open(str(pdf_path)) as pdf:
            for i, page in enumerate(pdf.pages):
                words = page.extract_words(keep_blank_chars=True) or []
                result[i + 1] = [
                    {
                        "text": w["text"],
                        "x0": round(float(w["x0"]) * PT_TO_MM, 2),
                        "y0": round(float(w["top"]) * PT_TO_MM, 2),
                        "x1": round(float(w["x1"]) * PT_TO_MM, 2),
                        "y1": round(float(w["bottom"]) * PT_TO_MM, 2),
                        "page": i + 1,
                    }
                    for w in words
                ]
    except Exception:
        return {}
    return result


def extract_pdf_layout(pdf_path: Path) -> Dict:
    """
    Extrai layout do PDF agrupando por bloco (não por span).
    Cada bloco pymupdf vira um único item de texto — evita fragmentação por linha.
    Chama mergerTexto para validação cruzada com pdfplumber e mesclagem de blocos próximos.
    """
    from src.mergerTexto import merge_text_items
    from src.scoreConfianca import score_image_type

    doc = fitz.open(pdf_path)
    raw_items = []

    for page_index in range(len(doc)):
        page = doc[page_index]
        page_dict = page.get_text("dict")

        for block in page_dict.get("blocks", []):
            btype = block.get("type", 0)
            if btype == 0:
                item = _aggregate_block(block, page_index + 1)
                if item:
                    raw_items.append(item)
            elif btype == 1:
                bbox = block.get("bbox")
                if not bbox:
                    continue
                bbox_mm = mm_bbox_from_pt_bbox(bbox)
                scored = score_image_type(bbox_mm)
                image_item = {
                    "type": "image",
                    "page": page_index + 1,
                    "bounding_box_mm": bbox_mm,
                    "element_type": scored["type"],
                    "confidence": scored["confidence"],
                    "confidence_flags": scored["flags"],
                }
                w = block.get("width")
                h = block.get("height")
                if isinstance(w, (int, float)) and isinstance(h, (int, float)):
                    image_item["pixel_size"] = {"width_px": int(w), "height_px": int(h)}
                raw_items.append(image_item)

    doc.close()

    text_items = [i for i in raw_items if i["type"] == "text"]
    image_items = [i for i in raw_items if i["type"] != "text"]

    plumber_words_by_page = _extract_pdfplumber_words(pdf_path)
    all_plumber_words = [w for words in plumber_words_by_page.values() for w in words]

    merged_text = merge_text_items(text_items, all_plumber_words)

    for item in merged_text:
        item.pop("_y0_mm", None)

    all_items = merged_text + image_items
    all_items.sort(key=lambda i: (i["page"], i["bounding_box_mm"]["y"], i["bounding_box_mm"]["x"]))

    return {"unit": "mm", "font_size_unit": "pt", "items": all_items}


def main() -> None:
    base_dir = Path(__file__).parent.parent
    pdf_path = base_dir / "fixtures" / "sample_certificate.pdf"

    if not pdf_path.exists():
        print(f"Arquivo PDF não encontrado: {pdf_path}")
        sys.exit(1)

    output_dir = base_dir / "target"

    try:
        print(f"Convertendo '{pdf_path}' para PNGs...")
        saved = convert_pdf_to_pngs(pdf_path, output_dir)
        if saved:
            print(f"Conversão concluída: {len(saved)} página(s) salva(s) em '{output_dir}'.")
        else:
            print("Nenhuma imagem gerada")

        print(f"Extraindo layout e texto estruturado...")
        layout_data = extract_pdf_layout(pdf_path)
        json_path = output_dir / "certidao_extracted.json"
        with json_path.open("w", encoding="utf-8") as f:
            json.dump(layout_data["items"], f, ensure_ascii=False, indent=2)
        print(f"Layout extraído: {len(layout_data['items'])} item(s) salvo(s) em '{json_path}'.")

        print("\nProcessamento concluído. Arquivos gerados em 'target/'")
    except Exception as exc:
        print(f"Erro durante o processamento: {exc}")
        sys.exit(1)


if __name__ == "__main__":
    main()