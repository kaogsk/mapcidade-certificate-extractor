import subprocess
import json
import sys
from pathlib import Path
from typing import Dict, List


def parse_pdftk_fields(output: str) -> List[Dict]:
    """Parseia saída de 'pdftk dump_data_fields' em lista de campos."""
    fields = []
    current: Dict = {}
    for line in output.splitlines():
        line = line.strip()
        if line.startswith("FieldName:"):
            current["name"] = line.split(":", 1)[1].strip()
        elif line.startswith("FieldValue:"):
            val = line.split(":", 1)[1].strip()
            current["value"] = val
        elif line == "---":
            if current.get("name") and current.get("value"):
                fields.append({
                    "name": current["name"],
                    "value": current["value"],
                    "confidence": 0.98,
                })
            current = {}
    if current.get("name") and current.get("value"):
        fields.append({"name": current["name"], "value": current["value"], "confidence": 0.98})
    return fields


def parse_pdftk_metadata(output: str) -> Dict:
    """Parseia saída de 'pdftk dump_data' em dict de metadados."""
    meta: Dict = {}
    key_map = {
        "Title": "title",
        "Author": "author",
        "Subject": "subject",
        "Creator": "creator",
        "CreationDate": "creation_date",
        "ModDate": "mod_date",
    }
    current_key = None
    for line in output.splitlines():
        line = line.strip()
        if line.startswith("InfoKey:"):
            current_key = line.split(":", 1)[1].strip()
        elif line.startswith("InfoValue:") and current_key:
            val = line.split(":", 1)[1].strip()
            if val and current_key in key_map:
                meta[key_map[current_key]] = val
            current_key = None
    return meta


def extrair_formulario(pdf_path: Path) -> Dict:
    """
    Extrai campos de formulário e metadados via pdftk.
    Retorna {"fields": [], "metadata": {}} se pdftk indisponível.
    """
    result = {"fields": [], "metadata": {}}

    try:
        meta_proc = subprocess.run(
            ["pdftk", str(pdf_path), "dump_data"],
            capture_output=True, text=True, timeout=30
        )
        if meta_proc.returncode == 0:
            result["metadata"] = parse_pdftk_metadata(meta_proc.stdout)
    except (FileNotFoundError, subprocess.TimeoutExpired):
        return result

    try:
        fields_proc = subprocess.run(
            ["pdftk", str(pdf_path), "dump_data_fields"],
            capture_output=True, text=True, timeout=30
        )
        if fields_proc.returncode == 0:
            result["fields"] = parse_pdftk_fields(fields_proc.stdout)
    except (FileNotFoundError, subprocess.TimeoutExpired):
        pass

    return result


def salvar_formulario(data: Dict, output_dir: Path) -> None:
    output_dir.mkdir(parents=True, exist_ok=True)
    if data.get("fields"):
        with (output_dir / "form_fields.json").open("w", encoding="utf-8") as f:
            json.dump(data["fields"], f, ensure_ascii=False, indent=2)
    if data.get("metadata"):
        with (output_dir / "metadata.json").open("w", encoding="utf-8") as f:
            json.dump(data["metadata"], f, ensure_ascii=False, indent=2)


if __name__ == "__main__":
    base_dir = Path(__file__).parent.parent
    pdf_path = base_dir / "fixtures" / "sample_certificate.pdf"
    if not pdf_path.exists():
        print("Arquivo 'fixtures/sample_certificate.pdf' não encontrado")
        sys.exit(1)
    data = extrair_formulario(pdf_path)
    salvar_formulario(data, base_dir / "target")
    n_fields = len(data.get("fields", []))
    n_meta = len(data.get("metadata", {}))
    print(f"[OK] {n_fields} campo(s) de formulário, {n_meta} metadado(s) extraídos")
