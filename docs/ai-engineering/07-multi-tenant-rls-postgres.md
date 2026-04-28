---
status: em-uso
created: 2026-04-28
tema: multi-tenancy, isolamento, postgres, rls
---

# 07 — Multi-tenancy via Row-Level Security no Postgres

## Conceito

Row-Level Security (RLS) é um mecanismo nativo do Postgres (desde 9.5,
2016) que permite definir **policies SQL** aplicadas automaticamente a
toda query — `SELECT`, `INSERT`, `UPDATE`, `DELETE` — em uma tabela. A
policy é uma expressão booleana avaliada **por linha**: se retornar
`true`, a linha é visível/editável; se `false`, é como se não existisse.

A diferença chave em relação a um `WHERE clinica_id = X` na aplicação:
o filtro não pode ser esquecido. Mesmo que alguém escreva
`SELECT * FROM pacientes` sem cláusula nenhuma — em um Django shell, em
um script ad-hoc, em um `psql` em produção — o Postgres aplica a policy
automaticamente. É **enforcement no banco**, não na aplicação.

## Por que usamos no MedChat

O MedChat é SaaS B2B onde a regra inegociável é nunca expor dados de uma
clínica para outra. O risco de vazamento por bug humano (um `WHERE`
esquecido em migration ad-hoc, um JOIN sem qualificação, uma query
exploratória feita pelo time pra debugar incidente) seria altíssimo se
o filtro morasse só no Django. Com RLS no Postgres:

1. O ORM do Django não precisa fazer nada — RLS é transparente, queries
   continuam idênticas.
2. Acesso direto via `psql` em produção também respeita policy (a
   sessão precisa setar `app.clinica_id` antes de ver qualquer coisa).
3. Compromisso ótimo entre simplicidade operacional (banco único,
   schema único, migrations únicas) e isolamento forte (três camadas
   defensivas: policy + middleware + validação no model).

A decisão completa, com alternativas avaliadas, está em
[ADR-0002](../adr/0002-rls-vs-schema.md).

## Como funciona

### 1. Definir a policy

```sql
ALTER TABLE pacientes ENABLE ROW LEVEL SECURITY;
ALTER TABLE pacientes FORCE ROW LEVEL SECURITY;

CREATE POLICY tenant_isolation ON pacientes
  USING (clinica_id = current_setting('app.clinica_id')::uuid)
  WITH CHECK (clinica_id = current_setting('app.clinica_id')::uuid);
```

- `ENABLE` ativa RLS na tabela.
- `FORCE` aplica a policy também ao OWNER da tabela. Sem isso, o usuário
  que criou a tabela bypassa — em Django dev, é fácil esquecer porque o
  usuário da app costuma ser o owner.
- `USING` filtra leituras (`SELECT`, e o lado lido de `UPDATE`/`DELETE`).
- `WITH CHECK` filtra escritas (`INSERT`, e o lado novo de `UPDATE`).
  Sem `WITH CHECK`, a app poderia inserir uma linha com `clinica_id`
  errado mesmo com `app.clinica_id` setado corretamente.

### 2. Setar `app.clinica_id` por sessão

Postgres suporta "settings de aplicação" customizados via `SET`. O
prefixo namespace é livre (`app.*`, `myapp.*`, etc) — Postgres não
valida o conteúdo, só armazena.

```sql
-- válido até o COMMIT/ROLLBACK da transação corrente:
SET LOCAL app.clinica_id = '550e8400-e29b-41d4-a716-446655440000';

-- ler de volta:
SELECT current_setting('app.clinica_id');
-- com fallback (não erra se não setado):
SELECT current_setting('app.clinica_id', true);
```

`SET LOCAL` (em vez de `SET`) é **obrigatório** em pool de conexões: o
valor é descartado no fim da transação e nunca vaza para a próxima
request que pegar a mesma conexão do pool.

### 3. Roles e BYPASSRLS

O role default do Postgres bypassa RLS quando é OWNER da tabela (a
menos que `FORCE`). Roles específicos podem ser criados com
`BYPASSRLS` para jobs cross-tenant:

```sql
CREATE ROLE app_readwrite LOGIN PASSWORD '...';      -- sob policy
CREATE ROLE app_jobs LOGIN BYPASSRLS PASSWORD '...'; -- bypass total
```

No MedChat: a aplicação Django roda como `app_readwrite`; tasks Celery
que precisam varrer todas as clínicas (lembretes diários, expurgo de
mensagens vencidas) usam `app_jobs`. Migrations rodam como super-user
em dev e como role com `BYPASSRLS` em produção.

### 4. O middleware Django

```python
class RLSMiddleware:
    def __init__(self, get_response):
        self.get_response = get_response

    def __call__(self, request):
        if self._is_public(request):
            return self.get_response(request)
        clinica_id = self._resolve_tenant(request)
        if clinica_id is None:
            return JsonResponse(
                {"erro": "tenant não resolvido"}, status=500
            )
        with transaction.atomic():
            with connection.cursor() as cur:
                cur.execute(
                    "SET LOCAL app.clinica_id = %s",
                    [str(clinica_id)],
                )
            return self.get_response(request)
```

E para Celery (mesmo contrato fora do ciclo HTTP):

```python
@with_tenant(clinica_id)
def process_inbound_message(self, mensagem_id):
    ...
```

O decorator faz o mesmo `SET LOCAL` dentro de `transaction.atomic()`
antes de executar a função, garantindo que toda task tenant-aware
opera dentro do escopo correto.

## Pegadinhas conhecidas

- **Silent zero rows:** se a policy é `USING (clinica_id = current_setting('app.clinica_id')::uuid)` e
  `app.clinica_id` não está setado, `current_setting` levanta erro — a
  menos que a chamada use o segundo argumento `current_setting('app.clinica_id', true)` (`missing_ok=true`),
  que retorna `NULL` e a query devolve zero rows. Decisão MedChat:
  **fail-loud no middleware**, antes do banco virar oracle silencioso.
- **`SET` vs `SET LOCAL`:** `SET` persiste pela conexão inteira. Em
  pool, isso vaza tenant entre requests. Sempre `SET LOCAL`.
- **`FORCE ROW LEVEL SECURITY`:** sem isso, o owner da tabela bypassa
  policy. Em dev é fácil esquecer porque o user do Django costuma ser
  o owner. Sempre habilitar.
- **Migrations precisam BYPASS:** `ALTER TABLE` em tabela com policy
  ativa exige role com `BYPASSRLS`. Em dev migrations rodam como
  super-user; em prod é o role dedicado.
- **`COPY`/`pg_dump`/`pg_restore`:** todos respeitam RLS quando rodados
  por role sob policy. Backup em prod precisa rodar como `BYPASSRLS`,
  senão sai vazio.

## Como vamos verificar que funciona

Teste integração obrigatório (mínimo 1 caso por tabela tenant-owned):

```python
def test_rls_isola_pacientes_entre_clinicas(db, clinica_a, clinica_b):
    # cria paciente em A
    with set_app_clinica_id(clinica_a.id):
        Paciente.objects.create(
            clinica=clinica_a, telefone_e164="+5511999999999", nome="Ana"
        )
    # tenta ler como B
    with set_app_clinica_id(clinica_b.id):
        assert Paciente.objects.count() == 0
```

E o anti-teste — request sem tenant deve abortar:

```python
def test_query_sem_tenant_falha(db):
    with pytest.raises(ProgrammingError):  # ou middleware 500
        Paciente.objects.count()
```

## Referências

- Postgres docs — Row Security Policies:
  <https://www.postgresql.org/docs/current/ddl-rowsecurity.html>
- Crunchy Data — "A Practical Guide to Multi-Tenant Postgres":
  <https://www.crunchydata.com/blog/postgres-row-level-security-for-multi-tenant-applications>
- Supabase docs — RLS examples (modelos prontos para auth/owner): <https://supabase.com/docs/guides/database/postgres/row-level-security>
- ADR companheiro deste repo:
  [`docs/adr/0002-rls-vs-schema.md`](../adr/0002-rls-vs-schema.md)
