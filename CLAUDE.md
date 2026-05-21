# Contexto do Projeto

## Visão Geral
- **Nome**: REALTIME-IOT-DECISIONING
- **Stack**: Python, Magistrala (SuperMQ), CrewAI, Kafka, Docker
- **Objetivo**: Integrar a plataforma Magistrala com IA para decisão automática de irrigação, aplicação de nitrogênio e pesticidas em lavouras, com base nas condições do solo, previsão do tempo e estado da cultura. Inclui chat para consulta da plantação (últimas irrigações, estado atual, previsão de colheita, etc.). Deve suportar requisições simultâneas de múltiplos usuários.

## Regras Importantes
- **Persistência obrigatória**: Toda decisão da IA deve ser persistida para consulta posterior (motivo da irrigação, estado atual, última irrigação, etc.)
- **LLM configurável**: O modelo de LLM (decisão e chat) deve ser trocável facilmente — suportar Gemini, OpenAI e modelos locais
- **Docker**: Tudo roda em Docker, EXCETO o crop-gym (simula uma fazenda externa)
- **Multi-usuário**: A plataforma deve suportar múltiplos usuários simultâneos
- **CLAUDE.md**: Sempre atualizar este arquivo ao alterar arquitetura, componentes ou estado do projeto

## Arquitetura de Componentes

### crop-gym/ — Simulador de fazenda (roda FORA do Docker)
- `scripts/crop_create.py`: Wrapper do PCSEEnv (PCSE-Gym); busca clima histórico via Open-Meteo e salva em Excel para alimentar o modelo
- `scripts/farm_simulator.py`: Publica dados diários da simulação no Magistrala via HTTP (formato SenML)
- `scripts/magistrala_setup.py`: Setup inicial — cria domain/client/channel no Magistrala e gera `farm_credentials.json`
- `scripts/run_farm.py`: Entry point da simulação; atualmente usa política `no_intervention` (sem irrigação)
- `PCSE-Gym/`: Biblioteca de simulação de culturas (submódulo)


### magistrala/ — Plataforma IoT broker
- Subprojeto Magistrala/SuperMQ completo com docker-compose
- Dados publicados no canal via SenML: DVS, LAI, SM, TWSO, TWRT, weather_*, irrigation_mm, N_applied_kg

## Fluxo de Dados
```
Fazenda (PCSE-Gym) → HTTP/SenML → Magistrala → Kafka CDC → app.py → CrewAI → Decisão
```

## Stack Técnica
| Componente | Tecnologia |
|---|---|
| Simulação de cultura | PCSE-Gym (WOFOST80) |
| Clima histórico | Open-Meteo archive API |
| Previsão do tempo | wttr.in |
| IoT broker | Magistrala (SuperMQ) |
| Mensageria | Kafka (via Magistrala CDC) |
| Agentes IA | CrewAI |
| LLM padrão | OpenAI GPT-4o (configurável para Gemini ou local) |
| Infraestrutura | Docker Compose |

## Estado Atual (2026-05-21)

### Infraestrutura
- Magistrala rodando via `make run_latest` dentro de `magistrala/` — 44 containers ativos
- IP EC2: `18.232.149.52`
- UI acessível em `http://18.232.149.52/` (nginx proxia para magistrala-ui:3000)
- Login: `admin@example.com` / `12345678`
- `magistrala-ui-backend` container rodando (necessário para UI funcionar)

### Correções aplicadas no docker/.env
- `NEXTAUTH_URL=http://18.232.149.52` (porta 80 via nginx)
- `SMQ_DOMAINS_GRPC_URL=domains:7013` (era 7003 — porta errada)
- `SMQ_CLIENTS_GRPC_URL=clients:7008` (era 7006 — porta errada)

### Correções no nginx
- `docker/nginx/nginx-key.conf`: adicionado catch-all `location /` que faz proxy para `http://ui:3000`

### Correção no SpiceDB
- Inserido relacionamento correto de membership do admin no domain `crop-farms`
  (bug do SuperMQ v0.19.1: gravava `{domain_id}_{user_id}` em vez de `{user_id}`)

### crop-gym — SIMULAÇÃO FUNCIONANDO
- Virtualenv: `crop-gym/venv/` com Python 3.13
- Credenciais: `crop-gym/farm_credentials.json` (domain_id, channel_id, client_secret)
  - Domain ID: `bfcec7dc-8a4e-4914-9641-4f8a09216067` (route: `crop-farms`)
  - Channel ID: `bfd6022a-7e16-499a-aa7a-49084daaec49`
  - Client secret: `06d248b6-a30d-46b5-b3a6-82131acdf6bb`
- **Simulação executada com sucesso**: 82 dias publicados via HTTP 202

```bash
# Rodar na EC2, dentro de crop-gym/
venv/bin/python scripts/run_farm.py --credentials farm_credentials.json
```

### Formato do tópico HTTP (Magistrala v0.19+)
O formato do tópico mudou completamente na v0.19. O URL correto para publicação é:
```
POST http://localhost/http/m/<domain_id>/c/<channel_id>/<subtopic>
Authorization: Client <client_secret>
```
Formato antigo (`/channels/{id}/messages/`) NÃO funciona.

### Agentes IA
- 3 agentes CrewAI definidos para decisão de irrigação
- `run_farm.py` usa política `no_intervention` (sem irrigação) — a ser substituída pela decisão da IA

### Falta implementar
- **Consumir mensagens do NATS/Kafka**: ler os dados publicados pelo crop-gym no Magistrala
- Persistência das decisões da IA (banco de dados)
- Interface de chat para o usuário consultar a plantação
- Suporte robusto a múltiplos usuários simultâneos
- Integração da decisão da IA de volta ao crop-gym (fechar o loop)
- Decisão de aplicação de nitrogênio e pesticidas
