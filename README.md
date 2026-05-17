# FinSight AI

An AI-powered conversational assistant for financial fraud analysts. FinSight combines Retrieval-Augmented Generation (RAG), machine learning predictions, and natural language data analysis into a single FastAPI backend.

---

## What it does

FinSight acts as an intelligent analyst co-pilot that can:

- **Answer policy questions** — retrieves answers from an internal knowledge base covering KYC, AML, and PCI DSS documents
- **Analyze transaction data** — translates natural language questions into SQL queries against live transaction and customer tables
- **Predict fraud** — classifies whether a transaction is fraudulent using a trained Random Forest model with custom feature engineering
- **Forecast purchase amounts** — estimates expected spend based on a customer profile
- **Remember context** — maintains per-user conversation history, persisted in SQLite and reconstructed across sessions

---

## Architecture overview

```
User Request
     │
     ▼
FastAPI (app/main.py)
     │
     ├── /api/v1/agent/chat  ──►  FinancialAgent (ReActAgent)
     │                                  │
     │                         ┌────────┼────────┐
     │                         ▼        ▼        ▼
     │                    Knowledge  SQL NL   ML Predictor
     │                    Base Tool  Query    (Fraud / Purchase)
     │
     └── /api/v1/chatbot/*  ──►  finsight (RAG pipeline)
                                      │
                            BM25 + Vector Retrieval
                            Reranker + Semantic Cache
                            Streaming Response
```

**Full architecture documentation:** [docs/architecture.md](docs/architecture.md)

---

## Tech stack

| Layer | Technology |
|---|---|
| API framework | FastAPI + Uvicorn |
| LLM | Google Gemini (gemini-3.1-flash-lite) |
| Agent orchestration | LlamaIndex ReActAgent |
| Embeddings | HuggingFace BAAI/bge-small-en-v1.5 |
| Reranker | cross-encoder/ms-marco-MiniLM-L12-v2 |
| Vector store | ChromaDB (persisted) |
| Database | SQLite via SQLAlchemy |
| ML models | Scikit-Learn Random Forest (GridSearchCV) |
| Model serialization | Joblib |
| Data processing | Pandas, Polars |
| Config & validation | Pydantic / pydantic-settings |

---

## Project structure

```
FinSight-AI/
├── app/
│   ├── api/routes/
│   │   ├── agent.py          # Tool-based agent endpoint
│   │   └── chatbot.py        # RAG chatbot + history endpoints
│   ├── services/
│   │   ├── agent/
│   │   │   ├── orchestrator.py   # ReActAgent wrapper
│   │   │   └── tools.py          # 5 specialized tools
│   │   ├── Rag_llm/
│   │   │   ├── llm.py            # ChatBot base class + finsight subclass
│   │   │   ├── llm_config.py     # Model and retrieval constants
│   │   │   ├── finsight_docs/    # Markdown knowledge base
│   │   │   └── finsight_embeddings/  # ChromaDB vector store (gitignored)
│   │   ├── data_analysis/
│   │   │   └── analyser.py       # NLSQLTableQueryEngine
│   │   ├── ml/
│   │   │   ├── predictor.py      # FraudPredictor + PurchasePredictor
│   │   │   └── transformers.py   # Custom sklearn transformers
│   │   ├── models/              # Trained .joblib artifacts
│   │   └── database/
│   │       └── database.py       # SQLite engine + table init
│   ├── config.py             # Pydantic settings + LlamaIndex init
│   ├── main.py               # FastAPI app + lifespan
│   └── schemas.py            # Request/response models
├── frontend/
│   └── index.html            # Single-page chat UI (served at GET /)
├── data/
│   ├── fraud_dataset.csv
│   ├── product_purchase_dataset.csv
│   └── load_datasets.py
├── notebooks/
│   ├── 01_fraud_model_training.ipynb
│   └── 02_purchase_model_training.ipynb
├── docs/
│   └── architecture.md
├── init_app.py               # One-time setup script
├── test_bot.py               # RAG chatbot smoke test
└── requirements.txt
```

---

## Prerequisites

- Python 3.10 or higher
- A [Google Gemini API key](https://aistudio.google.com/app/apikey)

---

## Setup

Run the initialization script once. It handles everything automatically:

```bash
python init_app.py
```

The script walks through 7 steps:

1. Python version check
2. Virtual environment creation (`.venv`)
3. Dependency installation
4. `.env` configuration (prompts for your Gemini API key)
5. Dataset loading (CSV → SQLite)
6. ML model training (Random Forest with GridSearchCV)
7. RAG index building (markdown docs → ChromaDB)

---

## Running the server

```bash
# Activate the virtual environment
.venv\Scripts\activate        # Windows
source .venv/bin/activate     # Linux / macOS

# Start the API
uvicorn app.main:app --reload
```

The API will be available at `http://localhost:8000` or your respectively-named IP address/domain name.
Interactive documentation (Swagger UI): `http://localhost:8000/docs` or your respectively-named IP address/domain name.

---

## Web interface

Once the server is running, open **http://localhost:8000** or your respectively-named IP address/domain name, in a browser to access the chat UI — no extra setup required.

The interface exposes both backends through two tabs:

| Tab | Endpoint | Behaviour |
|---|---|---|
| ⚡ Agent | `POST /api/v1/agent/chat` | Tool-based reasoning: fraud detection, ML predictions, SQL data queries |
| 📚 Chatbot | `POST /api/v1/chatbot/chat` | RAG streaming: policy questions, KYC, AML, PCI DSS compliance |

Each tab includes ready-to-use example prompts so you can explore the system immediately after startup. Responses are rendered as Markdown and the Chatbot tab streams tokens in real time.

---

## API reference

### Health check

```
GET /health
```

```json
{ "status": "ok" }
```

---

### Agent — tool-based reasoning

```
POST /api/v1/agent/chat
```

The agent selects the right tool (knowledge base, SQL analysis, or ML prediction) based on the query. It keeps per-user conversation history, so follow-up questions ("explain further", "what about that transaction?") are answered in context. History is persisted in SQLite and survives server restarts.

**Request:**
```json
{
  "query": "Is a $3,200 transaction at 3am from an unrecognized device high risk?",
  "user_id": 1
}
```

`user_id` is optional (defaults to `1`) and scopes the conversation thread.

**Response:**
```json
{
  "response": "Based on the fraud detection model and transaction patterns..."
}
```

---

### Chatbot — RAG with streaming

```
POST /api/v1/chatbot/chat
```

Streams the response as plain text. Uses hybrid BM25 + vector retrieval with reranking.

**Request:**
```json
{
  "query": "What are the KYC requirements for high-risk customers?",
  "user_id": 1,
  "task_id": "optional-uuid"
}
```

**Response:** `text/plain` stream

---

### Conversation history

Both the agent and the chatbot maintain independent, per-user conversation threads persisted in SQLite.

```
GET  /api/v1/agent/history/{user_id}
POST /api/v1/agent/clear-history/{user_id}
GET  /api/v1/chatbot/history/{user_id}
POST /api/v1/chatbot/clear-history/{user_id}
```

---

## Agent tools

| Tool | Description |
|---|---|
| Knowledge Base | Queries RAG index for financial policy documents |
| Fraud Data Analysis | Natural language → SQL on `transactions` table |
| Purchase Data Analysis | Natural language → SQL on `customers` table |
| Fraud Prediction | Classifies a transaction as fraudulent or not |
| Purchase Prediction | Estimates expected purchase amount for a customer |

---

## ML models

### Fraud Detector
- Algorithm: Random Forest Classifier (tuned with GridSearchCV)
- Custom features: `failed_velocity_ratio`, `velocity_failure_index`, `brute_force_warning`
- Output: binary label + fraud probability + risk level

### Purchase Predictor
- Algorithm: Random Forest Regressor
- Input: 25+ customer profile features
- Output: predicted purchase amount (USD)

Both models are serialized to `.joblib` and loaded at startup — no runtime training.

---

## Configuration

The only required configuration is a `.env` file in the project root:

```
GEMINI_CHATBOT_API_KEY=your_api_key_here
```

`init_app.py` creates this file for you during setup.

Model and retrieval parameters can be adjusted in [app/services/Rag_llm/llm_config.py](app/services/Rag_llm/llm_config.py):

```python
DEFAULT_REMOTE_LLM_MODEL   = "gemini-3.1-flash-lite"
DEFAULT_REMOTE_EMBED_MODEL = "BAAI/bge-small-en-v1.5"
DEFAULT_RERANKER_MODEL     = "cross-encoder/ms-marco-MiniLM-L12-v2"
DEFAULT_RERANKER_TOP_N     = 3
```

---

## Development notes

- The ChromaDB vector store and SQLite database are gitignored. Run `init_app.py` to regenerate them locally.
- The RAG index is built once by `init_app.py`; production workers load it read-only.
- Chatbot history is stored in SQLite (`query_chatbots_logs`) and reconstructed per user on each request, making it safe to run multiple Uvicorn workers.
- Agent history is stored in a separate SQLite table (`agent_logs`). On first message after a restart, the agent replays the user's prior turns from the database into its working memory, so context survives restarts.
- Semantic caching (3-day TTL) avoids redundant LLM calls for similar queries.

---

## License

MIT
