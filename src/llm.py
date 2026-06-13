"""Conexão de LLM trocável (OpenAI / Gemini / local).

Corrige o módulo antigo (llm_connection.py), que retornava None no branch openai
e quebrava se a key não existisse. Retorna um crewai.LLM pronto para os agentes.
"""

from crewai import LLM

from . import config


def get_llm() -> LLM:
    """Retorna o LLM configurado em LLM_PROVIDER (openai | gemini | local)."""
    provider = config.LLM_PROVIDER

    if provider == "openai":
        if not config.OPENAI_API_KEY:
            raise RuntimeError("LLM_PROVIDER=openai mas OPENAI_API_KEY não foi definida.")
        return LLM(model=config.OPENAI_MODEL, api_key=config.OPENAI_API_KEY)

    if provider == "gemini":
        if not config.GEMINI_API_KEY:
            raise RuntimeError("LLM_PROVIDER=gemini mas GEMINI_API_KEY/GOOGLE_API_KEY não foi definida.")
        return LLM(model=config.GEMINI_MODEL, api_key=config.GEMINI_API_KEY)

    if provider == "local":
        # Self-hosted via litellm (Ollama, vLLM, LM Studio, ...).
        return LLM(
            model=config.LOCAL_MODEL,
            base_url=config.LOCAL_API_BASE,
            api_key=config.LOCAL_API_KEY,
        )

    raise RuntimeError(
        f"LLM_PROVIDER inválido: '{provider}'. Use openai, gemini ou local."
    )
