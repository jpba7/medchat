---
title: grant-faltava-na-migration
type: aprendizado
tags: [rls, postgres, migration, grant]
---

# Aprendizado: roles RLS existiam mas não tinham `GRANT` — testes de isolation falhavam silenciosamente

> Postgres aceita `SET LOCAL ROLE <role>` mesmo se esse role não tem permissão pra ler nada. A query que vem depois falha por **falta de privilégio**, não por **RLS**. Sintoma confunde — parece que RLS tá quebrada quando na verdade falta GRANT.

## O que descobrimos

Migration `core/0001_rls_setup` (commit `46caf61`) criou os roles `app_readwrite` e `app_jobs`:

```sql
CREATE ROLE app_readwrite NOLOGIN;
CREATE ROLE app_jobs NOLOGIN;
```

Comentário da migration dizia "produção via `ALTER ROLE`" — assumindo que o GRANT seria feito por fora.

Mas em **dev**, esses roles nasciam sem GRANT em nenhuma tabela. Quando os testes RLS começaram a usar `SET LOCAL ROLE app_readwrite` pra exercer a policy de verdade, qualquer `SELECT` retornava `permission denied for table <X>` — não 0 rows como esperado.

## Como descobrimos

Tentando rodar o primeiro teste de isolation cross-tenant (parte de `tests/integration/test_rls.py`):

```python
def test_clinica_a_nao_ve_paciente_da_clinica_b(self, ...):
    with connection.cursor() as cur:
        cur.execute("SET LOCAL ROLE app_readwrite")
        cur.execute("SET LOCAL app.clinica_id = %s", [str(clinica_a.id)])
        cur.execute("SELECT count(*) FROM pacientes")
        # Esperado: count = N (só pacientes da clinica_a)
        # Real: psycopg2.errors.InsufficientPrivilege: permission denied for table pacientes
```

O fato é que `app_readwrite` não tinha GRANT. A policy RLS nunca chegou a ser avaliada.

## Implicação

Migrations que criam roles **precisam fazer GRANT junto** — não é seguro deixar pra "fora do código". Solução adotada (commit `82cc114` — `core/0002_grants_app_roles.py`):

1. Função `apply_rls_policy(<table>)` foi atualizada pra também conceder:
   ```sql
   GRANT SELECT, INSERT, UPDATE, DELETE ON <table> TO app_readwrite;
   GRANT SELECT, INSERT, UPDATE, DELETE ON <table> TO app_jobs;
   ```
2. Migration aplicou retroativamente o GRANT nas 8 tabelas tenant-aware existentes na época.
3. Toda nova migration que cria tabela tenant-aware chama `apply_rls_policy()` que já dá GRANT junto.

Resultado: testes de isolation rodaram, e a policy RLS finalmente foi exercitada de verdade pela primeira vez no projeto.

## Onde já apareceu

- `apps/core/migrations/0002_grants_app_roles.py` — fix da migration.
- `apps/core/migrations/0001_rls_setup.py` — onde o gap começou.
- Helper `apply_rls_policy()` (no schema `public`) — atualizado pra incluir GRANT.

## Próxima vez que importar

Quando criar nova role Postgres com policy RLS:

1. **Mesmo commit** que cria a role inclui GRANT nas tabelas relevantes. Não deixar pra "produção via ALTER ROLE" — vira esquecido.
2. Helper de criar tabela tenant-aware (no nosso caso `apply_rls_policy()`) deve **automaticamente** dar GRANT pros roles app — toda tabela nova já fica protegida + acessível pelos roles.
3. Teste mínimo de smoke: depois da migration, rodar `SELECT * FROM <tabela>` como cada role e confirmar que nem `permission denied` nem vazamento aparecem.

## Status

- [x] Confirmado e resolvido. Helper `apply_rls_policy()` dá GRANT automático desde commit `82cc114`.

## Notas relacionadas

- [[aprendizados/medchat-superuser-bypassrls]] — outro problema na mesma área: SUPERUSER bypassa RLS em prod
- [[entidades/clinica]] — `Clinica` é a única tabela sem RLS (e por isso sem essa preocupação)
