import json
from datetime import datetime
from pathlib import Path
from typing import List, Dict


CONFIDENCE_THRESHOLD = 0.70


def coletar_itens_baixa_confianca(items: List[Dict]) -> List[Dict]:
    """Filtra itens com confidence abaixo do threshold."""
    return [i for i in items if i.get("confidence", 1.0) < CONFIDENCE_THRESHOLD]


def formatar_relatorio(baixos: List[Dict], total_items: int, source_name: str) -> str:
    now = datetime.now().strftime("%Y-%m-%d %H:%M")
    n = len(baixos)
    pct = (n / total_items * 100) if total_items > 0 else 0.0

    lines = [
        f"# Revisão necessária — {source_name}",
        f"Gerado: {now} | Itens: {n} de {total_items} ({pct:.1f}%)",
        "",
    ]

    if not baixos:
        lines.append("Extração limpa — nenhum item para revisão.")
        return "\n".join(lines)

    text_items = [i for i in baixos if i.get("type") == "text"]
    image_items = [i for i in baixos if i.get("type") == "image"]
    table_items = [i for i in baixos if i.get("type") == "table_cell"]

    if text_items:
        lines += [
            "## Texto",
            "| Pág | Posição (mm) | Texto extraído | Confiança | Motivo |",
            "|-----|-------------|----------------|-----------|--------|",
        ]
        for item in text_items:
            bb = item.get("bounding_box_mm", {})
            pos = f"x={bb.get('x','?')} y={bb.get('y','?')}"
            text = item.get("text", "")[:40].replace("|", "\\|")
            conf = item.get("confidence", 0)
            motivo = ", ".join(item.get("confidence_flags", ["-"])) or "-"
            lines.append(f"| {item.get('page','?')} | {pos} | \"{text}\" | {conf:.2f} | {motivo} |")
        lines.append("")

    if image_items:
        lines += [
            "## Imagens",
            "| Pág | Posição (mm) | Tamanho | Classe atual | Confiança | Motivo |",
            "|-----|-------------|---------|-------------|-----------|--------|",
        ]
        for item in image_items:
            bb = item.get("bounding_box_mm", {})
            pos = f"x={bb.get('x','?')} y={bb.get('y','?')}"
            size = f"{bb.get('width','?')}×{bb.get('height','?')}mm"
            classe = item.get("element_type", "?")
            conf = item.get("confidence", 0)
            motivo = ", ".join(item.get("confidence_flags", ["-"])) or "-"
            lines.append(f"| {item.get('page','?')} | {pos} | {size} | {classe} | {conf:.2f} | {motivo} |")
        lines.append("")

    if table_items:
        lines += [
            "## Tabelas DOCX",
            "| Tabela | Linha | Coluna | Problema |",
            "|--------|-------|--------|---------|",
        ]
        for item in table_items:
            motivo = ", ".join(item.get("confidence_flags", ["-"])) or "-"
            lines.append(f"| {item.get('table_idx','?')} | {item.get('row','?')} | {item.get('col','?')} | {motivo} |")
        lines.append("")

    return "\n".join(lines)


def gerar_relatorio(base_dir: Path) -> str:
    """Lê targets gerados e cria review_needed.md. Retorna o caminho do arquivo."""
    target_dir = base_dir / "target"
    all_items = []
    source_name = "certidao"

    extracted_path = target_dir / "certidao_extracted.json"
    if extracted_path.exists():
        with extracted_path.open(encoding="utf-8") as f:
            items = json.load(f)
        all_items.extend(items)

    tables_path = target_dir / "tables_extracted.json"
    if tables_path.exists():
        with tables_path.open(encoding="utf-8") as f:
            tables_data = json.load(f)
        for t_idx, tabela in enumerate(tables_data.get("tabelas", [])):
            for linha in tabela.get("linhas", []):
                for celula in linha.get("celulas", []):
                    if celula.get("rowspan", 1) > 1:
                        all_items.append({
                            "type": "table_cell",
                            "confidence": 0.65,
                            "confidence_flags": ["rowspan_inferido"],
                            "table_idx": t_idx,
                            "row": linha.get("indice"),
                            "col": celula.get("indice_coluna_inicial"),
                        })

    baixos = coletar_itens_baixa_confianca(all_items)
    md = formatar_relatorio(baixos, total_items=len(all_items), source_name=source_name)

    output_path = target_dir / "review_needed.md"
    output_path.parent.mkdir(parents=True, exist_ok=True)
    with output_path.open("w", encoding="utf-8") as f:
        f.write(md)

    return str(output_path)


if __name__ == "__main__":
    import sys
    base_dir = Path(__file__).parent.parent
    path = gerar_relatorio(base_dir)
    print(f"[OK] Relatório salvo em: {path}")
