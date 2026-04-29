"""Gera as 3 figuras PNG embutidas no relatório `medchat-fase-1.docx`.

Uso:
    uv run python docs/relatorios/_gerar_assets.py

Saída: três arquivos em `docs/relatorios/_assets/`:
- `fluxo-rls.png` — request HTTP passando pelo `RLSMiddleware`.
- `diagrama-relacoes.png` — modelo de domínio (15 tabelas).
- `loop-webhook.png` — webhook → eco → outbox.

Sem dependência de internet (matplotlib local). Imagens em PNG
1600×900 (16:9) — encaixam bem em página A4 retrato.
"""

from __future__ import annotations

from pathlib import Path

import matplotlib.pyplot as plt
from matplotlib.patches import FancyArrowPatch, FancyBboxPatch

ASSETS_DIR = Path(__file__).parent / "_assets"
ASSETS_DIR.mkdir(exist_ok=True)

# Paleta sóbria, alto contraste, amigável pra impressão B&W.
COR_DESTAQUE = "#1f6feb"
COR_NEUTRO = "#24292f"
COR_FUNDO = "#f6f8fa"
COR_PERIGO = "#cf222e"
COR_SUCESSO = "#1a7f37"


def _caixa(ax, x, y, largura, altura, texto, fundo=COR_FUNDO, borda=COR_NEUTRO, bold=False):
    """Desenha uma caixa retangular arredondada com texto centrado."""
    box = FancyBboxPatch(
        (x, y),
        largura,
        altura,
        boxstyle="round,pad=0.04,rounding_size=0.12",
        facecolor=fundo,
        edgecolor=borda,
        linewidth=1.5,
    )
    ax.add_patch(box)
    ax.text(
        x + largura / 2,
        y + altura / 2,
        texto,
        ha="center",
        va="center",
        fontsize=10,
        fontweight="bold" if bold else "normal",
        color=COR_NEUTRO,
        wrap=True,
    )


def _seta(ax, x1, y1, x2, y2, label=None, cor=COR_NEUTRO):
    """Seta direcionada de (x1,y1) a (x2,y2) com label opcional."""
    ax.add_patch(
        FancyArrowPatch(
            (x1, y1),
            (x2, y2),
            arrowstyle="-|>",
            mutation_scale=18,
            color=cor,
            linewidth=1.4,
        )
    )
    if label:
        mx, my = (x1 + x2) / 2, (y1 + y2) / 2
        ax.text(
            mx,
            my + 0.15,
            label,
            ha="center",
            va="center",
            fontsize=8,
            style="italic",
            color=cor,
            bbox=dict(facecolor="white", edgecolor="none", pad=2),
        )


def _setup_axes(ax, xlim, ylim):
    ax.set_xlim(*xlim)
    ax.set_ylim(*ylim)
    ax.set_aspect("equal")
    ax.axis("off")


def _save(fig, nome):
    out = ASSETS_DIR / nome
    fig.savefig(out, dpi=180, bbox_inches="tight", facecolor="white")
    plt.close(fig)
    print(f"  -> {out.relative_to(Path.cwd())}")


# ---------------------------------------------------------------------------
# FIGURA 1 — Fluxo de uma request HTTP passando pelo RLSMiddleware.
# ---------------------------------------------------------------------------


def gerar_fluxo_rls():
    fig, ax = plt.subplots(figsize=(13, 6))
    _setup_axes(ax, (0, 13), (0, 6))

    ax.text(
        6.5,
        5.7,
        "Fluxo de uma request HTTP através do RLSMiddleware",
        ha="center",
        fontsize=13,
        fontweight="bold",
        color=COR_NEUTRO,
    )

    # 5 passos em linha horizontal
    passos = [
        (0.3, "1. Request\nX-Clinic-Slug: clinica-x"),
        (2.9, "2. RLSMiddleware\nresolve slug → UUID"),
        (5.5, "3. SET LOCAL\napp.clinica_id = '<uuid>'\n(transaction.atomic)"),
        (8.1, "4. View executa queries\nPostgres filtra automaticamente\nvia policy RLS"),
        (10.7, "5. Transação commita\nSET LOCAL expira\nconexão volta ao pool"),
    ]
    for x, texto in passos:
        _caixa(ax, x, 2.6, 2.3, 1.6, texto, fundo=COR_FUNDO)

    # Setas entre passos
    for i in range(len(passos) - 1):
        x1 = passos[i][0] + 2.3
        x2 = passos[i + 1][0]
        _seta(ax, x1, 3.4, x2, 3.4)

    # Barra inferior: estado da sessão Postgres
    _caixa(
        ax,
        0.3,
        0.6,
        2.3,
        1.2,
        "app.clinica_id\n= (vazio)",
        fundo="#fff5d4",
        borda="#bf8700",
    )
    _caixa(
        ax,
        2.9,
        0.6,
        2.3,
        1.2,
        "app.clinica_id\n= (vazio)",
        fundo="#fff5d4",
        borda="#bf8700",
    )
    _caixa(
        ax,
        5.5,
        0.6,
        2.3,
        1.2,
        "app.clinica_id\n= '7f3a-…'",
        fundo="#dafbe1",
        borda=COR_SUCESSO,
    )
    _caixa(
        ax,
        8.1,
        0.6,
        2.3,
        1.2,
        "app.clinica_id\n= '7f3a-…'",
        fundo="#dafbe1",
        borda=COR_SUCESSO,
    )
    _caixa(
        ax,
        10.7,
        0.6,
        2.3,
        1.2,
        "app.clinica_id\n= (vazio)",
        fundo="#fff5d4",
        borda="#bf8700",
    )

    ax.text(
        6.5,
        0.1,
        "Estado de current_setting('app.clinica_id') na conexão Postgres em cada passo",
        ha="center",
        fontsize=9,
        style="italic",
        color=COR_NEUTRO,
    )

    _save(fig, "fluxo-rls.png")


# ---------------------------------------------------------------------------
# FIGURA 2 — Diagrama de relações simplificado entre as 15 tabelas.
# ---------------------------------------------------------------------------


def gerar_diagrama_relacoes():
    fig, ax = plt.subplots(figsize=(13, 8))
    _setup_axes(ax, (0, 13), (0, 9))

    ax.text(
        6.5,
        8.5,
        "Modelo de domínio — 15 tabelas em 4 ondas",
        ha="center",
        fontsize=13,
        fontweight="bold",
        color=COR_NEUTRO,
    )

    # CLINICA no centro topo
    _caixa(ax, 5.5, 7.0, 2.0, 0.8, "Clinica\n(global)", fundo="#dafbe1", borda=COR_SUCESSO, bold=True)

    # Onda 1 — extensões da clínica + cadastro
    _caixa(ax, 0.3, 5.6, 2.0, 0.7, "ClinicaCanal", fundo=COR_FUNDO)
    _caixa(ax, 0.3, 4.6, 2.0, 0.7, "ClinicaPolitica", fundo=COR_FUNDO)
    _caixa(ax, 11.0, 5.6, 1.8, 0.7, "Especialidade", fundo=COR_FUNDO)
    _caixa(ax, 11.0, 4.6, 1.8, 0.7, "Convenio", fundo=COR_FUNDO)

    # Paciente (centro esquerdo)
    _caixa(ax, 2.7, 5.6, 1.7, 0.7, "Paciente", fundo="#ddf4ff", borda=COR_DESTAQUE, bold=True)

    # Medico (centro direito)
    _caixa(ax, 8.7, 5.6, 1.7, 0.7, "Medico", fundo="#ddf4ff", borda=COR_DESTAQUE, bold=True)

    # Through tables (Medico × Convenio, Medico × Disponibilidade)
    _caixa(ax, 8.7, 4.0, 1.7, 0.6, "MedicoConvenio", fundo=COR_FUNDO)
    _caixa(ax, 8.7, 3.2, 1.7, 0.6, "MedicoDisponib.", fundo=COR_FUNDO)

    # Onda 2 — Agendamento (centro)
    _caixa(
        ax,
        5.3,
        4.4,
        2.4,
        0.9,
        "Agendamento\n(EXCLUDE GIST anti-overlap)",
        fundo="#fff5d4",
        borda="#bf8700",
        bold=True,
    )

    # Onda 3 — Conversação
    _caixa(ax, 2.7, 3.2, 1.7, 0.7, "Conversa", fundo="#ddf4ff")
    _caixa(
        ax,
        2.7,
        2.0,
        1.7,
        0.7,
        "Mensagem\n(unique parcial)",
        fundo="#ddf4ff",
        borda=COR_DESTAQUE,
    )
    _caixa(ax, 0.3, 2.0, 2.0, 0.7, "Handoff", fundo="#ddf4ff")

    # Onda 4 — Outbox + EventoBot
    _caixa(
        ax,
        2.7,
        0.6,
        2.0,
        0.7,
        "Outbox\n(envio assíncrono)",
        fundo="#fff5d4",
        borda="#bf8700",
    )
    _caixa(ax, 5.3, 0.6, 2.0, 0.7, "EventoBot\n(log local)", fundo=COR_FUNDO)

    # Setas (cardinalidades simbolizadas pela direção; rotuladas onde importa)
    # Tudo aponta indiretamente pra Clinica via FK clinica_id, mas pra não
    # poluir o diagrama mostramos só algumas chave:
    _seta(ax, 1.3, 6.3, 5.5, 7.0)  # ClinicaCanal → Clinica
    _seta(ax, 3.55, 6.3, 5.7, 7.0)  # Paciente → Clinica
    _seta(ax, 9.55, 6.3, 7.5, 7.0)  # Medico → Clinica
    _seta(ax, 11.9, 6.3, 7.5, 7.0)  # Especialidade → Clinica

    # Medico → Especialidade (FK opcional)
    _seta(ax, 10.4, 5.95, 11.0, 5.95)
    # Medico → MedicoConvenio (1:N) e Convenio → MedicoConvenio
    _seta(ax, 9.55, 5.6, 9.55, 4.6)
    _seta(ax, 11.9, 4.95, 10.4, 4.3)
    # Medico → Disponibilidade
    _seta(ax, 9.55, 5.6, 9.55, 3.8)

    # Agendamento ← Paciente (1:N) e ← Medico
    _seta(ax, 4.4, 5.95, 5.3, 5.0)
    _seta(ax, 8.7, 5.95, 7.7, 5.0)

    # Paciente → Conversa
    _seta(ax, 3.55, 5.6, 3.55, 3.9, label="1:N")
    # Conversa → Mensagem
    _seta(ax, 3.55, 3.2, 3.55, 2.7, label="1:N")
    # Conversa → Handoff
    _seta(ax, 2.7, 3.55, 2.3, 2.7)

    # Mensagem → Outbox (referência via payload, não FK direta)
    _seta(ax, 3.55, 2.0, 3.55, 1.3, label="ref")
    # Conversa → EventoBot (FK opcional, SET_NULL)
    _seta(ax, 4.4, 3.55, 6.0, 1.3)

    # Legenda
    legenda_y = 8.0
    _caixa(ax, 0.3, legenda_y, 1.4, 0.4, "Onda 1", fundo="#f6f8fa", borda=COR_NEUTRO)
    _caixa(ax, 1.85, legenda_y, 1.4, 0.4, "Onda 2", fundo="#fff5d4", borda="#bf8700")
    _caixa(ax, 3.4, legenda_y, 1.4, 0.4, "Onda 3", fundo="#ddf4ff", borda=COR_DESTAQUE)
    _caixa(ax, 4.95, legenda_y, 1.4, 0.4, "Onda 4", fundo="#fff5d4", borda="#bf8700")
    _caixa(ax, 6.5, legenda_y, 1.4, 0.4, "Global", fundo="#dafbe1", borda=COR_SUCESSO)

    _save(fig, "diagrama-relacoes.png")


# ---------------------------------------------------------------------------
# FIGURA 3 — Loop completo do MVP (webhook → eco → outbox).
# ---------------------------------------------------------------------------


def gerar_loop_webhook():
    fig, ax = plt.subplots(figsize=(13, 8))
    _setup_axes(ax, (0, 13), (0, 9))

    ax.text(
        6.5,
        8.5,
        "Loop completo do MVP — webhook entrante até eco enfileirado",
        ha="center",
        fontsize=13,
        fontweight="bold",
        color=COR_NEUTRO,
    )

    # Coluna esquerda: 5 passos da request HTTP
    passos_esq = [
        (7.4, "1. WhatsApp envia\nPOST /api/webhooks/whatsapp/{canal_id}\n+ X-Hub-Signature-256"),
        (6.0, "2. RLSMiddleware libera\n('/api/webhooks/' é PUBLIC)"),
        (4.6, "3. Handler resolve\nClinicaCanal por canal_id\n(404 se não existe)"),
        (3.2, "4. Verifica HMAC-SHA256\ncom canal.webhook_secret\n(401 se inválido)"),
        (1.8, "5. Parse Evolution payload\n→ external_id, from_e164, body\n(200 'ignorado' se sem texto)"),
    ]
    for y, texto in passos_esq:
        _caixa(ax, 0.3, y, 4.5, 1.0, texto, fundo=COR_FUNDO)

    # Setas verticais entre passos
    for i in range(len(passos_esq) - 1):
        y1 = passos_esq[i][0]
        y2 = passos_esq[i + 1][0] + 1.0
        _seta(ax, 2.55, y1, 2.55, y2)

    # Coluna direita: passos pós-validação (dentro de tenant_session)
    passos_dir = [
        (7.4, "6. tenant_session(canal.clinica_id)\nabre transação + SET LOCAL"),
        (6.0, "7. get_or_create\nPaciente + Conversa"),
        (4.6, "8. INSERT Mensagem (entrada)\n(IntegrityError = duplicado)"),
        (3.2, "9. apply_async eco\ntask_id=external_id\n(idempotência via Celery)"),
        (1.8, "10. Eco MVP roda\n(em modo eager, inline)\n→ Mensagem saída + Outbox"),
    ]
    for y, texto in passos_dir:
        _caixa(ax, 8.2, y, 4.5, 1.0, texto, fundo="#ddf4ff", borda=COR_DESTAQUE)

    for i in range(len(passos_dir) - 1):
        y1 = passos_dir[i][0]
        y2 = passos_dir[i + 1][0] + 1.0
        _seta(ax, 10.45, y1, 10.45, y2)

    # Seta horizontal: ponte entre coluna esquerda (passo 5) e direita (passo 6)
    _seta(ax, 4.8, 2.3, 8.2, 7.9, label="parsed OK → entra na sessão")

    # Resposta no rodapé
    _caixa(
        ax,
        4.5,
        0.4,
        4.0,
        0.7,
        "← 200 OK\n{ status: 'aceito', mensagem_id: ... }",
        fundo="#dafbe1",
        borda=COR_SUCESSO,
        bold=True,
    )
    _seta(ax, 8.2, 1.5, 6.5, 1.1)

    _save(fig, "loop-webhook.png")


# ---------------------------------------------------------------------------
# Entry point
# ---------------------------------------------------------------------------


def main():
    print(f"Gerando figuras em {ASSETS_DIR.relative_to(Path.cwd())}/")
    gerar_fluxo_rls()
    gerar_diagrama_relacoes()
    gerar_loop_webhook()
    print("OK — 3 figuras geradas.")


if __name__ == "__main__":
    main()
