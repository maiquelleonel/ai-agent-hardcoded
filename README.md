# AI Agent Bootcamp — Enterprise AI Initiative Assessment Agent

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
- python-dotenv
- JSON local storage
- OpenAI Embeddings

### Frontend

- React
- Vite
- JavaScript / JSX
- CSS
- Fetch API

---

## 4. Estrutura do projeto

```text
ai-agent-bootcamp/
│
├── ai_agent.py              # Núcleo do agente
├── main.py                  # Backend FastAPI principal
├── app.py                   # Versão anterior/simplificada do backend
├── prompts.py               # Prompt de sistema
├── schemas.py               # Schemas Pydantic
├── tools.py                 # Tools determinísticas usadas pelo agente
├── requirements.txt         # Dependências Python
├── .env                     # Variáveis de ambiente locais
├── .gitignore
│
├── data/
│   ├── assessments/         # Avaliações persistidas
│   ├── embeddings/          # Embeddings salvos
│   └── reviews/             # Itens de revisão humana
│
└── frontend/
    ├── package.json
    ├── src/
    └── ...
```

---

## 5. Configuração do ambiente

### 5.1. Clonar o projeto

```bash
git clone https://github.com/klaubersantos/ai-agent-bootcamp.git
cd ai-agent-bootcamp
```

---

## 6. Configuração do backend

### 6.1. Criar ambiente virtual

No Windows PowerShell:

```powershell
python -m venv .venv
```

Ativar o ambiente virtual:

```powershell
.\.venv\Scripts\Activate.ps1
```

Se o PowerShell bloquear a ativação da venv, execute:

```powershell
Set-ExecutionPolicy -ExecutionPolicy RemoteSigned -Scope CurrentUser
```

Depois tente ativar novamente:

```powershell
.\.venv\Scripts\Activate.ps1
```

---

### 6.2. Instalar dependências

```powershell
python -m pip install --upgrade pip
python -m pip install -r requirements.txt
```

Caso precise instalar manualmente:

```powershell
python -m pip install fastapi uvicorn python-multipart openai python-dotenv pydantic
```

---

### 6.3. Configurar variáveis de ambiente

Crie um arquivo `.env` na raiz do projeto:

```env
OPENAI_API_KEY=sua_chave_da_openai_aqui
OPENAI_MODEL=gpt-5
```

Importante: não suba o arquivo `.env` para o GitHub.

Confirme que o `.gitignore` contém:

```gitignore
.env
.venv/
venv/
__pycache__/
*.pyc
data/
```

---

### 6.4. Rodar o backend

Na raiz do projeto, com a venv ativada:

```powershell
python -m uvicorn main:app --reload
```

O backend ficará disponível em:

```text
http://127.0.0.1:8000
```

Documentação automática da API:

```text
http://127.0.0.1:8000/docs
```

Healthcheck:

```text
http://127.0.0.1:8000/
```

Resposta esperada:

```json
{
  "status": "ok"
}
```

---

## 7. Configuração do frontend

Abra um segundo terminal.

Entre na pasta do frontend:

```powershell
cd frontend
```

Instale as dependências:

```powershell
npm install
```

Rode o frontend:

```powershell
npm run dev
```

O frontend normalmente ficará disponível em:

```text
http://localhost:5173
```

ou:

```text
http://127.0.0.1:5173
```

---

## 8. Como rodar backend e frontend juntos

Use dois terminais.

### Terminal 1 — Backend

```powershell
cd "C:\Users\klaub\Documents\Python Scripts\ai-agent-bootcamp"
.\.venv\Scripts\Activate.ps1
python -m uvicorn main:app --reload
```

### Terminal 2 — Frontend

```powershell
cd "C:\Users\klaub\Documents\Python Scripts\ai-agent-bootcamp\frontend"
npm install
npm run dev
```

Depois abra no navegador:

```text
http://localhost:5173
```

---

## 9. Principais endpoints do backend

### Healthcheck

```http
GET /
```

---

### Avaliar uma iniciativa

```http
POST /assess
```

Exemplo de payload:

```json
{
  "initiative": "Criar um assistente de IA para responder dúvidas internas dos colaboradores sobre políticas de RH."
}
```

---
