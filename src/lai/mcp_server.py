"""MCP server do LAI — expõe o banco de decisões da IA como tools.

Cada tool exige `owner_user_id` e delega para queries.py, que filtra por ele no
SQL. O backend do chat (chat.py) conecta neste server (cliente in-memory) e
SEMPRE injeta o owner_user_id da sessão autenticada — o LLM nunca o fornece.

Também roda standalone (stdio) para hosts MCP externos (ex.: Claude Desktop):
    python -m src.lai.mcp_server
"""

from fastmcp import FastMCP

from . import queries

mcp = FastMCP("LAI — Decisões de Irrigação/Nitrogênio")


@mcp.tool
def get_farm_info(owner_user_id: str) -> list[dict]:
    """Informações da(s) fazenda(s)/cultura do usuário: cultura (ex.: batata),
    variedade, localização, coordenadas e início da safra. Use SEMPRE que o
    usuário perguntar o que é a lavoura, qual cultura, onde fica, etc."""
    return queries.farm_info(owner_user_id)


@mcp.tool
def get_latest_decision(owner_user_id: str, farm_id: str | None = None) -> dict | None:
    """Retorna a decisão de manejo mais recente do usuário (irrigação + nitrogênio).
    Use para 'qual foi a última decisão/irrigação?'."""
    return queries.latest_decision(owner_user_id, farm_id)


@mcp.tool
def list_recent_decisions(owner_user_id: str, limit: int = 10,
                          only_actions: bool = False,
                          farm_id: str | None = None) -> list[dict]:
    """Lista as últimas decisões do usuário (mais recentes primeiro).
    only_actions=True filtra só dias com irrigação ou aplicação de N."""
    return queries.list_decisions(owner_user_id, limit, only_actions, farm_id)


@mcp.tool
def get_decision_by_date(owner_user_id: str, date: str,
                         farm_id: str | None = None) -> dict | None:
    """Decisão de um dia específico. date no formato YYYY-MM-DD."""
    return queries.decision_by_date(owner_user_id, date, farm_id)


@mcp.tool
def get_decisions_summary(owner_user_id: str) -> dict:
    """Resumo agregado: total de dias, dias irrigados, total de mm e kg de N,
    período coberto e nº de fazendas. Use para visão geral da temporada."""
    return queries.decisions_summary(owner_user_id)


@mcp.tool
def get_sensor_history(owner_user_id: str, variable: str, days: int = 7) -> list[dict]:
    """Histórico bruto de um sensor das fazendas do usuário (TimescaleDB).
    variable: SM (umidade), DVS (estágio), LAI, irrigation_mm, weather_RAIN, etc."""
    return queries.sensor_history(owner_user_id, variable, days)


if __name__ == "__main__":
    mcp.run()  # stdio
