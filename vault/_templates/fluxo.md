---
name: template-fluxo
type: fluxo
tags: []
---

# Fluxo: {Nome}

> Frase única: o que esse fluxo entrega pro paciente / pra clínica.

## Disparado por

- {ex.: paciente manda mensagem nova}
- {ex.: Celery Beat dispara X horas antes da consulta}

## Estados / etapas

1. **{estado 1}** — {o que acontece}
2. **{estado 2}** — {o que acontece}
3. **{estado terminal}** — {o que acontece}

## Decisões pelo bot vs handoff humano

- O bot resolve sozinho quando: {condições}
- Escala pra humano quando: {condições}

## Entidades envolvidas

- `[[entidades/<entidade1>]]`
- `[[entidades/<entidade2>]]`

## Integrações envolvidas

- `[[integracoes/<integracao1>]]`

## Conceitos AI usados

- `[[conceitos-ai/<conceito1>]]`

## Políticas configuráveis (`ClinicaPolitica`)

- `<chave>` — {o que essa política controla nesse fluxo}

## Gotchas / edge cases

- {caso difícil}: {como tratar}

## Próximos passos

- {o que falta implementar}
