"""Helpers para o handler de webhook WhatsApp.

Vivem fora de `config/api.py` para que sejam testáveis isoladamente
e reutilizáveis quando o `EvolutionProvider` real entrar (item 10
da Fase 1) — o parser ganha implementações dedicadas por
provedor (`evolution.py`, `cloud.py`) seguindo este shape.

Hoje o `parse_evolution_payload` cobre o caminho mínimo do
provedor Evolution (mensagem de texto entrante). Não é o parser
completo; quando virar provider real, este vira `parse_minimo`
e a versão completa fica em `apps.channels.providers.evolution`.
"""

from __future__ import annotations

import hashlib
import hmac
from typing import Any, Optional


def verifica_hmac_sha256(raw_body: bytes, header_signature: str, secret: str) -> bool:
    """Compara HMAC-SHA256 do body cru com o header `X-Hub-Signature-256`.

    Convenção do WhatsApp Cloud (e Meta em geral): header tem o
    prefixo `sha256=` antes do hex digest. Comparação com
    `hmac.compare_digest` para evitar timing attacks (operação
    em tempo constante independente da posição do byte que difere).

    Retorna `False` para qualquer header mal-formado em vez de
    levantar — o handler converte em 401, não em 500.
    """
    if not header_signature or not header_signature.startswith("sha256="):
        return False
    esperado_hex = header_signature[len("sha256=") :]
    calculado = hmac.new(secret.encode("utf-8"), raw_body, hashlib.sha256).hexdigest()
    return hmac.compare_digest(calculado, esperado_hex)


def parse_evolution_payload(payload: dict[str, Any]) -> Optional[dict[str, Any]]:
    """Extrai campos mínimos de um webhook Evolution de mensagem texto.

    Retorna `None` quando o payload é um evento que não nos interessa
    (status update, ack de leitura, mídia ainda não suportada). O
    handler interpreta `None` como "aceitar 200 mas não disparar
    fluxo" — provedor não retransmite o evento.

    Shape esperado (subconjunto do que Evolution manda):
    ```
    {
      "data": {
        "key": {"id": "wamid_xxx", "remoteJid": "5511...@s.whatsapp.net"},
        "message": {"conversation": "texto"},
        "pushName": "Nome opcional"
      }
    }
    ```

    Quando o `EvolutionProvider` entrar (item 10), este parser
    passa a viver em `apps/channels/providers/evolution.py` e
    cobre os outros tipos (audio, image, location, button reply).
    """
    data = payload.get("data") or {}
    key = data.get("key") or {}
    message = data.get("message") or {}

    external_id = key.get("id")
    remote_jid = key.get("remoteJid") or ""
    conteudo = message.get("conversation")

    if not (external_id and remote_jid and conteudo):
        return None

    # JID Evolution: "5511999999999@s.whatsapp.net" → "+5511999999999".
    # Grupo (`@g.us`) e broadcast (`@broadcast`) são ignorados — só
    # processamos diálogo direto. Quando entrar suporte, refletir aqui.
    numero, _, sufixo = remote_jid.partition("@")
    if sufixo != "s.whatsapp.net":
        return None
    if not numero.isdigit():
        return None

    return {
        "external_id": external_id,
        "from_e164": f"+{numero}",
        "body": conteudo,
        "push_name": data.get("pushName"),
    }
