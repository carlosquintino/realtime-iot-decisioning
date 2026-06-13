"""Atuação: publica a decisão de volta no Magistrala (fecha o loop).

Usa o MESMO client MQTT do consumer (reusa conexão/credencial). Publica em
m/<domain>/c/<channel>/<farm_id>/command. O crop-gym assina esse subtopic,
correlaciona pelo timestamp `t` (epoch do dia) e aplica irrigação/N no PCSE-Gym.
"""

import json

from . import config
from .decision.schemas import FarmDecision


def build_command_senml(decision: FarmDecision, day_epoch: int) -> list:
    """SenML do comando. `t` = epoch do dia, para correlação dia↔comando no crop-gym."""
    return [
        {"n": "cmd_irrigation_mm", "v": float(decision.irrigation_mm), "t": day_epoch},
        {"n": "cmd_nitrogen_kg", "v": float(decision.nitrogen_kg), "t": day_epoch},
    ]


def publish_command(mqtt_client, farm_id: str, decision: FarmDecision, day_epoch: int) -> None:
    topic = (
        f"m/{config.DOMAIN_ID}/c/{config.CHANNEL_ID}/{farm_id}/{config.SUBTOPIC_COMMAND}"
    )
    payload = json.dumps(build_command_senml(decision, day_epoch))
    mqtt_client.publish(topic, payload, qos=0)
