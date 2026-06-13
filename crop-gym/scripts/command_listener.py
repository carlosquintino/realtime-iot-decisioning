"""
command_listener.py  —  FARM SIDE
==================================
Assina via MQTT os comandos de manejo que o serviço `decisioning` publica de
volta (subtopic .command) e os disponibiliza ao run_farm para fechar o loop.

Correlação dia↔comando: pelo timestamp `t` do SenML (epoch do dia simulado),
que é o mesmo da observação publicada naquele dia.
"""

import json
import threading
import time

import paho.mqtt.client as mqtt


class CommandListener:
    def __init__(self, host, port, domain_id, channel_id, client_id, client_secret,
                 protocol_id="farm-listener", subtopic_command="command"):
        self.domain_id = domain_id
        self.channel_id = channel_id
        self.subtopic_command = subtopic_command
        self._commands = {}          # {epoch:int -> {"irrigation": mm, "N": kg}}
        self._lock = threading.Lock()

        self._client = mqtt.Client(mqtt.CallbackAPIVersion.VERSION2, client_id=protocol_id)
        self._client.username_pw_set(client_id, client_secret)
        self._client.on_connect = self._on_connect
        self._client.on_message = self._on_message
        self._client.reconnect_delay_set(min_delay=1, max_delay=30)
        self._host, self._port = host, port

    # ── MQTT callbacks ────────────────────────────────────────────────────────
    def _on_connect(self, client, userdata, flags, reason_code, properties=None):
        topic = f"m/{self.domain_id}/c/{self.channel_id}/+/{self.subtopic_command}"
        client.subscribe(topic, qos=0)
        print(f"[listener] conectado, assinando {topic}")

    def _on_message(self, client, userdata, msg):
        try:
            records = json.loads(msg.payload)
            epoch, irrig, n = None, 0.0, 0.0
            for rec in records:
                if rec.get("t"):
                    epoch = int(rec["t"])
                if rec.get("n") == "cmd_irrigation_mm":
                    irrig = float(rec.get("v", 0))
                elif rec.get("n") == "cmd_nitrogen_kg":
                    n = float(rec.get("v", 0))
            if epoch is not None:
                with self._lock:
                    self._commands[epoch] = {"irrigation": irrig, "N": n}
                print(f"[listener] comando recebido t={epoch} irrig={irrig}mm N={n}kg")
        except Exception as e:  # noqa: BLE001
            print(f"[listener] erro ao processar comando: {e}")

    # ── API pública ───────────────────────────────────────────────────────────
    def start(self):
        self._client.connect(self._host, self._port, keepalive=60)
        self._client.loop_start()

    def stop(self):
        self._client.loop_stop()
        self._client.disconnect()

    def wait_for(self, epoch: int, timeout: float = 60.0, poll: float = 0.5):
        """Espera o comando correlacionado a `epoch`. Retorna o dict de ação ou None."""
        deadline = time.time() + timeout
        while time.time() < deadline:
            with self._lock:
                cmd = self._commands.pop(epoch, None)
            if cmd is not None:
                return cmd
            time.sleep(poll)
        return None
