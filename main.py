#!/usr/bin/env python3
import sys
import os
from pathlib import Path
import subprocess


def print_header(message):
    print("\n" + "=" * 80)
    print(f"  {message}")
    print("=" * 80)


def print_success(message):
    print(f"[OK] {message}")


def print_error(message):
    print(f"[ERRO] {message}")


def print_warning(message):
    print(f"[AVISO] {message}")


def print_info(message):
    print(f"[INFO] {message}")


def check_file_exists(file_path, description):
    if file_path.exists():
        print_success(f"{description} encontrado: {file_path.name}")
        return True
    else:
        print_warning(f"{description} não encontrado: {file_path.name}")
        return False


def run_script(script_name, description, interactive=False):
    script_path = Path(__file__).parent / "src" / script_name
    
    if not script_path.exists():
        print_error(f"Script não encontrado: {script_path}")
        return False
    
    print_info(f"Executando: {description}")
    
    try:
        if interactive:
            result = subprocess.run(
                [sys.executable, str(script_path)],
                cwd=Path(__file__).parent
            )
        else:
            result = subprocess.run(
                [sys.executable, str(script_path)],
                cwd=Path(__file__).parent,
                capture_output=True,
                text=True,
                encoding='cp1252',
                errors='replace'
            )
            
            if result.stdout:
                print(result.stdout)
        
        if result.returncode == 0:
            print_success(f"{description} concluído")
            return True
        else:
            print_error(f"{description} falhou")
            if not interactive and result.stderr:
                print(f"Erro: {result.stderr}")
            return False
            
    except Exception as e:
        print_error(f"Erro ao executar {script_name}: {e}")
        return False


def main():
    base_dir = Path(__file__).parent

    print_header("PROCESSAMENTO DE CERTIDÕES")
    print_info("Verificando arquivos necessários...\n")

    pdf_path = base_dir / "fixtures" / "sample_certificate.pdf"
    docx_path = base_dir / "fixtures" / "sample_certificate.docx"

    has_pdf = check_file_exists(pdf_path, "Arquivo PDF")
    has_docx = check_file_exists(docx_path, "Arquivo DOCX")

    if not has_pdf and not has_docx:
        print_error("\nNenhum arquivo de entrada encontrado!")
        print_info("Rode 'python scripts/generate_fixtures.py' para gerar os arquivos de exemplo em fixtures/")
        return 1

    target_dir = base_dir / "target"
    target_dir.mkdir(exist_ok=True)

    executions = []
    etapa_num = 1

    if has_pdf:
        print_header(f"ETAPA {etapa_num}: Extrair metadados e formulário (pdftk)")
        success = run_script("extrairFormulario.py", "Extrair metadados e campos de formulário (pdftk)")
        executions.append(("Extrair formulário/metadados", success))
        etapa_num += 1

        print_header(f"ETAPA {etapa_num}: Processar PDF")
        success = run_script("processarPdf.py", "Processar PDF (block-level + pdfplumber + merger + scoring)")
        executions.append(("Processar PDF", success))
        etapa_num += 1

        print_header(f"ETAPA {etapa_num}: Extrair imagens")
        success = run_script("extrairImagens.py", "Extrair imagens do PDF com posicionamento")
        executions.append(("Extrair imagens", success))
        etapa_num += 1

        print_header(f"ETAPA {etapa_num}: Extrair comentários")
        success = run_script("extrairComentarios.py", "Extrair comentários do PDF")
        executions.append(("Extrair comentários", success))
        etapa_num += 1
    else:
        print_info("PDF não disponível - pulando processamento de PDF")

    if has_docx:
        print_header(f"ETAPA {etapa_num}: Extrair tabelas")
        success = run_script("extrairTabelas.py", "Extrair tabelas do DOCX (com rowspan)")
        executions.append(("Extrair tabelas", success))
        etapa_num += 1

        print_header(f"ETAPA {etapa_num}: Extrair fontes")
        success = run_script("extrairFontes.py", "Extrair fontes do DOCX (com runs)")
        executions.append(("Extrair fontes", success))
        etapa_num += 1
    else:
        print_info("DOCX não disponível - pulando processamento de DOCX")

    print_header(f"ETAPA {etapa_num}: Gerar relatório de revisão")
    success = run_script("gerarRelatorio.py", "Gerar review_needed.md")
    executions.append(("Gerar relatório", success))
    etapa_num += 1

    print_header("RESUMO DA EXECUÇÃO")
    if executions:
        print("\nEtapas executadas:")
        for name, s in executions:
            status = "Sucesso" if s else "Falhou"
            print(f"  - {name}: {status}")

        total = len(executions)
        successful = sum(1 for _, s in executions if s)

        review_path = base_dir / "target" / "review_needed.md"
        if review_path.exists():
            print()
            with review_path.open(encoding="utf-8") as f:
                f.readline()
                second_line = f.readline().strip()
            print_info(f"Relatório: {second_line}")

        print(f"\nTotal: {successful}/{total} etapas concluídas com sucesso")
        if successful == total:
            print_success("Processamento completo!")
            return 0
        else:
            print_warning("Processamento concluído com algumas falhas")
            return 1
    else:
        print_warning("Nenhuma etapa foi executada")
        return 1


if __name__ == "__main__":
    try:
        sys.exit(main())
    except KeyboardInterrupt:
        print("\n\n[AVISO] Processamento interrompido pelo usuario")
        sys.exit(1)
    except Exception as e:
        print_error(f"Erro inesperado: {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)
