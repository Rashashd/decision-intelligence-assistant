# Decision Intelligence Assistant

A tool that helps triage customer support tickets. You type in a complaint or issue, and it tells you how urgent it is, gives you a suggested response, and shows you similar past tickets.

It uses two approaches to answer: one that looks up similar past tickets first (RAG), and one that answers directly without any context. Both answers are shown side by side so you can compare them.

---

## What's inside

```
decision-intelligence-assistant/
├── backend/       FastAPI app (API, RAG, ML model, logging)
├── frontend/      React app (the UI)
├── notebooks/     ML training notebook
├── data/          Raw CSV + processed pickle file
├── models/        Trained classifier (priority_classifier.joblib)
└── docker-compose.yml
```

---

## How it works

When you submit a query:

1. **Retrieval**: ChromaDB finds the 5 most similar past tweets using embeddings
2. **RAG answer**: GPT-4o reads those 5 tweets and writes a response with that context
3. **Direct answer**: GPT-4o answers the same question without any context (for comparison)
4. **ML priority**: A locally trained classifier predicts urgent vs normal
5. **LLM priority**: GPT-4o also predicts priority, so you can compare the two

---

## Before you start

You need:
- **Python 3.11+**: [download here](https://www.python.org/downloads/)
- **Node.js 20+**: [download here](https://nodejs.org/)
- **uv** (Python package manager): `pip install uv`
- **Docker Desktop** (only if you want to run via Docker): [download here](https://www.docker.com/products/docker-desktop/)
- An **OpenAI API key**: [get one here](https://platform.openai.com/api-keys)
- **Twitter Customer Support Dataset**: you can download it from: [download here](kaggle.com/datasets/thoughtvector/customer-support-on-twitter) and put it in the folder *data*

---

## Setup

### 1. Copy the environment file

```bash
cp .env.example .env
```

Then open `.env` and fill in your API key:

```
OPENAI_API_KEY=sk-...your key here...
```

Everything else can stay as-is for local development.

> If you also have a Gemini API key, add it too. The app will automatically fall back to Gemini if OpenAI rate-limits you. If you leave it empty, that's fine, it just won't fall back.

### 2. Run the ML notebook

Open `notebooks/ml-pipeline.ipynb` and run all cells. This trains the priority classifier and saves two files:

- `models/priority_classifier.joblib` — the trained model
- `data/inbound_processed.pkl` — the processed tweet data (used for the vector store)

You only need to do this once.

---

## Running locally (without Docker)

### Backend

```bash
cd backend
uv sync              # install dependencies (first time only)
python -m app.utils.ingest   # load tweets into ChromaDB (first time only)
uv run uvicorn app.main:app --reload
```

The API will be running at `http://localhost:8000`.

> The `ingest` step embeds 105,000 tweets and will take a few minutes the first time. After that, ChromaDB saves everything to `chroma_db/` and you don't need to run it again.

### Frontend

Open a second terminal:

```bash
cd frontend
npm install          # first time only
npm run dev
```

Open your browser at `http://localhost:5173`.

---

## Running with Docker

Make sure Docker Desktop is running, then:

```bash
docker compose up --build
```

That's it. Docker will:
1. Build the backend and frontend images
2. Run the ingestion step automatically (skips it if already done)
3. Start both servers

Open your browser at `http://localhost:3000`.

> The first build takes a while because it installs all Python and Node dependencies. Subsequent starts are fast.

---

## Environment variables

| Variable | What it does | Default |
|---|---|---|
| `OPENAI_API_KEY` | Your OpenAI key (required) | — |
| `OPENAI_MODEL` | Which OpenAI model to use | `gpt-4o` |
| `GEMINI_API_KEY` | Gemini key for fallback (optional) | empty |
| `EMBEDDING_PROVIDER` | `openai` or `gemini` | `openai` |
| `CHROMA_PERSIST_DIR` | Where ChromaDB stores data | `./chroma_db` |
| `TOP_K_RESULTS` | How many similar tickets to retrieve | `5` |
| `LOG_DIR` | Where query logs are saved | `./logs` |
| `MODEL_PATH` | Path to the trained classifier | `./models/priority_classifier.joblib` |

> Important: `EMBEDDING_PROVIDER` must be the same value when you run `ingest.py` and when you start the server. If you change it, you need to re-run ingest.

---

## API

One endpoint:

**POST** `/api/query`

```json
{
  "query": "My order hasn't arrived and it's been 2 weeks"
}
```

Returns:
```json
{
  "rag_answer":       { "text": "...", "latency_ms": 1200, "cost_usd": 0.0012 },
  "non_rag_answer":   { "text": "...", "latency_ms": 800,  "cost_usd": 0.0008 },
  "ml_priority":      { "label": "urgent", "confidence": 0.91, "latency_ms": 4 },
  "llm_priority":     { "label": "urgent", "confidence": 0.95, "latency_ms": 900 },
  "retrieved_tickets": [ ... ]
}
```

You can test it directly at `http://localhost:8000/docs` (FastAPI's built-in interactive docs).

---

## Troubleshooting

**`ModuleNotFoundError: No module named 'app'`**
Make sure you're running commands from inside the `backend/` folder, not the project root.

**`Collection 'support_tickets' does not exist`**
You need to run the ingest step first: `python -m app.utils.ingest`

**`models/priority_classifier.joblib not found`**
Run the ML notebook first to generate the model file.

**OpenAI errors (401)**
Double-check your `OPENAI_API_KEY` in the `.env` file. Make sure there are no extra spaces.