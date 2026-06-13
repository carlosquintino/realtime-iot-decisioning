<div align="center">

# 🌱 Realtime IoT Decisioning

### Decisão agrícola em tempo real com IA sobre a plataforma Magistrala

### Irrigação • Nitrogênio • Loop Fechado • Chat Conversacional

![Python](https://img.shields.io/badge/python-3.13-blue?style=flat-square&logo=python&logoColor=white)
![Docker](https://img.shields.io/badge/docker-compose-2496ED?style=flat-square&logo=docker&logoColor=white)
![Magistrala](https://img.shields.io/badge/IoT-Magistrala%20(SuperMQ)-orange?style=flat-square)
![CrewAI](https://img.shields.io/badge/AI-CrewAI-success?style=flat-square)
![MCP](https://img.shields.io/badge/LLM-MCP-purple?style=flat-square)
![License](https://img.shields.io/badge/license-Apache%202.0-blue?style=flat-square)

</div>

## Introdução 🌍

O **Realtime IoT Decisioning** integra a plataforma IoT **[Magistrala](https://github.com/absmach/magistrala) (SuperMQ)** com **Inteligência Artificial** para automatizar decisões de manejo em lavouras — **irrigação** e **aplicação de nitrogênio** — com base nas condições do solo, no estado da cultura e na previsão do tempo.

Uma fazenda simulada publica dados diários de sensores na Magistrala; um serviço de IA consome esses dados, decide a ação ideal, persiste a decisão e devolve o comando de volta para a fazenda — fechando o **loop de decisão** de forma autônoma. Toda decisão fica registrada e pode ser consultada em linguagem natural pelo robô conversacional **LAI**, integrado à interface da plataforma.

### Por que é diferente

- **Loop fechado real**: a IA não só recomenda — o comando volta e é aplicado na cultura no dia seguinte.
- **Decisão explicável e persistida**: cada irrigação/adubação guarda a justificativa, o resumo do clima e o snapshot dos sensores.
- **LLM trocável**: Gemini, OpenAI ou modelos locais (Ollama) — basta uma variável de ambiente.
- **Multiusuário com isolamento**: cada usuário só enxerga as decisões das suas próprias fazendas.

## ✨ Funcionalidades

- 🤖 **Decisão autônoma com IA (CrewAI)**: 5 agentes especializados (clima, solo, irrigação, nitrogênio e sintetizador) chegam a uma decisão estruturada por dia.
- 🔄 **Loop fechado de manejo**: `crop-gym → Magistrala → IA → comando de volta → aplicação na cultura` (lag de 1 dia, com fallback seguro).
- 💧 **Irrigação e nitrogênio inteligentes**: conservador com água e fertilizante — só age sob estresse hídrico/nutricional real.
- 💬 **Chat conversacional LAI**: pergunte em português sobre últimas irrigações, estado da lavoura, cultura, totais da temporada, etc.
- 🔒 **Isolamento por usuário**: o LAI nunca mostra decisões de outro usuário (escopo aplicado no banco, não pelo LLM).
- 🧩 **MCP sobre o banco**: as consultas do chat são expostas como ferramentas MCP escopadas por dono.
- 🖥️ **Integrado à UI**: widget de chat injetado nas telas da Magistrala (sem fork da interface).
- 🗄️ **Persistência completa**: decisões em PostgreSQL e séries de sensores em TimescaleDB.
- 🔁 **LLM trocável**: OpenAI, Gemini ou local via uma única variável de ambiente.
- 🐳 **Tudo em Docker**, exceto o simulador de fazenda (que representa um cliente externo).

## 🏗️ Arquitetura — Loop Fechado

```
 crop-gym ──HTTP/SenML (.daily)──▶ Magistrala ──MQTT──▶ decisioning (CrewAI)
    ▲  (simula a fazenda,                                  │ decide irrigação + N
    │   roda FORA do Docker)                               ├─▶ persiste em ai_decisions (PostgreSQL)
    │                                                      │
    │   aplica a ação no PCSE-Gym                          ▼
    └────────── MQTT (.command) ◀───────────────── publica o comando de volta
                                                           │
                            TimescaleDB (sensores) ◀───────┘
                                   ▲
                                   │  consultas (MCP, escopado por usuário)
                          ┌────────┴─────────┐
        Browser (UI) ─────▶  LAI (chat)  ─────▶ ai_decisions + sensores
        widget injetado     login herdado       responde em linguagem natural
        via nginx           da UI (SSO)
```

A `crop-gym` assina o subtopic `.command`, correlaciona a resposta pelo timestamp do dia e aplica a ação no dia seguinte. Se a decisão não chegar no tempo limite, há fallback para "nenhuma intervenção".

## 🧩 Componentes

| Componente | Papel | Onde roda |
|---|---|---|
| **`crop-gym/`** | Simulador de fazenda (PCSE-Gym/WOFOST80). Busca clima histórico, simula a cultura, publica dados diários na Magistrala e aplica os comandos da IA. | **Fora** do Docker (cliente externo) |
| **`magistrala/`** | Plataforma IoT (SuperMQ): broker MQTT/HTTP, autenticação, canais, persistência e UI. | Docker Compose |
| **`src/` (decisioning)** | Cérebro de IA. Consome MQTT, decide com CrewAI, persiste e publica o comando de volta. | Docker |
| **`src/lai/` (LAI)** | Chat conversacional + servidor MCP sobre as decisões. Login herdado da UI, isolamento por usuário. | Docker |

### O serviço `decisioning`

Consome as mensagens `.daily`, monta um snapshot dos sensores, consulta a previsão do tempo e executa um **crew CrewAI** com 5 papéis encadeados, produzindo um objeto estruturado `FarmDecision` (`irrigate`, `irrigation_mm`, `apply_nitrogen`, `nitrogen_kg`, `rationale`, `weather_summary`). A decisão é gravada em `ai_decisions` (idempotente por fazenda+dia) e o comando é publicado de volta no subtopic `.command`.

### O robô conversacional `LAI`

- **Servidor MCP** com ferramentas sobre o banco: última decisão, listagem, decisão por data, resumo da temporada, histórico de sensores e informações da cultura/fazenda.
- **Isolamento por usuário**: toda consulta é filtrada por `owner_user_id`; o backend injeta o usuário da sessão — o LLM nunca controla esse parâmetro.
- **Login herdado da UI (SSO)**: reaproveita a sessão NextAuth da Magistrala; cai para login próprio se necessário.
- **Guardrails**: responde apenas sobre lavoura/irrigação/nitrogênio/sensores e recusa educadamente assuntos fora de escopo.
- **Widget na UI**: injetado em todas as páginas via `nginx sub_filter`, com perguntas-exemplo prontas.

## 🛠️ Stack Técnica

| Camada | Tecnologia |
|---|---|
| Simulação de cultura | PCSE-Gym (WOFOST80) |
| Clima histórico / previsão | Open-Meteo / wttr.in |
| Broker IoT | Magistrala (SuperMQ) |
| Transporte da IA | MQTT |
| Persistência de sensores | TimescaleDB |
| Persistência de decisões | PostgreSQL (`ai_decisions`) |
| Agentes de IA | CrewAI |
| Chat / ferramentas | FastAPI + MCP (FastMCP) + LiteLLM |
| LLM padrão | Gemini (trocável p/ OpenAI ou local) |
| Infraestrutura | Docker Compose + nginx |

## 🚀 Como Rodar

### 1. Subir a plataforma (Magistrala + decisioning + LAI)

```bash
cd magistrala
make run_latest        # sobe todos os serviços, incluindo decisioning e LAI
```

> A interface fica em `http://<IP>/` e o login padrão é `admin@example.com` / `12345678`.

### 2. Configurar a chave do LLM

Defina a chave do provedor escolhido em `magistrala/docker/.env` (arquivo **não versionado**):

```bash
GEMINI_API_KEY=sua-chave-aqui      # ou OPENAI_API_KEY
```

Depois recrie os serviços de IA:

```bash
make run_latest up args="-d --no-deps --force-recreate decisioning lai"
```

### 3. Rodar a fazenda simulada (loop fechado)

```bash
cd crop-gym
venv/bin/python scripts/run_farm.py --credentials farm_credentials.json
```

Opções úteis: `--open-loop` (sem IA), `--max-days N` (teste curto), `--wav <cm>` (água inicial no solo).

### 4. Conversar com o LAI

Abra a UI no navegador e clique no botão **LAI** (canto inferior direito). Exemplos de perguntas:

- *Qual foi a última irrigação?*
- *Mostre os últimos dados da fazenda*
- *Qual cultura estou cultivando?*
- *Resuma as decisões da temporada*

## 📁 Estrutura do Repositório

```
.
├── crop-gym/          # Simulador de fazenda (PCSE-Gym) — roda fora do Docker
│   └── scripts/       # run_farm, farm_simulator, command_listener, setup
├── magistrala/        # Plataforma Magistrala/SuperMQ (docker-compose, addons, nginx)
│   └── docker/addons/ # decisioning/ e lai/ (features deste projeto)
├── src/               # Serviço decisioning (IA de decisão)
│   ├── decision/      # crew CrewAI + schemas
│   └── lai/           # Chat conversacional LAI + servidor MCP
├── Dockerfile         # Imagem do decisioning
└── Dockerfile.lai     # Imagem do LAI
```

## 📜 Licença

Distribuído sob a licença **Apache 2.0**. A plataforma Magistrala pertence a [Abstract Machines](https://www.absmach.eu) sob a mesma licença.
