---
title: snapshotter-overlayfs-corrompido
type: aprendizado
tags: [docker, wsl, postgres, debug]
---

# Aprendizado: `wsl --shutdown` brusco corrompe snapshotter overlayfs do Docker Desktop

> Os sintomas que apareceram (exec format error, 502 Bad Gateway, `docker run` travando) **todos** apontavam pra "imagem errada de arquitetura" ou "engine fora do ar". A causa real era storage corrompido — invisível pelos sinais de superfície.

## O que descobrimos

`wsl --shutdown` chamado durante uma operação de **write** do containerd no overlayfs deixa o snapshotter num estado inconsistente: o registro lógico (snapshot id 353/354 etc.) existe, mas o filesystem físico no path `/var/lib/desktop-containerd/daemon/io.containerd.snapshotter.v1.overlayfs/snapshots/<id>/fs` **não**.

Resultado: qualquer operação Docker que toque uma layer afetada falha de jeitos não-óbvios:

- `postgres` (e qualquer container que lê layers afetadas) sai com `exec format error` — parece bug de arquitetura, mas não é.
- API do Docker engine retorna **`502 Bad Gateway`** em chamadas que mexem em containers/networks.
- `docker run --rm <imagem>` standalone **trava sem timeout** — nem retorna erro.
- `docker info` continua funcionando (parece que o engine tá ok).

## Como descobrimos

Diagnóstico foi pelo `docker system df`:

```
Error: failed to calculate image disk usage:
  lstat /var/lib/desktop-containerd/daemon/io.containerd.snapshotter.v1.overlayfs/snapshots/354/fs:
  no such file or directory
```

Snapshot id 354 registrado, filesystem físico ausente. Confirmação.

Antes do diagnóstico real, perdi tempo com hipóteses falsas:

1. **"A imagem `pgvector/pgvector:pg17` é arch errada"** — Não. Standalone `docker run --rm postgres:17-alpine` também travava.
2. **"O engine inteiro tá morto"** — Não. `docker info` respondia.
3. **"Reiniciar o Docker Desktop"** — `wsl --shutdown` + kill processos + `Start-Process` do `.exe` resultou no Docker Desktop morrendo silenciosamente. Pior ainda: piorou o estado.

## Implicação

**`wsl --shutdown` é destrutivo se chamado no momento errado.** Pra recuperar do estado quebrado, a única solução prática foi **Clean / Purge data** via Docker Desktop UI:

1. Docker Desktop → ⚙️ Settings → Troubleshoot → **Clean / Purge data** (NÃO "Reset to factory defaults" — esse apaga tudo, inclusive configs).
2. Selecionar tudo (Hyper-V/WSL2, containers, images, volumes).
3. Confirmar. Demora 1-2 min, Docker Desktop reinicia limpo.
4. Próximo `docker compose up -d` puxa imagens novas.

## Onde já apareceu

- Sessão de debug em 2026-04-28 noite (commit `ce46e74` em `docs/context/05-progresso-fase-1.md`).
- Stack do MedChat ficou ~2h fora antes do diagnóstico correto.

## Próxima vez que importar

- **Não usar `wsl --shutdown`** com Docker Desktop rodando. Se precisar reiniciar Docker, usar a opção "Restart" do menu da bandeja.
- Se aparecer `exec format error` + `502 Bad Gateway` simultâneos, **rodar `docker system df` primeiro** — é o teste mais rápido pra detectar snapshotter corrompido.
- Não confundir sintoma de storage corrompido com bug de imagem.

## Status

- [x] Confirmado — vimos em produção local. Reproduzido pelo diagnóstico de `docker system df`.

## Notas relacionadas

- [[entidades/clinica]] — Postgres roda nessa stack
