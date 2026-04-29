/**
 * Gera o relatório técnico da Fase 1 do MedChat em .docx.
 *
 * Uso:
 *   node docs/relatorios/_gerar_docx.js
 *
 * Saída: docs/relatorios/medchat-fase-1.docx
 *
 * Pré-requisito: 3 PNGs em docs/relatorios/_assets/ (gerados por
 * `_gerar_assets.py`).
 */

const fs = require("fs");
const path = require("path");
const {
  Document,
  Packer,
  Paragraph,
  TextRun,
  Table,
  TableRow,
  TableCell,
  ImageRun,
  AlignmentType,
  HeadingLevel,
  LevelFormat,
  PageBreak,
  BorderStyle,
  WidthType,
  ShadingType,
  TableOfContents,
} = require("docx");

// ---------------------------------------------------------------------------
// Config
// ---------------------------------------------------------------------------
const ROOT = path.resolve(__dirname, "../..");
const ASSETS = path.join(__dirname, "_assets");
const OUTPUT = path.join(__dirname, "medchat-fase-1.docx");

// A4 retrato: 11906 x 16838 DXA. Margem 2.5cm = ~1417 DXA.
const PAGE_WIDTH = 11906;
const PAGE_HEIGHT = 16838;
const MARGIN = 1417;
const CONTENT_WIDTH = PAGE_WIDTH - 2 * MARGIN; // 9072 DXA

// Largura útil em pixels (96 DPI): 9072 * 96 / 1440 ≈ 605 px. Vou usar 600.
const IMG_WIDTH_PX = 600;

// Cores
const COR_TEXTO = "24292F";
const COR_DESTAQUE = "1F6FEB";
const COR_CODIGO_FUNDO = "F0F0F0";
const COR_BORDA_TABELA = "CCCCCC";
const COR_HEADER_TABELA = "D5E8F0";

// ---------------------------------------------------------------------------
// Helpers
// ---------------------------------------------------------------------------
function p(text, options = {}) {
  return new Paragraph({
    children: [new TextRun({ text, size: 22, ...options })],
    spacing: { after: 160 },
    alignment: options.alignment,
  });
}

function pRich(runs, options = {}) {
  return new Paragraph({
    children: runs,
    spacing: { after: 160 },
    ...options,
  });
}

function run(text, options = {}) {
  return new TextRun({ text, size: 22, ...options });
}

function code(text, options = {}) {
  return new TextRun({
    text,
    size: 20,
    font: "Consolas",
    ...options,
  });
}

function h1(text) {
  return new Paragraph({
    heading: HeadingLevel.HEADING_1,
    children: [new TextRun({ text, size: 36, bold: true })],
    spacing: { before: 360, after: 200 },
  });
}

function h2(text) {
  return new Paragraph({
    heading: HeadingLevel.HEADING_2,
    children: [new TextRun({ text, size: 28, bold: true })],
    spacing: { before: 240, after: 160 },
  });
}

function bullet(text, runs = null) {
  return new Paragraph({
    numbering: { reference: "bullets", level: 0 },
    children: runs || [new TextRun({ text, size: 22 })],
    spacing: { after: 80 },
  });
}

function numbered(runs) {
  return new Paragraph({
    numbering: { reference: "numbers", level: 0 },
    children: runs,
    spacing: { after: 80 },
  });
}

function pageBreak() {
  return new Paragraph({ children: [new PageBreak()] });
}

function blank() {
  return new Paragraph({ children: [new TextRun({ text: "" })] });
}

function codeBlock(text) {
  // Cada linha vira um Paragraph com fundo cinza para simular bloco de código.
  return text.split("\n").map(
    (line) =>
      new Paragraph({
        children: [
          new TextRun({
            text: line || " ",
            size: 18,
            font: "Consolas",
          }),
        ],
        shading: { fill: COR_CODIGO_FUNDO, type: ShadingType.CLEAR },
        spacing: { after: 0, line: 260 },
        indent: { left: 200 },
      })
  );
}

function image(filename, widthPx, heightPx, captionText) {
  const filePath = path.join(ASSETS, filename);
  const ext = path.extname(filename).slice(1).toLowerCase();
  const data = fs.readFileSync(filePath);

  const imgPara = new Paragraph({
    alignment: AlignmentType.CENTER,
    spacing: { before: 200, after: 80 },
    children: [
      new ImageRun({
        type: ext,
        data,
        transformation: { width: widthPx, height: heightPx },
        altText: { title: captionText, description: captionText, name: filename },
      }),
    ],
  });

  const captionPara = new Paragraph({
    alignment: AlignmentType.CENTER,
    spacing: { after: 240 },
    children: [
      new TextRun({
        text: captionText,
        size: 20,
        italics: true,
        color: "555555",
      }),
    ],
  });

  return [imgPara, captionPara];
}

function tableSimple(rows, columnWidthsDxa) {
  const totalWidth = columnWidthsDxa.reduce((a, b) => a + b, 0);
  const border = { style: BorderStyle.SINGLE, size: 4, color: COR_BORDA_TABELA };
  const cellBorders = { top: border, bottom: border, left: border, right: border };

  return new Table({
    width: { size: totalWidth, type: WidthType.DXA },
    columnWidths: columnWidthsDxa,
    rows: rows.map((row, rowIndex) => {
      const isHeader = rowIndex === 0;
      return new TableRow({
        tableHeader: isHeader,
        children: row.map((cellText, colIndex) => {
          return new TableCell({
            borders: cellBorders,
            width: { size: columnWidthsDxa[colIndex], type: WidthType.DXA },
            shading: isHeader
              ? { fill: COR_HEADER_TABELA, type: ShadingType.CLEAR }
              : undefined,
            margins: { top: 80, bottom: 80, left: 120, right: 120 },
            children: cellText.split("\n").map(
              (line) =>
                new Paragraph({
                  children: [
                    new TextRun({ text: line, size: 20, bold: isHeader }),
                  ],
                  spacing: { after: 40 },
                })
            ),
          });
        }),
      });
    }),
  });
}

// ---------------------------------------------------------------------------
// Conteúdo
// ---------------------------------------------------------------------------

const capa = [
  blank(),
  blank(),
  blank(),
  blank(),
  new Paragraph({
    alignment: AlignmentType.CENTER,
    spacing: { after: 320 },
    children: [
      new TextRun({
        text: "MedChat",
        size: 72,
        bold: true,
        color: COR_DESTAQUE,
      }),
    ],
  }),
  new Paragraph({
    alignment: AlignmentType.CENTER,
    spacing: { after: 240 },
    children: [
      new TextRun({
        text: "Relatório técnico da Fase 1",
        size: 48,
        bold: true,
        color: COR_TEXTO,
      }),
    ],
  }),
  new Paragraph({
    alignment: AlignmentType.CENTER,
    spacing: { after: 800 },
    children: [
      new TextRun({
        text: "Fundação Django: multi-tenant, modelo de domínio e loop do MVP",
        size: 28,
        italics: true,
        color: "555555",
      }),
    ],
  }),
  blank(),
  blank(),
  blank(),
  blank(),
  new Paragraph({
    alignment: AlignmentType.CENTER,
    spacing: { after: 80 },
    children: [
      new TextRun({
        text: "Gerado em 2026-04-29",
        size: 22,
        color: "555555",
      }),
    ],
  }),
  new Paragraph({
    alignment: AlignmentType.CENTER,
    children: [
      new TextRun({
        text: "18 commits  ·  53 testes verdes  ·  7 containers UP",
        size: 22,
        color: "555555",
      }),
    ],
  }),
  pageBreak(),
];

const sumario = [
  h1("Sumário"),
  new Paragraph({
    children: [
      new TextRun({
        text: "(Atualize o sumário no Word: clique com o botão direito → Atualizar Campo)",
        italics: true,
        size: 18,
        color: "888888",
      }),
    ],
    spacing: { after: 160 },
  }),
  new TableOfContents("Sumário", {
    hyperlink: true,
    headingStyleRange: "1-2",
  }),
  pageBreak(),
];

// === Seção 1 ===
const secao1 = [
  h1("1. Sobre o produto MedChat"),
  pRich([
    run("O MedChat é um SaaS B2B vendido para "),
    run("clínicas médicas", { bold: true }),
    run(
      ". O cliente pagante é a clínica; o usuário final é o paciente, que conversa com o bot via WhatsApp. O produto se posiciona como "
    ),
    run("secretária virtual com IA", { bold: true }),
    run(
      ": agenda, remarca e cancela consultas, dispara lembretes e — quando incerta — escala para um atendente humano da clínica."
    ),
  ]),
  p("Algumas premissas que governam o design:"),
  bullet(null, [
    new TextRun({ text: "Multi-tenant desde o dia 1. ", size: 22, bold: true }),
    new TextRun({
      text:
        "Cada clínica enxerga apenas os próprios pacientes, médicos, agendamentos e conversas. O isolamento é físico no banco (Postgres com Row-Level Security), não confiança no código de aplicação.",
      size: 22,
    }),
  ]),
  bullet(null, [
    new TextRun({ text: "Bot declara que é IA. ", size: 22, bold: true }),
    new TextRun({
      text:
        'Logo na primeira mensagem o paciente lê "sou a assistente virtual da Clínica X". Não simulamos humano — questão de transparência e proteção contra reclamação.',
      size: 22,
    }),
  ]),
  bullet(null, [
    new TextRun({ text: "Escopo enxuto no MVP. ", size: 22, bold: true }),
    new TextRun({
      text:
        "Agendar, remarcar, cancelar consulta + lembretes automáticos. Triagem clínica e pagamentos ficam de fora (LGPD Art. 11 e regulação CFM aumentam risco).",
      size: 22,
    }),
  ]),
  bullet(null, [
    new TextRun({ text: "4 gatilhos de handoff humano: ", size: 22, bold: true }),
    new TextRun({
      text:
        "pedido explícito do paciente, baixa confiança da IA (pergunta fora do FAQ/escopo), palavras de urgência médica (dor no peito, sangramento, desmaio), reclamação ou após N falhas de entendimento.",
      size: 22,
    }),
  ]),
  p(
    "A Fase 1 entregou a fundação técnica: estrutura multi-tenant, modelo de domínio completo, infra Celery e o loop end-to-end de webhook → eco automático. Falta apenas o cliente HTTP real do provedor WhatsApp e a integração com o Langfuse para fechar a experiência."
  ),
];

// === Seção 2 ===
const stackRows = [
  ["Camada", "Escolha", "Justificativa breve"],
  [
    "Linguagem / gerenciador",
    "Python 3.13 + uv",
    "Rápido para resolver dependências; modelo Cargo-like",
  ],
  [
    "Web framework",
    "Django 5 + Django Ninja",
    "ORM maduro; Ninja dá REST tipado sem o peso do DRF",
  ],
  [
    "Banco",
    "Postgres 17 + pgvector",
    "RLS nativo, rich types (range, JSONB), pgvector pronto pra Fase 2",
  ],
  [
    "Cache + broker",
    "Redis 7",
    "Padrão da indústria; Django/Celery integram nativamente",
  ],
  [
    "Async",
    "Celery + Celery Beat",
    "Retry, scheduler, autodiscover de tasks",
  ],
  [
    "LLM",
    "Anthropic SDK (principal) + OpenRouter (fallback)",
    "Anthropic com prompt caching forte; OpenRouter cobre indisponibilidade",
  ],
  [
    "Observabilidade AI",
    "Langfuse self-hosted",
    "Trace de prompts, custos e tokens — independente do provider",
  ],
  [
    "Canal WhatsApp",
    "Evolution API (MVP) → WhatsApp Cloud API (prod)",
    "Evolution rápido pra protótipo; Cloud para evitar bans",
  ],
  ["Deploy", "Railway", "PaaS simples para a fase de validação"],
  [
    "Testes",
    "pytest + pytest-django + factory-boy",
    "Testes de integração contra Postgres real",
  ],
  ["Lint", "ruff", "Único formatter+linter; rápido"],
];

const secao2 = [
  h1("2. Stack escolhido"),
  tableSimple(stackRows, [2400, 2700, 3972]),
  blank(),
  pRich([
    run("Por que sair do n8n. ", { bold: true }),
    run("O projeto começou como prova-de-conceito em n8n (workflow "),
    code("0O13PjgBKcONHd0F"),
    run(
      "). A revisão concluiu que Django+Postgres ganha em três pontos: testabilidade (pytest contra Postgres real), migrations versionadas no git (versus exportar JSON do n8n), e suporte nativo a RLS — peça central da arquitetura multi-tenant."
    ),
  ]),
];

// === Seção 3 ===
const secao3 = [
  h1("3. Multi-tenancy via Row-Level Security"),
  h2("3.1 O problema"),
  pRich([
    run(
      "Um banco, N clínicas. Como garantir que a clínica A nunca veja pacientes da clínica B, mesmo se um desenvolvedor distraído escrever uma query sem "
    ),
    code("WHERE clinica_id = ..."),
    run("?"),
  ]),
  p("Três abordagens são clássicas:"),
  bullet(null, [
    new TextRun({ text: "Banco por tenant. ", size: 22, bold: true }),
    new TextRun({
      text:
        "Caro de provisionar, lento pra adicionar novo cliente, dificulta queries analíticas cross-tenant.",
      size: 22,
    }),
  ]),
  bullet(null, [
    new TextRun({ text: "Schema por tenant. ", size: 22, bold: true }),
    new TextRun({
      text:
        "Meio termo. Migrations multiplicam por N, ferramental Postgres não foi pensado pra esse padrão.",
      size: 22,
    }),
  ]),
  bullet(null, [
    new TextRun({
      text: "Row-Level Security (RLS). ",
      size: 22,
      bold: true,
    }),
    new TextRun({
      text:
        "Um banco, um schema, mas cada tabela tem uma policy SQL que filtra linhas baseado numa variável de sessão. É a abordagem escolhida (justificativa em docs/adr/0002-rls-vs-schema.md).",
      size: 22,
    }),
  ]),

  h2("3.2 Como funciona uma request"),
  pRich([
    run("A figura abaixo mostra o caminho de uma request HTTP através do "),
    code("RLSMiddleware"),
    run(":"),
  ]),
  ...image(
    "fluxo-rls.png",
    IMG_WIDTH_PX,
    Math.round(IMG_WIDTH_PX / 2.167),
    "Figura 1 — Fluxo de uma request pelo RLSMiddleware"
  ),
  p("A sequência:"),
  numbered([
    new TextRun({ text: "Cliente envia request com header ", size: 22 }),
    new TextRun({ text: "X-Clinic-Slug: clinica-x", size: 22, font: "Consolas" }),
    new TextRun({ text: ".", size: 22 }),
  ]),
  numbered([
    new TextRun({ text: "RLSMiddleware ", size: 22, font: "Consolas" }),
    new TextRun({ text: "resolve o slug para o UUID da clínica.", size: 22 }),
  ]),
  numbered([
    new TextRun({ text: "Abre ", size: 22 }),
    new TextRun({ text: "transaction.atomic()", size: 22, font: "Consolas" }),
    new TextRun({ text: " e executa ", size: 22 }),
    new TextRun({
      text: "SET LOCAL app.clinica_id = '<uuid>'",
      size: 22,
      font: "Consolas",
    }),
    new TextRun({ text: ".", size: 22 }),
  ]),
  numbered([
    new TextRun({
      text:
        "View executa queries normalmente — Postgres filtra cada linha automaticamente pela policy.",
      size: 22,
    }),
  ]),
  numbered([
    new TextRun({ text: "Transação commita, ", size: 22 }),
    new TextRun({ text: "SET LOCAL", size: 22, font: "Consolas" }),
    new TextRun({
      text: " expira, conexão volta limpa para o pool.",
      size: 22,
    }),
  ]),
  p(
    "A peça-chave é o helper SQL que toda migration de tabela tenant-aware chama:"
  ),
  ...codeBlock(`CREATE OR REPLACE FUNCTION apply_rls_policy(target_table regclass)
RETURNS void LANGUAGE plpgsql AS $fn$
BEGIN
    EXECUTE format('ALTER TABLE %s ENABLE ROW LEVEL SECURITY', target_table);
    EXECUTE format('ALTER TABLE %s FORCE ROW LEVEL SECURITY', target_table);
    EXECUTE format(
        'CREATE POLICY tenant_isolation ON %s '
        'USING (clinica_id = current_setting(''app.clinica_id'')::uuid) '
        'WITH CHECK (clinica_id = current_setting(''app.clinica_id'')::uuid)',
        target_table
    );
    EXECUTE format(
        'GRANT SELECT, INSERT, UPDATE, DELETE ON %s TO app_readwrite, app_jobs',
        target_table
    );
END; $fn$;`),
  blank(),
  pRich([
    code("USING"),
    run(" filtra leitura; "),
    code("WITH CHECK"),
    run(
      " filtra escrita. Toda nova tabela de domínio chama essa função e ganha policy + GRANTs corretos sem reinventar."
    ),
  ]),

  h2("3.3 Defesa em profundidade — 4 camadas"),
  p(
    "Multi-tenant é o tipo de bug em que falha silenciosa é catastrófica (cliente vê dado de outro). Por isso construímos quatro camadas independentes para o mesmo invariante:"
  ),
  numbered([
    new TextRun({ text: "Policy RLS no Postgres ", size: 22, bold: true }),
    new TextRun({
      text:
        "— filtra SELECT/UPDATE/DELETE/INSERT direto no banco. Última verdade.",
      size: 22,
    }),
  ]),
  numbered([
    new TextRun({
      text: "TenantAwareModel.save() ",
      size: 22,
      bold: true,
      font: "Consolas",
    }),
    new TextRun({
      text:
        "— valida no Python que self.clinica_id bate com current_setting('app.clinica_id') da sessão. Pega bug que escapou da camada 1.",
      size: 22,
    }),
  ]),
  numbered([
    new TextRun({
      text: "Role app_readwrite sem BYPASSRLS ",
      size: 22,
      bold: true,
    }),
    new TextRun({
      text:
        '— em produção, Django conecta como esse role; mesmo se o handler esquecer tenant_session(), query retorna 0 rows em vez de vazar (defesa "se eu errar como dev, ninguém se machuca").',
      size: 22,
    }),
  ]),
  numbered([
    new TextRun({
      text: "clinica_id desnormalizado em through-tables ",
      size: 22,
      bold: true,
    }),
    new TextRun({
      text:
        "— MedicoConvenio, MedicoDisponibilidade, Mensagem, Handoff carregam clinica_id próprio (auto-populado do FK pai no save()). Com isso, RLS aplica direto na tabela em vez de depender de JOIN com a tabela pai.",
      size: 22,
    }),
  ]),
];

// === Seção 4 ===
const ondaRows = [
  ["Modelo", "App", "Função no domínio"],
  ["ClinicaCanal", "clinics", "Número/instância WhatsApp por clínica"],
  ["ClinicaPolitica", "clinics", "Pares chave-valor de regras por clínica"],
  ["Paciente", "patients", "Identificado por telefone E.164"],
  ["Especialidade", "catalog", "Cardiologia, Pediatria, etc"],
  [
    "Medico",
    "catalog",
    "CRM unique por clínica + duracao_consulta_min",
  ],
  ["Convenio", "catalog", "Unimed, Bradesco Saúde, etc"],
  ["MedicoConvenio", "catalog", "Through-table com preço"],
  ["MedicoDisponibilidade", "catalog", "Faixas horárias semanais"],
];

const secao4 = [
  h1("4. Modelo de domínio em 4 ondas"),
  pRich([
    run("Foram 15 tabelas no total — 14 tenant-aware e 1 global ("),
    code("clinicas"),
    run(
      "). Construídas em quatro ondas coerentes para que cada commit fosse revisável e contasse uma parte da história no "
    ),
    code("git log"),
    run(":"),
  ]),
  ...image(
    "diagrama-relacoes.png",
    IMG_WIDTH_PX,
    Math.round(IMG_WIDTH_PX / 1.625),
    "Figura 2 — Modelo de domínio em 4 ondas"
  ),

  h2("4.1 Onda 1 — Cadastro (8 tabelas)"),
  tableSimple(ondaRows, [2400, 1500, 5172]),
  blank(),

  h2("4.2 Onda 2 — Agendamento (1 tabela, conceito-chave do schema)"),
  pRich([
    run(
      "A invariante mais forte do produto: dois agendamentos ATIVOS do mesmo médico não podem se sobrepor no tempo. "
    ),
    run("O Postgres garante isso, não a aplicação:", { bold: true }),
  ]),
  ...codeBlock(`CREATE EXTENSION IF NOT EXISTS btree_gist;

ALTER TABLE agendamentos ADD CONSTRAINT agendamento_sem_overlap_por_medico
EXCLUDE USING GIST (
    medico_id WITH =,
    tstzrange(inicio_em, fim_em) WITH &&
) WHERE (status != 'cancelado');`),
  blank(),
  p("Como ler:"),
  bullet(null, [
    new TextRun({
      text: "EXCLUDE USING GIST",
      size: 22,
      font: "Consolas",
    }),
    new TextRun({
      text:
        ' é um tipo de constraint que generaliza UNIQUE: "não permita duas linhas que satisfaçam um operador".',
      size: 22,
    }),
  ]),
  bullet(null, [
    new TextRun({
      text: "medico_id WITH =",
      size: 22,
      font: "Consolas",
    }),
    new TextRun({
      text:
        " exige que sejam o mesmo médico. Para usar = em índice GIST precisa da extension btree_gist — GIST nativo só faz operadores não-equality (range overlap, geometria, full-text).",
      size: 22,
    }),
  ]),
  bullet(null, [
    new TextRun({
      text: "tstzrange(inicio_em, fim_em) WITH &&",
      size: 22,
      font: "Consolas",
    }),
    new TextRun({
      text:
        " constrói um range de timestamps a partir das duas colunas e usa && (overlap).",
      size: 22,
    }),
  ]),
  bullet(null, [
    new TextRun({
      text: "WHERE (status != 'cancelado')",
      size: 22,
      font: "Consolas",
    }),
    new TextRun({
      text:
        ' exclui canceladas — quando paciente desmarca, o slot é liberado de novo. Sem essa cláusula, cancelar "queimaria" o horário.',
      size: 22,
    }),
  ]),
  p(
    'A validação acontece dentro do INSERT/UPDATE como operação atômica. Não há janela de race condition entre "checa agenda" e "insere".'
  ),

  h2("4.3 Onda 3 — Conversação (3 tabelas, idempotência de webhook)"),
  pRich([
    code("Conversa"),
    run(", "),
    code("Mensagem"),
    run(" e "),
    code("Handoff"),
    run(
      ' modelam o "fio" da conversa entre paciente e bot. O conceito-chave é a unique parcial em '
    ),
    code("mensagens"),
    run(":"),
  ]),
  ...codeBlock(`CREATE UNIQUE INDEX msg_canal_external_id_unico_se_presente
ON public.mensagens (canal_id, external_id)
WHERE (external_id IS NOT NULL);`),
  blank(),
  pRich([
    run("Por que parcial? O WhatsApp entrega webhook "),
    run("at-least-once", { bold: true }),
    run(
      " — o provedor reenvia se não receber 200 OK em ~5s. A constraint impede duplicar mensagem. O "
    ),
    code("WHERE"),
    run(" parcial deixa mensagens "),
    run("de saída", { italics: true }),
    run(" locais (que ainda não receberam ID do provedor, ficam com "),
    code("external_id = NULL"),
    run(
      ") coexistirem livremente — caso contrário o bot só conseguiria enfileirar uma resposta por canal."
    ),
  ]),

  h2("4.4 Onda 4 — Envio + log (2 tabelas)"),
  pRich([
    code("Outbox"),
    run(" (em "),
    code("apps.channels"),
    run(
      ") é a fila de envio assíncrono. Em vez de chamar a API do WhatsApp diretamente do request HTTP — o que acoplaria a resposta do paciente à latência (e disponibilidade) do provedor —, gravamos uma linha no "
    ),
    code("Outbox"),
    run(" e uma task Celery ("),
    code("send_outbox"),
    run(
      ") drena depois com retry exponencial. Esse padrão tem nome: "
    ),
    run("outbox pattern", { bold: true }),
    run(" (Hohpe, "),
    run("Enterprise Integration Patterns", { italics: true }),
    run(
      '). Ele resolve o problema de "atomic dual write" — se a conexão com o provedor cai entre INSERT e POST, a outbox preserva o estado.'
    ),
  ]),
  pRich([
    code("EventoBot"),
    run(" (em "),
    code("apps.observability"),
    run(
      ') é log estruturado complementar ao Langfuse. Permite que o painel da clínica mostre "o que aconteceu nessa conversa" sem depender do Langfuse estar online.'
    ),
  ]),
];

// === Seção 5 ===
const secao5 = [
  h1("5. Loop completo do MVP"),
  p(
    "A figura abaixo mostra o caminho completo de uma mensagem WhatsApp recebida até o eco enfileirado:"
  ),
  ...image(
    "loop-webhook.png",
    IMG_WIDTH_PX,
    Math.round(IMG_WIDTH_PX / 1.625),
    "Figura 3 — Loop do webhook entrante até eco enfileirado"
  ),
  pRich([
    run(
      "A coluna esquerda são os passos da request HTTP até o parse do payload. A coluna direita são as ações dentro de "
    ),
    code("tenant_session(canal.clinica_id)"),
    run(" — onde Postgres já está com "),
    code("app.clinica_id"),
    run(" setado, então RLS aplica corretamente."),
  ]),
  pRich([
    run("Trecho resumido do handler em "),
    code("config/api.py"),
    run(":"),
  ]),
  ...codeBlock(`@api.post("/webhooks/whatsapp/{canal_id}")
def webhook_whatsapp(request, canal_id: UUID):
    canal = ClinicaCanal.objects.filter(id=canal_id, ativo=True).first()
    if canal is None:
        return JsonResponse({"erro": "canal_nao_encontrado"}, status=404)

    if not verifica_hmac_sha256(request.body,
                                request.headers.get("X-Hub-Signature-256", ""),
                                canal.webhook_secret):
        return JsonResponse({"erro": "assinatura_invalida"}, status=401)

    parsed = parse_evolution_payload(json.loads(request.body))
    if parsed is None:
        return JsonResponse({"status": "ignorado"}, status=200)

    with tenant_session(canal.clinica_id):
        paciente, _ = Paciente.objects.get_or_create(...)
        conversa = (Conversa.objects.filter(...)
                    .exclude(status=ENCERRADA).first()
                    or Conversa.objects.create(...))

        try:
            with transaction.atomic():  # savepoint pra capturar IntegrityError
                mensagem = Mensagem.objects.create(
                    ..., external_id=parsed["external_id"]
                )
        except IntegrityError:
            return JsonResponse({"status": "duplicado"}, status=200)

        process_inbound_message.apply_async(
            kwargs={"clinica_id": str(canal.clinica_id),
                    "mensagem_id": str(mensagem.id)},
            task_id=parsed["external_id"],
        )

    return JsonResponse({"status": "aceito"}, status=200)`),
  blank(),
  h2("5.1 Idempotência em 3 camadas"),
  p(
    "Como webhook é at-least-once, três linhas defensivas trabalham juntas:"
  ),
  numbered([
    new TextRun({
      text: "Unique parcial em mensagens ",
      size: 22,
      bold: true,
    }),
    new TextRun({
      text:
        "— (canal, external_id) WHERE external_id IS NOT NULL faz INSERT falhar no DB e o handler captura como duplicado. Última verdade, sempre funciona.",
      size: 22,
    }),
  ]),
  numbered([
    new TextRun({
      text: "task_id=external_id no apply_async ",
      size: 22,
      bold: true,
      font: "Consolas",
    }),
    new TextRun({
      text:
        "— Celery descarta retry com mesmo task_id no broker. Evita trabalho duplicado quando a 1ª camada já negou.",
      size: 22,
    }),
  ]),
  numbered([
    new TextRun({
      text: "(Futuro) Provedor confere ack ",
      size: 22,
      bold: true,
    }),
    new TextRun({
      text:
        "— se o WhatsApp já recebeu confirmação para esse external_id, não envia de novo.",
      size: 22,
    }),
  ]),
  p(
    "Cada camada cobre um buraco diferente. Falha em uma — as outras seguram."
  ),
];

// === Seção 6 ===
const secao6 = [
  h1("6. Conceitos técnicos chave (resumo)"),
  p("Cada conceito em um parágrafo curto, para consulta rápida:"),
  pRich([
    run("Row-Level Security (RLS). ", { bold: true }),
    run(
      "Policy SQL do Postgres que filtra linhas baseado numa variável de sessão. Mais forte que filtro no app porque acontece no banco — não dá pra esquecer. Documentação: postgresql.org/docs/current/ddl-rowsecurity.html."
    ),
  ]),
  pRich([
    run("Exclusion constraint com ", { bold: true }),
    code("btree_gist", { bold: true }),
    run(". ", { bold: true }),
    run(
      'Generaliza UNIQUE: "duas linhas não podem ter valores que satisfaçam um operador". Aqui usamos pra "mesmo médico + ranges de tempo sobrepostos = inválido". Substitui lock distribuído entre workers porque a verificação acontece atomicamente no INSERT.'
    ),
  ]),
  pRich([
    run("Unique parcial pra idempotência. ", { bold: true }),
    run("Postgres aceita "),
    code("UNIQUE (...) WHERE <condição>"),
    run(
      ". Útil quando o invariante só vale para um subconjunto das linhas — no nosso caso, só mensagens já confirmadas pelo provedor ("
    ),
    code("external_id IS NOT NULL"),
    run(")."),
  ]),
  pRich([
    run("Outbox pattern. ", { bold: true }),
    run(
      "Em vez de chamar API externa direto do request, escreve linha no DB e deixa worker async drenar. Sobrevive a crash entre os dois passos. Combinado com idempotência do consumidor (provider dedupa por "
    ),
    code("external_id"),
    run("), vira at-least-once end-to-end."),
  ]),
  pRich([
    run("Defesa em profundidade. ", { bold: true }),
    run(
      "Múltiplas camadas independentes para o mesmo invariante — RLS + save() validation + role sem BYPASSRLS + clinica_id desnormalizado. Se uma falha, as outras seguram."
    ),
  ]),
  pRich([
    run("Health check com severidade. ", { bold: true }),
    run("Endpoints "),
    code("/api/ready"),
    run(" (só Postgres) e "),
    code("/api/health"),
    run(
      " (Postgres + Redis + Celery). Retornam 200 ok ou 503 degraded com diagnóstico granular por dependência. Padrão Kubernetes (readiness vs liveness probes)."
    ),
  ]),
  pRich([
    run("Migrations testáveis. ", { bold: true }),
    run(
      "Toda migration roda contra Postgres real (não SQLite mock). Nunca squash, nunca editar uma já aplicada — gerar nova. Postgres é diferente de mock o suficiente que mocking esconde bugs."
    ),
  ]),
  pRich([
    run("Celery autodiscover + ", { bold: true }),
    code("@shared_task", { bold: true }),
    run(". ", { bold: true }),
    run("A "),
    code('app = Celery("medchat")'),
    run(" é definida em "),
    code("config/celery.py"),
    run(" e chama "),
    code("app.autodiscover_tasks()"),
    run(". Cada "),
    code("apps/<app>/tasks.py"),
    run(" é encontrado automaticamente; "),
    code("@shared_task"),
    run(" (em vez de "),
    code("@app.task"),
    run(
      ') registra a task em qualquer Celery app que estiver "current" — evita import circular.'
    ),
  ]),
];

// === Seção 7 ===
const metricasRows = [
  ["Métrica", "Valor"],
  [
    "Commits narrativos",
    "18 (formato O quê / Por quê / Conceito / Próximo passo)",
  ],
  ["Apps Django", "9 (8 com modelos, 1 reservado pra Fase 2)"],
  ["Tabelas tenant-aware", "14 (+ 1 global = 15 no total)"],
  ["Migrations versionadas", "12"],
  [
    "Testes verdes",
    "53 (40 RLS + 3 Celery + 5 API + 5 Webhook)",
  ],
  ["Tempo de execução dos testes", "~18 segundos contra Postgres real"],
  [
    "Containers Docker UP",
    "7/7 (postgres, redis, langfuse-db, langfuse, web, worker, beat)",
  ],
  [
    "Endpoints HTTP funcionais",
    "3 (/api/ready, /api/health, /api/webhooks/whatsapp/{canal_id})",
  ],
  [
    "Tasks Celery registradas",
    "2 (process_inbound_message, send_outbox)",
  ],
];

const secao7 = [h1("7. Métricas finais"), tableSimple(metricasRows, [3500, 5572])];

// === Seção 8 ===
const secao8 = [
  h1("8. O que vem a seguir"),
  p("Quatro frentes em ordem de prioridade:"),
  numbered([
    new TextRun({
      text: "Item 10 — EvolutionProvider real. ",
      size: 22,
      bold: true,
    }),
    new TextRun({
      text:
        "HTTP client (httpx) que substitui o stub _entrega_via_provider_stub em send_outbox. Atualiza Mensagem.external_id quando o provedor retorna o ID, fechando o ciclo de envio. Inclui também o parser real do payload Evolution (substitui o parse_evolution_payload mínimo de hoje).",
      size: 22,
    }),
  ]),
  numbered([
    new TextRun({
      text: "Item 11 — Langfuse client + primeiro trace. ",
      size: 22,
      bold: true,
    }),
    new TextRun({
      text:
        "Validar end-to-end que o trace de webhook → eco aparece no UI Langfuse local (já está rodando em http://localhost:3000).",
      size: 22,
    }),
  ]),
  numbered([
    new TextRun({
      text: "Hardening de role no banco. ",
      size: 22,
      bold: true,
    }),
    new TextRun({
      text:
        "Em produção, trocar DATABASE_URL para conectar como app_readwrite (sem BYPASSRLS). Hoje a aplicação conecta como o owner SUPERUSER medchat em dev — RLS só aplica de verdade nos testes via SET LOCAL ROLE. Sem essa troca, a camada 3 da defesa em profundidade não está ativa em runtime.",
      size: 22,
    }),
  ]),
  numbered([
    new TextRun({
      text: "ADRs faltantes. ",
      size: 22,
      bold: true,
    }),
    new TextRun({
      text:
        "Escrever docs/adr/0001-django-vs-n8n.md e docs/adr/0003-anthropic-openrouter.md para fechar o trio fundacional de decisões arquiteturais documentadas.",
      size: 22,
    }),
  ]),
  p(
    "Concluído isso, a Fase 1 fecha por completo e a Fase 2 (LLM real, prompt caching, Anthropic SDK + tool use para agendamento) pode começar em terreno sólido."
  ),
];

// ---------------------------------------------------------------------------
// Document
// ---------------------------------------------------------------------------
const doc = new Document({
  creator: "Claude (anthropic-skills:docx)",
  title: "MedChat — Relatório técnico da Fase 1",
  description: "Fundação Django: multi-tenant, modelo de domínio e loop do MVP",
  styles: {
    default: {
      document: { run: { font: "Calibri", size: 22 } },
    },
    paragraphStyles: [
      {
        id: "Heading1",
        name: "Heading 1",
        basedOn: "Normal",
        next: "Normal",
        quickFormat: true,
        run: { size: 36, bold: true, font: "Calibri", color: "1F6FEB" },
        paragraph: {
          spacing: { before: 400, after: 200 },
          outlineLevel: 0,
        },
      },
      {
        id: "Heading2",
        name: "Heading 2",
        basedOn: "Normal",
        next: "Normal",
        quickFormat: true,
        run: { size: 28, bold: true, font: "Calibri", color: "24292F" },
        paragraph: {
          spacing: { before: 300, after: 160 },
          outlineLevel: 1,
        },
      },
    ],
  },
  numbering: {
    config: [
      {
        reference: "bullets",
        levels: [
          {
            level: 0,
            format: LevelFormat.BULLET,
            text: "•",
            alignment: AlignmentType.LEFT,
            style: { paragraph: { indent: { left: 720, hanging: 360 } } },
          },
        ],
      },
      {
        reference: "numbers",
        levels: [
          {
            level: 0,
            format: LevelFormat.DECIMAL,
            text: "%1.",
            alignment: AlignmentType.LEFT,
            style: { paragraph: { indent: { left: 720, hanging: 360 } } },
          },
        ],
      },
    ],
  },
  sections: [
    {
      properties: {
        page: {
          size: { width: PAGE_WIDTH, height: PAGE_HEIGHT },
          margin: {
            top: MARGIN,
            right: MARGIN,
            bottom: MARGIN,
            left: MARGIN,
          },
        },
      },
      children: [
        ...capa,
        ...sumario,
        ...secao1,
        ...secao2,
        ...secao3,
        ...secao4,
        ...secao5,
        ...secao6,
        ...secao7,
        ...secao8,
      ],
    },
  ],
});

Packer.toBuffer(doc).then((buffer) => {
  fs.writeFileSync(OUTPUT, buffer);
  const stats = fs.statSync(OUTPUT);
  console.log(`Gerado: ${path.relative(ROOT, OUTPUT)}`);
  console.log(`Tamanho: ${(stats.size / 1024).toFixed(1)} KB`);
});
