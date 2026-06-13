"""Persistência das decisões no Postgres (db `decisions` no re-db).

Fonte de verdade que o MCP conversacional vai consultar depois.
"""

import json

import psycopg2

from . import config
from .decision.schemas import FarmDecision


def _connect():
    return psycopg2.connect(config.DATABASE_URL)


def get_farm_owner(farm_id: str) -> str | None:
    """Resolve o dono (user_id SuperMQ) de uma fazenda via tabela farm_owners.

    Retorna None se a fazenda não tiver dono mapeado — nesse caso a decisão é
    gravada com owner_user_id NULL e NENHUM usuário a vê no LAI (fail-safe de
    isolamento: melhor ocultar do que vazar para o usuário errado).
    """
    with _connect() as conn, conn.cursor() as cur:
        cur.execute(
            "SELECT owner_user_id FROM farm_owners WHERE farm_id = %s",
            (farm_id,),
        )
        row = cur.fetchone()
        return row[0] if row else None


def decision_exists(farm_id: str, data_date: str) -> bool:
    """Idempotência: já existe decisão para esta fazenda neste dia?"""
    with _connect() as conn, conn.cursor() as cur:
        cur.execute(
            "SELECT 1 FROM ai_decisions WHERE farm_id = %s AND data_date = %s",
            (farm_id, data_date),
        )
        return cur.fetchone() is not None


def insert_decision(
    *,
    farm_id: str,
    domain_id: str,
    channel_id: str,
    data_date: str,
    decision: FarmDecision,
    sensor_snapshot: dict,
    llm_model: str,
    owner_user_id: str | None = None,
) -> None:
    """Grava a decisão. ON CONFLICT (farm_id, data_date) não duplica.

    owner_user_id carimba o dono (isolamento do LAI). Se None, resolve via
    farm_owners; se ainda assim não houver dono, grava NULL (fail-safe).
    """
    if owner_user_id is None:
        owner_user_id = get_farm_owner(farm_id)
    with _connect() as conn, conn.cursor() as cur:
        cur.execute(
            """
            INSERT INTO ai_decisions (
                farm_id, domain_id, channel_id, data_date,
                irrigate, irrigation_mm, apply_nitrogen, nitrogen_kg,
                rationale, weather_summary, sensor_snapshot, llm_model, raw_output,
                owner_user_id
            ) VALUES (%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s)
            ON CONFLICT (farm_id, data_date) DO NOTHING
            """,
            (
                farm_id, domain_id, channel_id, data_date,
                decision.irrigate, decision.irrigation_mm,
                decision.apply_nitrogen, decision.nitrogen_kg,
                decision.rationale, decision.weather_summary,
                json.dumps(sensor_snapshot), llm_model,
                json.dumps(decision.model_dump()),
                owner_user_id,
            ),
        )
        conn.commit()
