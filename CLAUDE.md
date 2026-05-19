# Contexto do Projeto

## Visão Geral
- **Nome**: REALTIME-IOT-DECISIONING
- **Stack**: python, magistrala, IA, MCP, AGENTS
- **Objetivo**: Adicionar a plataforma MAGISTRALA integração com IA, usando ou agentes ou MCP para decisão de irrigação ou não, uso de Nitrogenio ou não e talvez pesticida, com base nas condições atuais do solo, previsão do tempo para os proximos dias e condição atual da cultura, bem como a propria cultura. Junto a isso, a ideia é ter um chat onde o usuario pode perguntar sobre sua plantação, ultimas irrigações, estado atual, previsão de colheita, etc... Importante pontuar que a plataforma deve suportar requisições simutaneas de diferentes usuarios
O projeto contem também o crop-gym, que é uma simulação de fazenda enviando dados pro MAGISTRALA e regando a cultura caso precise 

## Arquitetura
As decisões tomada pela IA deve ser persistida, para consulta posterior do motivo de irrigação ou não, estado atual, ultima irrigação etc.
Importante que o modelo de LLM usado tanto para decisão quanto para respostas seja feito de forma que eu possa alterar o tipo de modelo ou até mesmo usar um modelo local.
Tudo deve rodar dentro do docker, menos o crop-gym, que é para simular uma plantação externa