# mapcidade-certificate-extractor

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

## O que o pipeline faz

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

## Arquitetura: score de confiança e merge de blocos

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

## Como rodar localmente

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

## Testes

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

## O que foi simplificado / decisões conscientes

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

## Demo

Não há deploy — este é um pipeline de processamento local (CLI Python), sem
componente de servidor web. `python main.py` contra os fixtures sintéticos
(gerados por `scripts/generate_fixtures.py`) é a forma de ver o pipeline
funcionando de ponta a ponta.

## Stack

Python 3.12, PyMuPDF (`fitz`), `pdfplumber`, `python-docx`, `pytest`. Fixtures
sintéticas geradas com `python-docx`, PyMuPDF e Pillow.
