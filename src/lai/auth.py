"""Auth do LAI — login próprio contra o SuperMQ.

Fluxo: email/senha → POST /users/tokens/issue → JWT cujo `sub` é o user_id.
O user_id é a chave de isolamento (owner_user_id). Emitimos um token de SESSÃO
LAI assinado localmente para não reexpor o token SuperMQ ao browser a cada msg.
"""

import base64
import json
import time

import itsdangerous
import requests

from . import config

_signer = itsdangerous.TimestampSigner(config.SESSION_SECRET)


class AuthError(Exception):
    pass


def _decode_jwt_sub(access_token: str) -> str:
    """Extrai o `sub` (user_id) do JWT sem validar assinatura (já veio do SuperMQ)."""
    try:
        payload_b64 = access_token.split(".")[1]
        payload_b64 += "=" * (-len(payload_b64) % 4)  # padding
        payload = json.loads(base64.urlsafe_b64decode(payload_b64))
        sub = payload.get("sub")
        if not sub:
            raise AuthError("token sem 'sub'")
        return sub
    except (IndexError, ValueError) as e:
        raise AuthError(f"JWT inválido: {e}") from e


def login(email: str, password: str) -> dict:
    """Autentica no SuperMQ e devolve {user_id, email}. Lança AuthError se falhar."""
    url = f"{config.SUPERMQ_USERS_URL.rstrip('/')}/users/tokens/issue"
    try:
        r = requests.post(url, json={"username": email, "password": password}, timeout=10)
    except requests.RequestException as e:
        raise AuthError(f"falha ao contatar SuperMQ: {e}") from e
    if r.status_code != 201 and r.status_code != 200:
        raise AuthError("credenciais inválidas")
    token = r.json().get("access_token")
    if not token:
        raise AuthError("SuperMQ não retornou access_token")
    user_id = _decode_jwt_sub(token)
    return {"user_id": user_id, "email": email}


def _find_access_token(obj) -> str | None:
    """Procura recursivamente um JWT (3 partes) em chaves típicas de token."""
    keys = ("accessToken", "access_token", "token")
    if isinstance(obj, dict):
        for k in keys:
            v = obj.get(k)
            if isinstance(v, str) and v.count(".") == 2:
                return v
        for v in obj.values():
            found = _find_access_token(v)
            if found:
                return found
    elif isinstance(obj, list):
        for v in obj:
            found = _find_access_token(v)
            if found:
                return found
    return None


def resolve_from_ui_session(cookie_header: str) -> str | None:
    """Herda o login da UI: encaminha o cookie NextAuth p/ /api/auth/session,
    lê o accessToken (JWT SuperMQ) e devolve o user_id (sub). None se não logado.

    Seguro: só um cookie NextAuth válido (assinado com NEXTAUTH_SECRET) produz
    uma sessão não-vazia; o endpoint da própria UI faz essa validação.
    """
    if not cookie_header:
        return None
    url = f"{config.UI_SESSION_URL.rstrip('/')}{config.UI_SESSION_PATH}"
    headers = {"Cookie": cookie_header, "Accept": "application/json"}
    if config.UI_SESSION_HOST:
        headers["Host"] = config.UI_SESSION_HOST
    try:
        r = requests.get(url, headers=headers, timeout=8)
        if r.status_code != 200:
            return None
        data = r.json()
    except (requests.RequestException, ValueError):
        return None
    if not data:
        return None
    token = _find_access_token(data)
    if not token:
        return None
    try:
        return _decode_jwt_sub(token)
    except AuthError:
        return None


def issue_session(user_id: str) -> str:
    """Assina um token de sessão LAI carregando o user_id."""
    raw = json.dumps({"uid": user_id, "iat": int(time.time())}).encode()
    return _signer.sign(base64.urlsafe_b64encode(raw)).decode()


def verify_session(session_token: str) -> str:
    """Valida o token de sessão e devolve o user_id. Lança AuthError se inválido/expirado."""
    try:
        unsigned = _signer.unsign(session_token, max_age=config.SESSION_TTL_SECONDS)
        data = json.loads(base64.urlsafe_b64decode(unsigned))
        return data["uid"]
    except (itsdangerous.BadSignature, itsdangerous.SignatureExpired, ValueError, KeyError) as e:
        raise AuthError(f"sessão inválida: {e}") from e
