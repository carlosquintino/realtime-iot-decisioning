from confluent_kafka import Consumer, KafkaException
import json

conf = {
    "bootstrap.servers": "localhost:9091",
    "group.id": "sensor-consumer-group",
    "auto.offset.reset": "earliest"
}
consumer = Consumer(conf)

# A CORREÇÃO É ESTA LINHA:
topic_name = "servidor_sensor.Sensor.dbo.LeiturasUmidade"
consumer.subscribe([topic_name])

print(f"Consumindo mensagens do tópico: {topic_name}")
print("Pressione Ctrl+C para parar.")

try:
    while True:
        msg = consumer.poll(1.0)

        if msg is None:
            continue
        if msg.error():
            raise KafkaException(msg.error())
        else:
            try:
                payload_str = msg.value().decode('utf-8')
                payload_json = json.loads(payload_str)
                print("\n--- Nova Leitura Recebida ---")
                print(json.dumps(payload_json, indent=2))
            except Exception as e:
                print(f"Não foi possível decodificar a mensagem: {e}")

except KeyboardInterrupt:
    print("\nConsumidor interrompido pelo usuário.")
finally:
    consumer.close()