# AI Agent Hardcoded — Enterprise AI Initiative Assessment Agent

Este projeto é um **agente de IA para avaliação de iniciativas enterprise de Inteligência Artificial**.

Ele foi construído como parte de um bootcamp prático de AI Agents, com foco em arquitetura realista, backend em FastAPI, frontend em React/Vite, uso da OpenAI API, validação estruturada com Pydantic, memória local, busca semântica com embeddings e workflow de avaliação com governança.

## 1. O que o projeto faz

O agente recebe a descrição de uma iniciativa de IA e produz uma avaliação executiva e técnica, incluindo:

- Problema de negócio identificado
- Valor potencial para a organização
- Complexidade técnica
- Principais riscos
- Stack inicial recomendada
- Quick wins de curto prazo
- Nota de viabilidade de 0 a 10
- Subscores estruturados
- Explicações de ajustes de score
- Decisão de revisão humana
- Contexto histórico de avaliações anteriores
- Busca semântica por iniciativas similares

A ideia é simular um agente que apoia líderes de tecnologia, produto, inovação e dados na **priorização de iniciativas de IA em ambiente corporativo**.

---

## 2. Conceitos de agente implementados

O projeto não é apenas um chatbot. Ele implementa vários conceitos reais de AI Agents:

- **LLM reasoning**: uso de modelo de linguagem para interpretar e avaliar iniciativas.
- **Structured output**: respostas em JSON validado por schemas Pydantic.
- **Tool calling**: uso de ferramentas internas para classificar iniciativa, sugerir stack e mapear riscos.
- **Workflow state**: controle das etapas executadas pelo agente.
- **Deterministic rules**: regras fixas para ajustar scores com base em risco, dados, integração e governança.
- **Semantic memory**: geração de embeddings para buscar avaliações similares.
- **Hybrid memory search**: busca semântica com fallback lexical.
- **Human-in-the-loop**: sinalização de casos que exigem revisão humana.
- **Persistence**: armazenamento local de avaliações, embeddings e revisões.
- **API productization**: exposição do agente por endpoints FastAPI.
- **Frontend integration**: interface web para interação com o agente.

---

## 3. Stack utilizada

### Backend

- Python
- FastAPI
- Uvicorn
- OpenAI API
- Pydantic
- uv (Gerenciamento de pacotes)
- python-dotenv
- JSON local storage
- OpenAI Embeddings

### Frontend

- React
- Vite
- bun (Gerenciamento de pacotes e execução)
- JavaScript / JSX
- CSS
- Fetch API

---

## 4. Estrutura do projeto

```text
ai-agent-hardcoded/
│
├── ai_agent.py              # Núcleo do agente
├── main.py                  # Backend FastAPI principal
├── utils.py                 # Funções utilitárias e constantes
├── constants.py             # Definições centrais
├── requests.py              # Schemas de Request
├── schemas.py               # Schemas de Dados
├── prompts.py               # Prompt de sistema
├── pyproject.toml           # Configuração uv
├── uv.lock                  # Lock file uv
├── .env                     # Variáveis de ambiente
├── data/                    # Storage local
└── frontend/                # Frontend (React + Vite)
    ├── package.json
    ├── bun.lock             # Lock file bun
    └── ...
```

---

## 5. Configuração do ambiente

### 5.1. Clonar o projeto

```bash
git clone <url-do-repositorio>
cd ai-agent-hardcoded
```

---

## 6. Configuração do backend

### 6.1. Instalar dependências e rodar

Utilizamos o `uv` para o gerenciamento de pacotes.

```bash
uv sync
uv run uvicorn main:app --reload
```

O backend ficará disponível em `http://127.0.0.1:8000`.

---

## 7. Configuração do frontend

Abra um novo terminal na pasta `frontend`:

```bash
cd frontend
bun install
bun run dev
```

O frontend ficará disponível em `http://localhost:5173`.
