# agentVoice — Local LLM Integration & Ollama Guide (Phase 3)

## 1. Overview

agentVoice uses **Ollama** as its default local LLM runtime. All inference happens locally on your machine or VPS—no paid external AI API keys or cloud accounts are required.

## 2. Installing & Starting Ollama

### Windows / macOS / Linux

1. Download and install Ollama from [https://ollama.com](https://ollama.com).
2. Start the Ollama server (if not already running as a background service):

```bash
ollama serve
```

3. Verify Ollama is reachable on its default local port (`http://localhost:11434`):

```bash
curl http://localhost:11434/api/version
```

You can override the endpoint in `.env`:

```env
OLLAMA_BASE_URL=http://localhost:11434
DEFAULT_LLM_MODEL=qwen2.5:7b-instruct
```

## 3. Managing Models in agentVoice

1. Open **http://localhost:3000/models** (**Model Manager**).
2. Check the **Local LLM Runtime (Ollama)** card to confirm connection and version.
3. Enter a model tag (e.g., `qwen2.5:3b` or `llama3.2:3b`) or click **Pull** on a recommended model.
4. Monitor live download progress or click **Cancel Download**.
5. Click **Set Default** on any installed model.

## 4. Assigning Models & Testing in AI Chat Playground

1. Open **AI Agents** (`/agents`), create or edit an agent, and go to the **AI Model** step.
2. Choose an installed model from the dropdown (or enter a custom model ID) and adjust `temperature`, `max_tokens`, and `context_window_messages`.
3. Open the agent's details page and click **Test in Playground** (`/agents/[id]/playground`).
4. Send a message in Hindi, Hinglish, or English to receive a streaming local LLM response. Conversations persist in `agentvoice-data/conversations/*.json`.

## 5. Conversation & Model API Endpoints

- `GET /api/v1/llm/health` — Ollama runtime health & version
- `GET /api/v1/llm/providers` — Supported LLM providers
- `GET /api/v1/models` — Runtime status, installed models, default model, recommendations
- `POST /api/v1/models/refresh` — Refresh installed models
- `POST /api/v1/models/default` — Set default model
- `POST /api/v1/models/pull` — Start background model pull (`202 Accepted`)
- `GET /api/v1/models/pull/{task_id}` — Poll pull progress
- `POST /api/v1/models/pull/{task_id}/cancel` — Cancel active pull
- `DELETE /api/v1/models/{model_id}` — Delete installed model
- `GET /api/v1/agents/{agent_id}/conversations` — List agent conversations
- `POST /api/v1/agents/{agent_id}/conversations` — Create conversation
- `GET /api/v1/conversations/{conversation_id}` — Get conversation
- `DELETE /api/v1/conversations/{conversation_id}` — Delete conversation
- `POST /api/v1/conversations/{conversation_id}/messages` — Non-streaming chat turn
- `POST /api/v1/conversations/{conversation_id}/messages/stream` — SSE streaming chat turn

## 6. Troubleshooting

- **Ollama is not reachable**: Ensure `ollama serve` is running and `OLLAMA_BASE_URL` in `.env` matches.
- **Model not installed**: Open **Model Manager** (`/models`) to pull the model or assign an installed model.
- **Slow responses**: Smaller quantized models (e.g., `qwen2.5:3b`) run much faster on CPU-only machines than 7B–9B models.
