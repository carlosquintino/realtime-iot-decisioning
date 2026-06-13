"""Configuração do serviço LAI (chat conversacional).

Autocontido: NÃO importa src.config (que exige vars de MQTT do decisioning).
"""

import os

# ── Bancos ────────────────────────────────────────────────────────────────────
# Decisões da IA (fonte primária do LAI).
DECISIONS_DB_URL = os.getenv(
    "DECISIONS_DB_URL",
    "postgresql://magistrala:magistrala@magistrala-re-db:5432/decisions",
)
# Histórico bruto de sensores (TimescaleDB do Magistrala).
TIMESCALE_DB_URL = os.getenv(
    "TIMESCALE_DB_URL",
    "postgresql://supermq:supermq@magistrala-timescale:5432/supermq",
)

# ── Auth (SuperMQ users) ──────────────────────────────────────────────────────
# Endpoint para emitir token a partir de email/senha (login próprio do LAI — fallback).
SUPERMQ_USERS_URL = os.getenv("SUPERMQ_USERS_URL", "http://users:9002")

# Herança de login da UI (SSO): LAI encaminha o cookie NextAuth p/ este endpoint
# e lê o accessToken (JWT SuperMQ) da sessão → user_id. Mesma origem via nginx.
UI_SESSION_URL = os.getenv("UI_SESSION_URL", "http://ui:3000")
UI_SESSION_PATH = os.getenv("UI_SESSION_PATH", "/api/auth/session")
# Host esperado pelo NextAuth (precisa casar com NEXTAUTH_URL no .env da UI).
UI_SESSION_HOST = os.getenv("UI_SESSION_HOST", "")

# ── LLM (trocável: openai | gemini | local) — espelha o decisioning ───────────
LLM_PROVIDER = os.getenv("LLM_PROVIDER", "gemini").lower()

OPENAI_API_KEY = os.getenv("OPENAI_API_KEY", "")
OPENAI_MODEL = os.getenv("OPENAI_MODEL", "gpt-4o")

GEMINI_API_KEY = os.getenv("GEMINI_API_KEY") or os.getenv("GOOGLE_API_KEY", "")
GEMINI_MODEL = os.getenv("GEMINI_MODEL", "gemini/gemini-flash-latest")

LOCAL_MODEL = os.getenv("LOCAL_MODEL", "ollama/llama3")
LOCAL_API_BASE = os.getenv("LOCAL_API_BASE", "http://host.docker.internal:11434")
LOCAL_API_KEY = os.getenv("LOCAL_API_KEY", "not-needed")

# Sessão do chat: segredo p/ assinar o cookie/token de sessão do LAI.
SESSION_SECRET = os.getenv("LAI_SESSION_SECRET", "lai-dev-secret-change-me")
SESSION_TTL_SECONDS = int(os.getenv("LAI_SESSION_TTL", "28800"))  # 8h


def llm_params() -> dict:
    """Retorna {model, api_key, [base_url]} para o litellm conforme o provider."""
    if LLM_PROVIDER == "openai":
        if not OPENAI_API_KEY:
            raise RuntimeError("LLM_PROVIDER=openai mas OPENAI_API_KEY não definida.")
        return {"model": OPENAI_MODEL, "api_key": OPENAI_API_KEY}
    if LLM_PROVIDER == "gemini":
        if not GEMINI_API_KEY:
            raise RuntimeError("LLM_PROVIDER=gemini mas GEMINI_API_KEY não definida.")
        return {"model": GEMINI_MODEL, "api_key": GEMINI_API_KEY}
    if LLM_PROVIDER == "local":
        return {"model": LOCAL_MODEL, "api_base": LOCAL_API_BASE, "api_key": LOCAL_API_KEY}
    raise RuntimeError(f"LLM_PROVIDER inválido: '{LLM_PROVIDER}'.")
