"""Serviço de decisão da IA (decisioning) — feature da plataforma Magistrala.

Consome dados de fazenda via MQTT, decide irrigação e nitrogênio com CrewAI,
persiste a decisão no Postgres e devolve o comando pelo Magistrala (loop fechado).
"""
