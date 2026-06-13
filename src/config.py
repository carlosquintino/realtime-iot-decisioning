"""Configuração via variáveis de ambiente.

Tudo que muda entre ambientes (broker, banco, canal, LLM) vem do .env / compose.
"""

import os

from dotenv import load_dotenv

load_dotenv()


def _req(name: str) -> str:
    val = os.getenv(name)
    if not val:
        raise RuntimeError(f"Variável de ambiente obrigatória ausente: {name}")
    return val


# ── MQTT (broker do Magistrala) ───────────────────────────────────────────────
MQTT_HOST = os.getenv("MQTT_HOST", "supermq-mqtt")
MQTT_PORT = int(os.getenv("MQTT_PORT", "1883"))
# Identificador MQTT (protocolo) — o adapter rejeita CONNECT sem client-id.
MQTT_PROTOCOL_ID = os.getenv("MQTT_PROTOCOL_ID", "ai-decisioning")
# Credencial do client SuperMQ usada na auth: username=<client_id>, password=<secret>.
MQTT_CLIENT_ID = _req("MQTT_CLIENT_ID")
MQTT_CLIENT_SECRET = _req("MQTT_CLIENT_SECRET")

# ── Canal / domínio do Magistrala ─────────────────────────────────────────────
DOMAIN_ID = _req("DOMAIN_ID")
CHANNEL_ID = _req("CHANNEL_ID")

# Subtopics: observações chegam em <farm>/daily; comandos saem em <farm>/command.
SUBTOPIC_DAILY = os.getenv("SUBTOPIC_DAILY", "daily")
SUBTOPIC_COMMAND = os.getenv("SUBTOPIC_COMMAND", "command")

# ── Banco de decisões (Postgres re-db) ────────────────────────────────────────
DATABASE_URL = os.getenv(
    "DATABASE_URL",
    "postgresql://magistrala:magistrala@magistrala-re-db:5432/decisions",
)

# ── LLM (trocável: openai | gemini | local) ───────────────────────────────────
# Troca de provedor = só mudar LLM_PROVIDER no .env e recriar o container.
LLM_PROVIDER = os.getenv("LLM_PROVIDER", "openai").lower()

OPENAI_API_KEY = os.getenv("OPENAI_API_KEY", "")
OPENAI_MODEL = os.getenv("OPENAI_MODEL", "gpt-4o")

GEMINI_API_KEY = os.getenv("GEMINI_API_KEY") or os.getenv("GOOGLE_API_KEY", "")
GEMINI_MODEL = os.getenv("GEMINI_MODEL", "gemini/gemini-2.0-flash")

# Local / self-hosted (ex.: Ollama, vLLM, LM Studio) via litellm.
LOCAL_MODEL = os.getenv("LOCAL_MODEL", "ollama/llama3")
LOCAL_API_BASE = os.getenv("LOCAL_API_BASE", "http://host.docker.internal:11434")
LOCAL_API_KEY = os.getenv("LOCAL_API_KEY", "not-needed")

# ── Clima ─────────────────────────────────────────────────────────────────────
# Em container não dá para deduzir cidade pelo IP; define explicitamente.
WEATHER_LOCATION = os.getenv("WEATHER_LOCATION", "Sao Paulo")
