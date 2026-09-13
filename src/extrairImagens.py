import fitz
import os
import hashlib
from pathlib import Path


PT_TO_MM = 25.4 / 72.0


def pt_to_mm(v: float) -> float:
    """Converte pontos para milímetros."""
    return v * PT_TO_MM


def gerar_hash_curta(image_bytes, length=8):
    """
    Gera uma hash curta a partir dos bytes da imagem.
    
    Args:
        image_bytes (bytes): Bytes da imagem
        length (int): Tamanho da hash (padrão: 8)
    
    Returns:
        str: Hash curta em hexadecimal
    """
    hash_completa = hashlib.md5(image_bytes).hexdigest()
    return hash_completa[:length]


def extrair_imagens_pdf(pdf_path, output_dir=None):
    """
    Extrai todas as imagens de um PDF e salva na pasta especificada.
    Cada imagem recebe um nome com posição e hash: x{X}y{Y}_{hash}.{ext}
    
    Args:
        pdf_path (str): Caminho para o arquivo PDF
        output_dir (str): Diretório de saída para as imagens (padrão: target/imagens)
    
    Returns:
        dict: Dicionário com informações das imagens extraídas
              {caminho: {hash, tamanho, extensão, página, posição}}
    """
    if output_dir is None:
        projeto_raiz = Path(__file__).parent.parent
        output_dir = projeto_raiz / "target" / "imagens"
    
    Path(output_dir).mkdir(parents=True, exist_ok=True)
    
    doc = fitz.open(pdf_path)
    imagens_extraidas = {}
    contador_imagens = 0
    
    for pagina_num in range(len(doc)):
        pagina = doc[pagina_num]
        
        image_list = pagina.get_images(full=True)
        
        image_rects = {}
        for img_info in image_list:
            xref = img_info[0]
            
            rects = pagina.get_image_rects(xref)
            if rects:
                image_rects[xref] = rects[0]
        
        for img_info in image_list:
            xref = img_info[0]
            
            if xref not in image_rects:
                continue
            
            rect = image_rects[xref]
            x0, y0, x1, y1 = rect
            
            x_mm = int(round(pt_to_mm(x0)))
            y_mm = int(round(pt_to_mm(y1)))
            
            try:
                base_image = doc.extract_image(xref)
                image_bytes = base_image["image"]
                image_ext = base_image["ext"]
                
                hash_curta = gerar_hash_curta(image_bytes)
                
                nome_arquivo = f"x{x_mm}y{y_mm}_{hash_curta}.{image_ext}"
                caminho_completo = os.path.join(output_dir, nome_arquivo)
                
                with open(caminho_completo, "wb") as img_file:
                    img_file.write(image_bytes)
                
                imagens_extraidas[caminho_completo] = {
                    "hash": hash_curta,
                    "tamanho": len(image_bytes),
                    "extensao": image_ext,
                    "pagina": pagina_num + 1,
                    "posicao_mm": {"x": x_mm, "y": y_mm},
                    "bbox_pt": {"x0": x0, "y0": y0, "x1": x1, "y1": y1}
                }
                contador_imagens += 1
                print(f"[OK] Extraída: {nome_arquivo} (pág {pagina_num + 1}, pos: x={x_mm}mm y={y_mm}mm)")
                
            except Exception as e:
                print(f"[ERRO] Erro ao extrair imagem xref={xref} na página {pagina_num + 1}: {e}")
                continue
    
    doc.close()
    
    print(f"\nTotal de imagens extraídas: {contador_imagens}")
    print(f"Pasta de destino: {output_dir}")
    
    return imagens_extraidas


if __name__ == "__main__":
    import sys
    
    if len(sys.argv) < 2:
        projeto_raiz = Path(__file__).parent.parent
        pdf_path = projeto_raiz / "fixtures" / "sample_certificate.pdf"

        if not pdf_path.exists():
            print("Erro: Arquivo fixtures/sample_certificate.pdf não encontrado")
            sys.exit(1)
        
        pdf_path = str(pdf_path)
    else:
        pdf_path = sys.argv[1]
        
        if not os.path.exists(pdf_path):
            print(f"Erro: Arquivo não encontrado: {pdf_path}")
            sys.exit(1)
    
    print(f"Processando PDF: {pdf_path}\n")
    extrair_imagens_pdf(pdf_path)
