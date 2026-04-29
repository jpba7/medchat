# MOC — Map of Content

Índice navegável do vault. Atualize aqui sempre que adicionar/renomear/remover uma nota.

## Entidades do domínio

- [[entidades/clinica]] — `Clinica` raiz tenant + `ClinicaCanal` + `ClinicaPolitica`

## Conceitos AI

- [[conceitos-ai/anthropic-sdk]] — provedor LLM principal, modelos por caso de uso

## Integrações

- [[integracoes/evolution-api]] — canal WhatsApp do MVP, config por clínica

## Fluxos de conversação

- [[fluxos/agendar-consulta]] — fluxo principal do produto (skeleton)

## Decisões

- [[decisoes/INDEX]] — link pra `docs/adr/` + decisões menores

## Aprendizados

- [[aprendizados/README]] — convenção da pasta + exemplo

## Diário

- [[diario/2026-04-28]] — criação do vault

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
