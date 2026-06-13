"""Consumer MQTT — entry point do serviço `decisioning`.

Fluxo por mensagem .daily:
  parse SenML → snapshot → (idempotência) → previsão do tempo → CrewAI →
  persiste decisão → publica comando de volta (loop fechado).

Mensagens .command são ignoradas (anti-feedback).
"""

import datetime as dt
import json
import logging

import paho.mqtt.client as mqtt

from . import actuator, config, db
from .decision.crew import DecisionCrew
from .weather import get_weather_forecast

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s %(levelname)s %(message)s",
)
log = logging.getLogger("decisioning")

# Crew (e LLM) construído sob demanda na 1ª mensagem e reusado depois.
# Lazy para o serviço subir/conectar no MQTT mesmo sem a key do LLM definida.
_crew = None


def _get_crew() -> DecisionCrew:
    global _crew
    if _crew is None:
        _crew = DecisionCrew()
    return _crew


def _parse_topic(topic: str):
    """m/<dom>/c/<chan>/<farm_id>/<subtopic> → (farm_id, subtopic)."""
    prefix = f"m/{config.DOMAIN_ID}/c/{config.CHANNEL_ID}/"
    if not topic.startswith(prefix):
        return None, None
    rest = topic[len(prefix):].split("/")
    farm_id = rest[0] if rest else None
    subtopic = rest[1] if len(rest) > 1 else None
    return farm_id, subtopic


def _parse_senml(payload: bytes):
    """Lista SenML → (snapshot {n: v}, day_epoch)."""
    records = json.loads(payload)
    snapshot, day_epoch = {}, None
    for rec in records:
        name = rec.get("n")
        if name is not None and "v" in rec:
            snapshot[name] = rec["v"]
        if day_epoch is None and rec.get("t"):
            day_epoch = int(rec["t"])
    return snapshot, day_epoch


def on_connect(client, userdata, flags, reason_code, properties=None):
    if reason_code != 0:
        log.error("Falha ao conectar no MQTT: %s", reason_code)
        return
    topic = f"m/{config.DOMAIN_ID}/c/{config.CHANNEL_ID}/#"
    client.subscribe(topic, qos=0)
    log.info("Conectado. Assinando %s", topic)


def on_message(client, userdata, msg):
    try:
        farm_id, subtopic = _parse_topic(msg.topic)
        if not farm_id or subtopic != config.SUBTOPIC_DAILY:
            return  # ignora .command e tópicos inesperados (anti-feedback)

        snapshot, day_epoch = _parse_senml(msg.payload)
        if day_epoch is None:
            log.warning("[%s] mensagem sem timestamp, ignorando", farm_id)
            return
        data_date = dt.date.fromtimestamp(day_epoch).isoformat()

        if db.decision_exists(farm_id, data_date):
            log.info("[%s] %s — decisão já existe, pulando", farm_id, data_date)
            return

        log.info("[%s] %s — decidindo (DVS=%s SM=%s)...",
                 farm_id, data_date, snapshot.get("DVS"), snapshot.get("SM"))

        weather = get_weather_forecast()
        decision = _get_crew().run(snapshot, weather, data_date)

        db.insert_decision(
            farm_id=farm_id,
            domain_id=config.DOMAIN_ID,
            channel_id=config.CHANNEL_ID,
            data_date=data_date,
            decision=decision,
            sensor_snapshot=snapshot,
            llm_model=f"{config.LLM_PROVIDER}",
        )
        actuator.publish_command(client, farm_id, decision, day_epoch)

        log.info("[%s] %s → irrigar=%s (%.1fmm) N=%s (%.1fkg)\n  rationale: %s\n  weather: %s",
                 farm_id, data_date, decision.irrigate, decision.irrigation_mm,
                 decision.apply_nitrogen, decision.nitrogen_kg,
                 decision.rationale, decision.weather_summary)

    except Exception:  # noqa: BLE001 — um erro num dia não pode derrubar o serviço
        log.exception("Erro processando mensagem de %s", msg.topic)


def main():
    client = mqtt.Client(
        mqtt.CallbackAPIVersion.VERSION2,
        client_id=config.MQTT_PROTOCOL_ID,
    )
    client.username_pw_set(config.MQTT_CLIENT_ID, config.MQTT_CLIENT_SECRET)
    client.on_connect = on_connect
    client.on_message = on_message
    client.reconnect_delay_set(min_delay=1, max_delay=30)

    log.info("Conectando em %s:%s ...", config.MQTT_HOST, config.MQTT_PORT)
    client.connect(config.MQTT_HOST, config.MQTT_PORT, keepalive=60)
    client.loop_forever()


if __name__ == "__main__":
    main()
