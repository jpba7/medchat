---
name: clinica-id-desnormalizado-vs-fk
type: decisao
tags: [rls, multi-tenant, defesa-em-profundidade, schema]
---

# Decisão: desnormalizar `clinica_id` em through-tables vs herdar via FK

> Tabelas como `MedicoConvenio`, `MedicoDisponibilidade`, `Mensagem`, `Handoff` e `EventoBot` poderiam **não ter** `clinica_id` — o tenant é derivável via JOIN com a entidade pai. Decidimos colocar `clinica_id` mesmo assim e proteger cada tabela com sua própria policy RLS.

**Data:** 2026-04-28

## Contexto

Quando criamos `MedicoConvenio` (through table entre `Medico` e `Convenio`), surgiu a pergunta: a tabela precisa de `clinica_id` próprio? Tenant é derivável de `medico.clinica_id`. Mesmo dilema apareceu depois em `MedicoDisponibilidade`, `Mensagem`, `Handoff`, `EventoBot`.

## Opções consideradas

### Caminho A: desnormalizar `clinica_id` + RLS própria

```python
class MedicoConvenio(TenantAwareModel):  # herda clinica_id, save() valida
    medico = FK(Medico, on_delete=CASCADE)
    convenio = FK(Convenio, on_delete=CASCADE)
    preco_consulta_centavos = IntegerField(null=True)

    def save(self, *args, **kwargs):
        # Auto-popula clinica_id do FK pai antes do save
        if not self.clinica_id and self.medico_id:
            self.clinica_id = self.medico.clinica_id
        super().save(*args, **kwargs)
```

Tabela tem coluna `clinica_id UUID` própria + policy RLS roda em CADA query. Migration aplica `apply_rls_policy('medico_convenios')`.

Custo: +16 bytes/row (UUID).

### Caminho B: herdar via FK (sem `clinica_id` próprio)

```python
class MedicoConvenio(models.Model):  # NÃO herda TenantAwareModel
    medico = FK(Medico, on_delete=CASCADE)
    convenio = FK(Convenio, on_delete=CASCADE)
    preco_consulta_centavos = IntegerField(null=True)
```

Tabela sem `clinica_id`, sem RLS. Confia que `Medico` e `Convenio` já estão sob RLS — então `SELECT mc.* FROM medico_convenios mc JOIN medicos m ON m.id = mc.medico_id` filtra por tenant via JOIN (porque `medicos` rejeita rows de outros tenants).

Custo: 0 storage extra.

## Cenário concreto que diferencia

Imagine uma rota `/api/admin/precos` listando preços de consulta. Bug clássico: dev escreve

```python
def listar_precos(request):
    return MedicoConvenio.objects.values('medico_id', 'preco_consulta_centavos')
```

E **esquece** de aplicar `RLSMiddleware` (rota foi listada como `PUBLIC_PATH_PREFIXES` por engano), ou a rota é chamada de uma Celery task **sem** `@with_tenant`.

- **Caminho A:** query falha. `app.clinica_id` não setado → policy não consegue avaliar `clinica_id = current_setting(...)` → Postgres retorna `0 rows` (ou erro, dependendo da config). Vazamento **impossível**.
- **Caminho B:** query retorna **TODOS os preços de TODAS as clínicas misturados.** Sem RLS na tabela, sem JOIN explícito, vaza tudo. Segurança depende do dev sempre lembrar do JOIN — confiança frágil.

## Decisão

Escolhemos **Caminho A** (desnormalizar + RLS própria) para todas as through-tables e tabelas filhas que dependem de outra tenant-owned: `MedicoConvenio`, `MedicoDisponibilidade`, `Mensagem`, `Handoff`, `EventoBot`.

**Motivo principal: defesa em profundidade.** Cada tabela se protege. Não confiamos que toda query futura vai lembrar do JOIN explícito ou que toda rota vai aplicar middleware corretamente.

| Aspecto | Caminho A (escolhido) | Caminho B (rejeitado) |
|---|---|---|
| Segurança | Cada tabela se protege independentemente | Confia que ninguém esquece o JOIN |
| Custo storage | +16 bytes/row (UUID) — irrelevante | 0 |
| Manutenção | `save()` popula `clinica_id` do FK pai automaticamente | Nada extra |
| Recuperação de erro humano | Sistema falha fechado | Sistema falha aberto (vaza) |

## Consequências

- `MedicoConvenio.save()` e similares têm 2 linhas de boilerplate pra auto-popular `clinica_id` antes do `super().save()` rodar (que valida contra `app.clinica_id` da sessão).
- `clean()` valida cross-tenant: por exemplo, se `medico` e `convenio` forem de clínicas diferentes, aborta antes do INSERT. Camada 3 da defesa (camada 1: RLS no banco; camada 2: `TenantAwareModel.save()` valida `app.clinica_id`).
- Cada tabela tem sua migration `apply_rls_policy(<tabela>)`.
- `clinica_id` redundante: dado já vem do FK. Trade-off aceito porque o ganho de segurança supera o custo trivial de armazenamento.

## Quando revisitar

- Se aparecer view materializada / tabela analítica que **deliberadamente** quer cross-tenant aggregate (ex.: dashboard interno de uso por clínica). Aí a tabela analítica não tem `clinica_id`, role usa BYPASSRLS, e fica documentado.
- Se descobrirmos custo de storage + index sendo perceptível em escala (improvável a curto prazo).

## Notas relacionadas

- [[../entidades/catalog]] — `MedicoConvenio` e `MedicoDisponibilidade` aplicam essa decisão
- [[../entidades/conversations]] — `Mensagem` e `Handoff` aplicam essa decisão
- [[../entidades/outbox]] — `EventoBot` aplica essa decisão
- [[../aprendizados/medchat-superuser-bypassrls]] — defesa em profundidade ainda mais importante porque RLS é silenciada com SUPERUSER
- [[../../docs/adr/0002-rls-vs-schema]] — decisão arquitetural macro de RLS vs schema-per-tenant
