"""Acesso a dados do LAI — SEMPRE escopado por owner_user_id.

Esta é a fronteira de isolamento: toda função exige owner_user_id e filtra por
ele no SQL. Não existe caminho para ler decisões/sensores de outro usuário.
O backend do chat injeta o owner_user_id da SESSÃO autenticada (nunca do LLM).
"""

import datetime as dt

import psycopg2
import psycopg2.extras

from . import config


def _decisions_conn():
    return psycopg2.connect(config.DECISIONS_DB_URL)


def _timescale_conn():
    return psycopg2.connect(config.TIMESCALE_DB_URL)


def list_user_farms(owner_user_id: str) -> list[str]:
    """Fazendas que pertencem ao usuário (de farm_owners)."""
    with _decisions_conn() as conn, conn.cursor() as cur:
        cur.execute(
            "SELECT farm_id FROM farm_owners WHERE owner_user_id = %s ORDER BY farm_id",
            (owner_user_id,),
        )
        return [r[0] for r in cur.fetchall()]


def farm_info(owner_user_id: str) -> list[dict]:
    """Metadados da(s) fazenda(s)/cultura do usuário: cultura, variedade, local,
    coordenadas e início da safra. Use para saber O QUE é a lavoura."""
    with _decisions_conn() as conn, conn.cursor(cursor_factory=psycopg2.extras.RealDictCursor) as cur:
        cur.execute(
            """
            SELECT farm_id, crop_name, crop_variety, location_name,
                   latitude, longitude, season_start
            FROM farm_owners WHERE owner_user_id = %s ORDER BY farm_id
            """,
            (owner_user_id,),
        )
        rows = cur.fetchall()
    for r in rows:
        if r.get("season_start"):
            r["season_start"] = r["season_start"].isoformat()
    return rows


def _decision_rows(owner_user_id: str, where_extra: str = "", params: tuple = (),
                   limit: int | None = None) -> list[dict]:
    sql = """
        SELECT farm_id, data_date, irrigate, irrigation_mm,
               apply_nitrogen, nitrogen_kg, rationale, weather_summary, created_at
        FROM ai_decisions
        WHERE owner_user_id = %s
    """ + where_extra + " ORDER BY data_date DESC"
    if limit is not None:
        sql += " LIMIT %s"
        params = params + (limit,)
    with _decisions_conn() as conn, conn.cursor(cursor_factory=psycopg2.extras.RealDictCursor) as cur:
        cur.execute(sql, (owner_user_id, *params))
        rows = cur.fetchall()
    # Serializa datas p/ JSON.
    for r in rows:
        r["data_date"] = r["data_date"].isoformat() if r["data_date"] else None
        r["created_at"] = r["created_at"].isoformat() if r.get("created_at") else None
    return rows


def latest_decision(owner_user_id: str, farm_id: str | None = None) -> dict | None:
    """Decisão mais recente do usuário (opcionalmente de uma fazenda)."""
    extra, params = "", ()
    if farm_id:
        extra, params = " AND farm_id = %s", (farm_id,)
    rows = _decision_rows(owner_user_id, extra, params, limit=1)
    return rows[0] if rows else None


def list_decisions(owner_user_id: str, limit: int = 10,
                   only_actions: bool = False, farm_id: str | None = None) -> list[dict]:
    """Lista as últimas decisões do usuário.

    only_actions=True retorna só dias em que houve irrigação ou aplicação de N.
    """
    extra, params = "", ()
    if farm_id:
        extra += " AND farm_id = %s"
        params += (farm_id,)
    if only_actions:
        extra += " AND (irrigate = true OR apply_nitrogen = true)"
    return _decision_rows(owner_user_id, extra, params, limit=max(1, min(limit, 100)))


def decision_by_date(owner_user_id: str, date: str, farm_id: str | None = None) -> dict | None:
    """Decisão de um dia específico (YYYY-MM-DD)."""
    extra, params = " AND data_date = %s", (date,)
    if farm_id:
        extra += " AND farm_id = %s"
        params += (farm_id,)
    rows = _decision_rows(owner_user_id, extra, params, limit=1)
    return rows[0] if rows else None


def decisions_summary(owner_user_id: str) -> dict:
    """Resumo agregado das decisões do usuário (totais, contagens, período)."""
    with _decisions_conn() as conn, conn.cursor(cursor_factory=psycopg2.extras.RealDictCursor) as cur:
        cur.execute(
            """
            SELECT
                count(*)                                   AS total_dias,
                count(*) FILTER (WHERE irrigate)           AS dias_irrigados,
                count(*) FILTER (WHERE apply_nitrogen)     AS dias_com_n,
                coalesce(sum(irrigation_mm), 0)            AS total_irrigacao_mm,
                coalesce(sum(nitrogen_kg), 0)              AS total_n_kg,
                min(data_date)                             AS primeira_data,
                max(data_date)                             AS ultima_data,
                count(DISTINCT farm_id)                    AS fazendas
            FROM ai_decisions
            WHERE owner_user_id = %s
            """,
            (owner_user_id,),
        )
        row = cur.fetchone() or {}
    for k in ("primeira_data", "ultima_data"):
        if row.get(k):
            row[k] = row[k].isoformat()
    return dict(row)


def sensor_history(owner_user_id: str, variable: str, days: int = 7) -> list[dict]:
    """Histórico bruto de um sensor (TimescaleDB), só das fazendas do usuário.

    variable: nome do sensor (ex.: SM, DVS, LAI, irrigation_mm, weather_RAIN).
    """
    farms = list_user_farms(owner_user_id)
    if not farms:
        return []
    # subtopic publicado tem o farm_id como prefixo (ex.: farm-001/daily).
    like_clauses = " OR ".join(["subtopic LIKE %s"] * len(farms))
    like_params = tuple(f"{f}%" for f in farms)
    since_ns = int((dt.datetime.now() - dt.timedelta(days=10000)).timestamp() * 1e9)  # tudo
    with _timescale_conn() as conn, conn.cursor(cursor_factory=psycopg2.extras.RealDictCursor) as cur:
        cur.execute(
            f"""
            SELECT to_timestamp(time/1e9)::date AS dia, name, value, subtopic
            FROM messages
            WHERE name = %s AND time >= %s AND ({like_clauses})
            ORDER BY time DESC
            LIMIT %s
            """,
            (variable, since_ns, *like_params, max(1, min(days * 5, 500))),
        )
        rows = cur.fetchall()
    for r in rows:
        r["dia"] = r["dia"].isoformat() if r["dia"] else None
    return rows
