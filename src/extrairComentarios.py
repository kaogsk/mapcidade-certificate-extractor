import fitz
import os


def extract_comments_from_pdf(pdf_path, output_md_path):
    doc = fitz.open(pdf_path)
    
    comments_data = []
    
    for page_num, page in enumerate(doc, start=1):
        annotations = page.annots()
        
        if annotations:
            for annot in annotations:
                annot_type = annot.type[0]

                comment_text = annot.info.get("content", "").strip()
                
                highlighted_text = ""
                
                try:
                    rect = annot.rect
                    
                    highlighted_text = page.get_textbox(rect).strip()
                    
                    if not highlighted_text:
                        quads = annot.vertices
                        if quads:
                            for i in range(0, len(quads), 4):
                                    quad_rect = fitz.Quad(quads[i:i+4]).rect
                                    text = page.get_textbox(quad_rect).strip()
                                    if text:
                                        highlighted_text += text + " "
                            highlighted_text = highlighted_text.strip()
                
                except Exception as e:
                    print(f"Erro ao extrair texto destacado na página {page_num}: {e}")
                
                if comment_text or highlighted_text:
                    comments_data.append({
                        "page": page_num,
                        "highlighted_text": highlighted_text or "(sem texto destacado)",
                        "comment": comment_text or "(sem comentário)"
                    })
    
    doc.close()
    
    os.makedirs(os.path.dirname(output_md_path), exist_ok=True)
    
    with open(output_md_path, "w", encoding="utf-8") as f:
        f.write("# Comentários do PDF\n\n")
        f.write("texto destacado | comentario\n")
        f.write("--- | ---\n")
        
        for item in comments_data:
            highlighted = item["highlighted_text"].replace("\n", " ").replace("|", "\\|")
            comment = item["comment"].replace("\n", " ").replace("|", "\\|")
            f.write(f"{highlighted} | {comment}\n")
    
    print(f"[OK] Arquivo Markdown gerado: {output_md_path}")
    print(f"Total de comentários extraídos: {len(comments_data)}")


if __name__ == "__main__":
    projeto_raiz = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
    pdf_path = os.path.join(projeto_raiz, "fixtures", "sample_certificate.pdf")
    
    output_md_path = os.path.join(projeto_raiz, "target", "comentarios.md")
    
    if not os.path.exists(pdf_path):
        print(f"[ERRO] Arquivo '{pdf_path}' nao encontrado!")
        exit(1)
    
    extract_comments_from_pdf(pdf_path, output_md_path)
