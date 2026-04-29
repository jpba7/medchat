# MOC — Map of Content

Índice navegável do vault. Atualize aqui sempre que adicionar/renomear/remover uma nota.

## Entidades do domínio

- [[entidades/clinica]] — `Clinica` raiz tenant + `ClinicaCanal` + `ClinicaPolitica`
- [[entidades/paciente]] — entidade central do bot, identificada por E.164
- [[entidades/catalog]] — `Especialidade`, `Medico`, `Convenio`, `MedicoConvenio`, `MedicoDisponibilidade`
- [[entidades/agendamento]] — consulta marcada com anti-overlap atômico
- [[entidades/conversations]] — `Conversa`, `Mensagem`, `Handoff`
- [[entidades/outbox]] — `Outbox` (envio) e `EventoBot` (log operacional)

## Conceitos AI / arquitetura

- [[conceitos-ai/anthropic-sdk]] — provedor LLM principal, modelos por caso de uso
- [[conceitos-ai/exclude-using-gist]] — `EXCLUDE USING GIST` anti-overlap de agendamento
- [[conceitos-ai/outbox-pattern]] — desacopla request HTTP de chamada externa
- [[conceitos-ai/idempotencia-via-unique-parcial]] — dedup de webhook no banco

## Integrações

- [[integracoes/evolution-api]] — canal WhatsApp do MVP, config por clínica

## Fluxos de conversação

- [[fluxos/agendar-consulta]] — fluxo principal do produto (com nomes reais após Item 7 da Fase 1)

## Decisões

- [[decisoes/INDEX]] — link pra `docs/adr/` + decisões menores
- [[decisoes/clinica-id-desnormalizado-vs-fk]] — defesa em profundidade nas through-tables

## Aprendizados

- [[aprendizados/README]] — convenção da pasta + exemplo
- [[aprendizados/snapshotter-overlayfs-corrompido]] — `wsl --shutdown` brusco corrompe storage Docker
- [[aprendizados/medchat-superuser-bypassrls]] — user `medchat` é SUPERUSER, RLS é silenciada
- [[aprendizados/grant-faltava-na-migration]] — roles RLS sem GRANT, fix em `core/0002`

## Diário

- [[diario/2026-04-28]] — criação do vault
- [[diario/2026-04-29]] — captura retroativa da sessão `d2e519b2` (12 commits do Item 7)

---

## Como navegar

- **Por entidade**: começa em `entidades/<nome>` — cada nota linka pra integrações, fluxos e conceitos AI relacionados.
- **Por fluxo de conversação**: começa em `fluxos/<nome>` — cada fluxo linka pras entidades e integrações que toca.
- **Por dúvida pontual**: `Grep` direto no vault pelo termo.

## Convenção de links

Use `[[path/sem/extensao]]` (estilo Obsidian wiki-link). Exemplos:

- `[[entidades/clinica]]` em vez de `[entidades/clinica.md](entidades/clinica.md)`.
- `[[../docs/adr/0002-rls-vs-schema]]` pra linkar fora do vault.

Para linkar arquivos fora do vault que não vão abrir no Obsidian, use markdown link normal: `[apps/clinics/models.py](../apps/clinics/models.py)`.
