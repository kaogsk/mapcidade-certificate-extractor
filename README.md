# mapcidade-certificate-extractor

> Anonymized, from-scratch reconstruction of a real internal tool's architecture, built for a portfolio. Fictional data only ("MapCidade" / Rivermeadow, Lakeside) — no real company, city, or infrastructure is represented here.

## English

### What the pipeline does

Python pipeline that converts a municipal certificate in PDF/DOCX (for example,
a land-use certificate) into structured JSON, ready to feed an automated
document generator. It grew out of the need to reuse the layout of an existing
document without retyping everything by hand: the pipeline extracts text,
images, tables, fonts and review comments, assigning a **confidence score** to
each item to flag what needs manual checking before it becomes a template.

This repository is an anonymized version of a real production project
(certificate-generation pipeline for city halls). Client names, municipalities,
database tables and credentials were removed — see the "What was simplified"
section below.

Given an input PDF and/or DOCX, the pipeline runs in sequence:

1. **`extrairFormulario.py`** — via `pdftk` (optional), extracts form fields
   and metadata from the PDF. If `pdftk` isn't installed, it returns empty
   lists without breaking the pipeline.
2. **`processarPdf.py`** — converts each page to PNG and extracts the
   **block-level text layout** (grouping PyMuPDF spans into blocks, not loose
   lines — avoids fragmenting a sentence into several items). Cross-checks
   with `pdfplumber` to validate word boundaries and detect blocks that
   should actually have been split.
3. **`extrairImagens.py`** — extracts every image embedded in the PDF, naming
   each file by its position (`x{X}y{Y}_{hash}.ext`) to allow later
   correlation with the layout.
4. **`extrairComentarios.py`** — extracts annotations/comments from the PDF
   (used as review markup in the original document) into a Markdown file.
5. **`extrairTabelas.py`** / **`extrairFontes.py`** — for DOCX input, extract
   tables (including `rowspan` detection via `w:vMerge`) and the formatting of
   each text `run` (bold, italic, font, size).
6. **`gerarRelatorio.py`** — consolidates every item with confidence below
   `0.70` into `review_needed.md`, a checklist for human review before any
   template is considered ready for use.

### Architecture: confidence score and block merging

The core idea of the pipeline is that **no extraction is treated as 100%
reliable by default**:

- **Multi-criteria image scoring**
  (`src/scoreConfianca.py`): every image extracted from the PDF is scored
  across 7 categories (`qrcode`, `logo`, `map`, `header`, `footer`, `line`,
  `image`) based on area, aspect ratio and position on the page. The final
  confidence is proportional to the **margin** between the best and
  second-best score — when two classifications tie, the item falls below the
  threshold and shows up in the review report instead of silently assuming
  the most likely classification.
- **Block-level text merge with cross-validation**
  (`src/mergerTexto.py`): PyMuPDF already groups spans into blocks, but two
  neighboring blocks (same visual line, small gap, same font) can still have
  been split incorrectly. `should_merge_blocks()` decides whether two items
  should become one; the extraction runs in parallel via `pdfplumber`, and
  when the two tools disagree on where a line starts/ends
  (`_check_split_conflict`), the output item inherits reduced confidence and
  the `split_conflict` flag — no ambiguous extraction ends up with high
  confidence just because one library didn't complain.

This is the design decision worth highlighting: instead of blindly trusting a
single extraction library, the pipeline cross-checks two sources (PyMuPDF +
pdfplumber) and turns disagreement into an explicit risk signal.

### How to run locally

```bash
pip install -r requirements.txt

# generates a synthetic PDF and DOCX in fixtures/ (no real data)
python scripts/generate_fixtures.py

# runs the full pipeline against the generated files
python main.py

# or the unit tests
pytest tests/ -v
```

The output goes to `target/`: per-page PNGs, `certidao_extracted.json` (PDF
text layout + images), `tables_extracted.json` and `word_extracted_info.json`
(DOCX), `comentarios.md`, and `review_needed.md` (items below the confidence
threshold).

`pdftk` is optional — if it isn't installed, step 1 simply returns empty (the
rest of the pipeline doesn't depend on it).

### Tests

39 unit tests (`pytest tests/`), covering:

- Parsing of `pdftk` output (form and metadata)
- Image classification scoring (7 categories, documented regression cases —
  e.g., an item at 36% of the page height should no longer fall into the
  generic `image` class because of an old 35% threshold)
- Text block merging (same line, different fonts, gaps, split conflict
  detected via `pdfplumber`)
- `rowspan` extraction in DOCX tables (`w:vMerge`)
- `run` formatting extraction (bold/italic/font/size)
- Review report generation (threshold filter, Markdown formatting)

Beyond the suite, `python main.py` was run end-to-end against the synthetic
PDF/DOCX generated by `scripts/generate_fixtures.py` — all 7 pipeline stages
completed successfully and the artifacts under `target/` were inspected
manually (see "What was simplified" for a caveat about the `rowspan` test).

### What was simplified / deliberate decisions

- **No new certificate generation (output DOCX/PDF) in this repository.** The
  original project has a second pipeline (template JSON → DOCX/PDF via
  Node.js) that reads tables from a municipal PostgreSQL database to populate
  the template. That second pipeline depends on infrastructure (a real
  database, 91+ registered municipalities, connection credentials) that
  doesn't make sense to reproduce in a portfolio repository. The
  **extraction** pipeline (PDF/DOCX → JSON), which is the technical core of
  the project and runs entirely locally, is the complete, testable story
  here.
- **`pdftk` is optional, not a hard dependency.** Form field/metadata
  extraction depends on an external binary; the code already handled that
  absence with a graceful fallback (empty lists) — kept as-is, without
  inventing a substitute.
- **DOCX table rowspan: unit-tested, not 100% on the synthetic fixture.**
  `detectar_rowspan()` is tested in isolation (`"restart"` → `start`, `""` →
  `continue`, `None` → `none`) and the `w:vMerge` extraction logic is
  unchanged from the production code. When generating the synthetic DOCX via
  `python-docx`, however, the library **normalizes reading of vertically
  merged cells** — `table.rows[n].cells[0]` starts returning the same Python
  object (the "master" cell) for every row of the merge, so extraction always
  reads `vMerge="restart"` and never detects the continuation. This is a
  quirk of tables built programmatically with the current `python-docx`
  version; it doesn't reproduce the behavior of a real DOCX exported by Word
  (where this object collision doesn't happen the same way). Documented here
  rather than hidden — the pipeline doesn't break, it just doesn't report
  `rowspan > 1` on the synthetic fixture.
- **100% fictional data.** `scripts/generate_fixtures.py` generates a PDF (2
  pages, text, "logo", "map", QR code and a review annotation) and a DOCX
  (table with a rowspan attempt, header/footer, bold runs) entirely from
  scratch — no real client data, no real municipality name, no real municipal
  law.
- **No database dependency.** `psycopg2-binary` and `paramiko` (used in the
  original project to populate templates from a municipal database and send
  images via SFTP) were removed from `requirements.txt` — they aren't part of
  the extraction pipeline.

### Demo

No deploy — this is a local processing pipeline (Python CLI), with no web
server component. `python main.py` against the synthetic fixtures (generated
by `scripts/generate_fixtures.py`) is the way to see the pipeline working
end-to-end.

### Stack

Python 3.12, PyMuPDF (`fitz`), `pdfplumber`, `python-docx`, `pytest`.
Synthetic fixtures generated with `python-docx`, PyMuPDF and Pillow.

## Português

Pipeline Python que converte um certificado municipal em PDF/DOCX (por exemplo,
uma certidão de uso e ocupação do solo) em JSON estruturado, pronto para
alimentar um gerador de documentos automatizado. Nasceu da necessidade de
reaproveitar o layout de um documento existente sem redigitar tudo à mão: o
pipeline extrai texto, imagens, tabelas, fontes e comentários de revisão,
atribuindo um **score de confiança** a cada item para sinalizar o que precisa
de checagem manual antes de virar template.

Este repositório é uma versão anonimizada de um projeto real de produção
(pipeline de geração de certidões para prefeituras). Nomes de cliente,
municípios, tabelas de banco e credenciais foram removidos — ver seção
"O que foi simplificado" abaixo.

### O que o pipeline faz

Dado um PDF e/ou DOCX de entrada, o pipeline roda em sequência:

1. **`extrairFormulario.py`** — via `pdftk` (opcional), extrai campos de
   formulário e metadados do PDF. Se `pdftk` não estiver instalado, retorna
   listas vazias sem quebrar o pipeline.
2. **`processarPdf.py`** — converte cada página em PNG e extrai o **layout de
   texto em nível de bloco** (agrupando spans do PyMuPDF em blocos, não em
   linhas soltas — evita fragmentar uma frase em vários itens). Cruza com
   `pdfplumber` para validar limites de palavra e detectar blocos que na
   verdade deveriam ter sido separados.
3. **`extrairImagens.py`** — extrai todas as imagens embutidas no PDF,
   nomeando cada arquivo pela posição (`x{X}y{Y}_{hash}.ext`) para permitir
   correlação posterior com o layout.
4. **`extrairComentarios.py`** — extrai anotações/comentários do PDF (usados
   como marcações de revisão no documento original) para um Markdown.
5. **`extrairTabelas.py`** / **`extrairFontes.py`** — para a entrada DOCX,
   extraem tabelas (incluindo detecção de `rowspan` via `w:vMerge`) e a
   formatação de cada `run` de texto (negrito, itálico, fonte, tamanho).
6. **`gerarRelatorio.py`** — consolida todos os itens com confiança abaixo de
   `0.70` em `review_needed.md`, um checklist para revisão humana antes de
   qualquer template ser considerado pronto para uso.

### Arquitetura: score de confiança e merge de blocos

O ponto central do pipeline é que **nenhuma extração é tratada como 100%
confiável por padrão**:

- **Classificação de imagem por scoring multicritério**
  (`src/scoreConfianca.py`): cada imagem extraída do PDF é pontuada em 7
  categorias (`qrcode`, `logo`, `map`, `header`, `footer`, `line`, `image`)
  a partir de área, proporção e posição na página. A confiança final é
  proporcional à **margem** entre a melhor e a segunda melhor pontuação —
  quando duas classificações empatam, o item cai abaixo do threshold e
  aparece no relatório de revisão em vez de silenciosamente assumir a
  classificação mais provável.
- **Merge de texto em nível de bloco com validação cruzada**
  (`src/mergerTexto.py`): o PyMuPDF já agrupa spans em blocos, mas dois
  blocos vizinhos (mesma linha visual, gap pequeno, mesma fonte) ainda podem
  ter sido cortados incorretamente. `should_merge_blocks()` decide se dois
  itens devem virar um só; a extração roda em paralelo via `pdfplumber` e,
  quando as duas ferramentas discordam sobre onde uma linha começa/termina
  (`_check_split_conflict`), o item de saída herda confiança reduzida e a
  flag `split_conflict` — nenhuma extração ambígua fica com confiança alta
  só porque uma biblioteca não reclamou.

Essa é a decisão de design que vale a pena mostrar: em vez de confiar cegamente
em uma única biblioteca de extração, o pipeline cruza duas fontes
(PyMuPDF + pdfplumber) e transforma divergência em sinal explícito de risco.

### Como rodar localmente

```bash
pip install -r requirements.txt

# gera um PDF e um DOCX sintéticos em fixtures/ (sem nenhum dado real)
python scripts/generate_fixtures.py

# roda o pipeline completo contra os arquivos gerados
python main.py

# ou os testes unitários
pytest tests/ -v
```

A saída fica em `target/`: PNGs por página, `certidao_extracted.json` (layout
de texto + imagens do PDF), `tables_extracted.json` e
`word_extracted_info.json` (DOCX), `comentarios.md`, e `review_needed.md`
(itens abaixo do threshold de confiança).

`pdftk` é opcional — se não estiver instalado, a etapa 1 simplesmente retorna
vazio (o restante do pipeline não depende dela).

### Testes

39 testes unitários (`pytest tests/`), cobrindo:

- Parsing de saída `pdftk` (formulário e metadados)
- Scoring de classificação de imagem (7 categorias, casos de regressão
  documentados — ex.: um item a 36% da altura da página não deve mais cair
  na classe genérica `image` por causa de um threshold antigo de 35%)
- Merge de blocos de texto (mesma linha, fontes diferentes, gaps, conflito
  de split detectado via `pdfplumber`)
- Extração de `rowspan` em tabelas DOCX (`w:vMerge`)
- Extração de formatação de `run` (negrito/itálico/fonte/tamanho)
- Geração do relatório de revisão (filtro por threshold, formatação Markdown)

Além da suíte, `python main.py` foi rodado de ponta a ponta contra o PDF/DOCX
sintéticos gerados por `scripts/generate_fixtures.py` — as 7 etapas do
pipeline completaram com sucesso e os artefatos em `target/` foram
inspecionados manualmente (ver "O que foi simplificado" para uma ressalva
sobre o teste de `rowspan`).

### O que foi simplificado / decisões conscientes

- **Sem geração de certidão nova (DOCX/PDF de saída) neste repositório.** O
  projeto original tem um segundo pipeline (JSON de template → DOCX/PDF via
  Node.js) que lê tabelas de um banco PostgreSQL municipal para popular o
  template. Esse segundo pipeline depende de infraestrutura (banco real,
  91+ municípios cadastrados, credenciais de conexão) que não faz sentido
  reproduzir num repositório de portfólio. O pipeline de **extração**
  (PDF/DOCX → JSON), que é o coração técnico do projeto e roda inteiramente
  local, é a história completa e testável aqui.
- **`pdftk` é opcional, não uma dependência rígida.** A extração de campos de
  formulário/metadados depende de um binário externo; o código já tratava
  essa ausência com um fallback gracioso (listas vazias) — mantido como
  está, sem inventar um substituto.
- **Rowspan em tabela DOCX: testado em unidade, não 100% no fixture
  sintético.** `detectar_rowspan()` é testado isoladamente (`"restart"` →
  `start`, `""` → `continue`, `None` → `none`) e a lógica de extração de
  `w:vMerge` está inalterada em relação ao código de produção. Ao gerar o
  DOCX sintético via `python-docx`, no entanto, a biblioteca **normaliza a
  leitura de células verticalmente mescladas** — `table.rows[n].cells[0]`
  passa a devolver o mesmo objeto Python (o "cell" mestre) para todas as
  linhas do merge, então a extração lê sempre `vMerge="restart"` e nunca
  detecta a continuação. Isso é uma particularidade de tabelas construídas
  programaticamente com a versão atual de `python-docx`; não reproduz o
  comportamento de um DOCX real exportado pelo Word (onde essa colisão de
  objeto não ocorre da mesma forma). Documentado aqui em vez de escondido —
  o pipeline não quebra, apenas não reporta `rowspan > 1` no fixture
  sintético.
- **Dados 100% fictícios.** `scripts/generate_fixtures.py` gera um PDF (2
  páginas, texto, "logo", "mapa", QR code e uma anotação de revisão) e um
  DOCX (tabela com tentativa de rowspan, cabeçalho/rodapé, runs com negrito)
  inteiramente do zero — nenhum dado de cliente real, nenhum nome de
  município real, nenhuma lei municipal real.
- **Sem dependência de banco de dados.** `psycopg2-binary` e `paramiko`
  (usadas no projeto original para popular templates a partir de um banco
  municipal e enviar imagens por SFTP) foram removidas do
  `requirements.txt` — não fazem parte do pipeline de extração.

### Demo

Não há deploy — este é um pipeline de processamento local (CLI Python), sem
componente de servidor web. `python main.py` contra os fixtures sintéticos
(gerados por `scripts/generate_fixtures.py`) é a forma de ver o pipeline
funcionando de ponta a ponta.

### Stack

Python 3.12, PyMuPDF (`fitz`), `pdfplumber`, `python-docx`, `pytest`. Fixtures
sintéticas geradas com `python-docx`, PyMuPDF e Pillow.

## License

MIT — see [LICENSE](./LICENSE).
