---
name: aprendizados-readme
type: aprendizado
tags: [readme]
---

# Aprendizados — Convenção da pasta

Notas de descobertas evolutivas. **Diferente de `conceitos-ai/`** (que descreve um conceito genérico) e de **`decisoes/`** (que registra escolha entre opções).

Aprendizado é: *"trabalhando no MedChat eu descobri que **X** se comporta de jeito **Y** quando **Z** — não estava no manual"*.

## Quando criar uma nota aqui

- Bug que ensinou algo sobre o produto.
- Comportamento de SDK/lib que documentação não cobre direito.
- Conexão entre duas partes do sistema que não era óbvia.
- Hipótese que virou regra ou que foi refutada.

## Quando NÃO criar

- Coisa que está no `conceitos-ai/` (genérico, não específico).
- Status do dia ("rodei pytest e passou").
- Refactor trivial.
- Reformulação de info já presente sem novo insight.

## Formato

Use [`vault/_templates/aprendizado.md`](../_templates/aprendizado.md). Status sempre marcado:

- **Hipótese**: ainda não confirmamos sob carga real / em produção.
- **Confirmado**: vimos no comportamento do sistema.
- **Refutado**: era falso. Manter pra registro — evita repetir o mesmo erro.

## Exemplo curto (formato)

```markdown
---
name: rls-bypass-em-celery
type: aprendizado
tags: [rls, celery]
---

# Aprendizado: tasks Celery precisam setar `app.clinica_id` explicitamente

## O que descobrimos
Sem o `RLSMiddleware` (que só roda em request HTTP), tasks Celery não têm
`app.clinica_id` setado por default. `TenantAwareModel.save()` aborta.

## Status
Hipótese — confirmar quando a primeira task tenant-aware aparecer.
```

(Este exemplo é fictício — quando virar real, criar arquivo separado e linkar aqui.)
