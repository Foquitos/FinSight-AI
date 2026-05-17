# FinSight AI — Architecture & Design Document

## 1. Overview

FinSight AI is a prototype conversational assistant for financial fraud analysts. The system was designed to answer three fundamentally different types of questions from a single natural-language interface:

| Question type | Example | Mechanism |
|---|---|---|
| Data analysis | "How many international transactions are in the dataset?" | NL → SQL via LlamaIndex |
| ML prediction | "Is this $1,250 transaction fraudulent?" | Serialized scikit-learn pipeline |
| Policy knowledge | "What are the KYC requirements for high-risk customers?" | RAG over markdown documents |

The core design challenge was integrating these three heterogeneous backends under a single agent that can route queries, chain tools when needed, and maintain conversational context.

---

## 2. System Architecture

### 2.1 High-level diagram

```
┌─────────────────────────────────────────────────────────────────────┐
│              Browser — FinSight UI  (GET /)                          │
│    Single-page HTML  ·  ⚡ Agent tab  ·  📚 Chatbot tab (streaming) │
└──────────────────────────────┬──────────────────────────────────────┘
                               │ HTTP / Fetch  (streaming for chatbot)
                               ▼
┌─────────────────────────────────────────────────────────────────────┐
│                        FastAPI Application                           │
│                                                                      │
│   GET  /                           (serves frontend/index.html)     │
│   POST /api/v1/agent/chat          POST /api/v1/chatbot/chat        │
│   GET  /api/v1/agent/history       GET  /api/v1/chatbot/history     │
│   POST /api/v1/agent/clear-…       POST /api/v1/chatbot/clear-…     │
│   GET  /health                                                       │
└───────────┬──────────────────────────────────┬──────────────────────┘
            │                                  │
            ▼                                  ▼
┌───────────────────────┐          ┌───────────────────────────────────┐
│   FinancialAgent       │          │   finsight (RAG Chatbot)          │
│   (ReActAgent)         │          │                                   │
│                        │          │  BM25 + Vector Hybrid Retrieval   │
│  ┌─────────────────┐  │          │  SentenceTransformer Reranker     │
│  │  Tool Router    │  │          │  Semantic Cache (3-day TTL)       │
│  └────────┬────────┘  │          │  Per-user memory (SQLite)         │
│           │            │          │  Streaming response               │
└───────────│────────────┘          └───────────────────────────────────┘
            │
     ┌──────┼──────────────────────────────────┐
     │      │                                  │
     ▼      ▼                                  ▼
┌─────────────────┐   ┌──────────────────┐   ┌───────────────────────┐
│  Knowledge Base │   │  Data Analysis   │   │   ML Predictors       │
│  Tool (RAG)     │   │  Tools (NL→SQL)  │   │                       │
│                 │   │                  │   │  FraudPredictor       │
│  ChromaDB       │   │  NLSQLTable      │   │  PurchasePredictor    │
│  (vector store) │   │  QueryEngine     │   │  (.joblib artifacts)  │
│                 │   │                  │   │                       │
│  finsight_docs/ │   │  SQLite          │   │  Random Forest        │
│  (20 md files)  │   │  (transactions + │   │  + custom sklearn     │
│                 │   │   customers)     │   │    transformers       │
└─────────────────┘   └──────────────────┘   └───────────────────────┘
                                │
                       ┌────────┘
                       ▼
              ┌─────────────────────┐
              │  Google Gemini LLM  │
              │  (gemini-3.1-flash- │
              │   lite via LlamaIndex│
              │   Settings.llm)     │
              └─────────────────────┘
```

### 2.2 Component responsibilities

**Frontend (`frontend/index.html`)** — Self-contained single-page app served by FastAPI at `GET /`. No build step or separate server is required. Implements two tabs backed by different endpoints:
- **⚡ Agent tab** — sends `POST /api/v1/agent/chat` and renders the JSON response as Markdown.
- **📚 Chatbot tab** — sends `POST /api/v1/chatbot/chat` and reads the `text/plain` stream token-by-token, progressively rendering Markdown as it arrives.

Both tabs expose pre-filled example prompts for quick exploration and auto-resize the input textarea. Markdown rendering uses `marked.js` (CDN, pinned to v9).

**FastAPI + Uvicorn** — Provides the frontend file and two independent API entry points: a tool-based agent endpoint and a streaming RAG chatbot endpoint with conversation history management.

**FinancialAgent (ReActAgent)** — LlamaIndex ReActAgent wrapper. Uses a financial system prompt to ground the LLM in the analyst domain. Dispatches to one or more tools per turn (max 10 iterations to prevent infinite loops). Exposes both async (`achat`) and sync (`chat`) interfaces.

**finsight (RAG Chatbot)** — Specialized subclass of a generic `ChatBot` base. Handles streaming, per-user memory reconstruction from SQLite, and semantic caching. The two-stage retrieval (BM25 keyword + vector similarity → cross-encoder reranker) improves precision over pure vector search without sacrificing recall on keyword-heavy regulatory queries.

**Agent Tools (5)** — Each tool is a self-contained function with a typed docstring that the ReActAgent uses as its tool schema:
- `KnowledgeBaseTool` — Queries the ChromaDB index
- `FraudDataAnalysisTool` — NL → SQL on `transactions` table
- `PurchaseDataAnalysisTool` — NL → SQL on `customers` table
- `FraudPredictionTool` — Calls `FraudPredictor.predict()`
- `PurchasePredictionTool` — Calls `PurchasePredictor.predict()`

**SQLite Database** — Four tables: `transactions` (fraud dataset), `customers` (purchase dataset), `query_chatbots_logs` (RAG chatbot history + token usage), and `agent_logs` (agent conversation history). The agent and chatbot use separate tables so their independent conversation threads never mix. Using SQLite instead of an in-memory store lets the app reconstruct conversation history across restarts and multiple Uvicorn workers.

---

## 3. Data Flow

### 3.1 Agent request (tool-based)

```
User query + user_id
  → Load/create per-user workflow Context
       (first time after restart → replay prior turns from agent_logs)
  → ReActAgent parses intent (with conversation history in context)
  → Selects tool(s) based on query type
  → Tool executes (SQL / ML inference / RAG lookup)
  → Agent synthesizes result into natural language
  → Turn persisted to agent_logs
  → Response returned to user
```

The agent can chain tools in a single turn. For example, a complex query like *"Analyze the top 5 suspicious transactions and explain the risk factors"* may trigger the fraud data analysis tool to retrieve records, then the fraud prediction tool to score each one, then the knowledge base tool to contextualize with policy language.

### 3.2 RAG chatbot request (streaming)

```
User query + user_id
  → Reconstruct conversation history from SQLite
  → Semantic cache lookup (ChromaDB similarity)
  → Cache miss → Hybrid retrieval (BM25 + vector)
  → Cross-encoder reranker selects top-3 chunks
  → LLM generates answer with retrieved context
  → Response streamed token-by-token
  → Result + tokens logged to SQLite
```

---

## 4. Model Selection & Performance

### 4.1 Fraud Detection — Binary Classification

**Dataset:** `fraud_dataset.csv` — 100 transactions, 50% fraud / 50% legitimate (synthetic, balanced).

**Model:** `RandomForestClassifier` (scikit-learn)

**Rationale:**
- **Interpretability:** Feature importance scores are natively available, which is critical in a fraud context where analysts need to understand *why* a transaction was flagged.
- **Non-linear relationships:** Fraud signals (velocity, failed attempts, international flag) interact non-linearly in ways that tree ensembles capture well without manual interaction terms.
- **Robustness:** Random Forest is resistant to outliers and requires minimal preprocessing, which accelerates prototyping and reduces the risk of pipeline bugs.
- **Baseline quality:** For a 100-row synthetic dataset, a Random Forest with tuned hyperparameters provides a reliable baseline before moving to gradient boosting (XGBoost, LightGBM) on real data.

**Custom feature engineering (`FraudFeatureEngineer` transformer):**

| Feature | Formula | Captures |
|---|---|---|
| `failed_velocity_ratio` | `failed_transactions_24h / (transaction_velocity_24h + 1)` | Failure density relative to activity |
| `velocity_failure_index` | `transaction_velocity_24h × failed_transactions_24h` | Magnitude of brute-force signal |
| `brute_force_warning` | `1 if velocity ≥ 3 AND failures ≥ 2 else 0` | Binary heuristic flag |

These features encode domain knowledge (brute-force attack patterns) directly into the pipeline, reducing the model's dependence on learning complex interactions from a small dataset.

**Training setup:**
- 80/20 stratified train/test split (`random_state=42`)
- `GridSearchCV` with `cv=3`, optimizing for **Recall** (minimizing false negatives is the priority in fraud detection — missing a fraudulent transaction is more costly than a false alarm)
- Hyperparameter grid: `n_estimators` ∈ {50, 100}, `max_depth` ∈ {None, 5, 10}, `min_samples_split` ∈ {2, 5}
- `class_weight='balanced'` to handle any residual imbalance

**Performance:**
- Cross-validation Recall: **1.00** on training set

> **Important caveat:** The perfect recall score reflects the synthetic, perfectly balanced nature of the 100-row dataset, not the model's real-world generalization ability. On a production dataset (typically <2% fraud rate, millions of rows), this model would require retraining with SMOTE or threshold calibration, and recall would drop to a realistic range. This prototype prioritizes demonstrating the *pipeline architecture* over validated model performance.

---

### 4.2 Purchase Amount Prediction — Regression

**Dataset:** `product_purchase_dataset.csv` — 100 customer records, `purchase_amount` as continuous target.

**Model:** `RandomForestRegressor` (scikit-learn)

**Rationale:**
- Same interpretability and robustness arguments as the classifier apply.
- The dataset contains a mix of numeric features (age, income, loyalty points) and categorical features (membership tier, preferred category, payment method). Random Forest handles mixed types natively after encoding.
- For a 100-row regression task, ensemble methods generalize better than linear models (which may underfit complex interactions) or deep networks (which overfit on small data).

**Custom feature engineering (`IncomeBracketParser` transformer):**

The raw `income_bracket` column stores string ranges like `"50K-100K"` or `"100K+"`. The custom transformer converts these to a single numeric estimate:
- `"50K-100K"` → midpoint `75000`
- `"100K+"` → `100000 × 1.2 = 120000` (configurable multiplier)
- Single values parsed directly

This avoids treating income brackets as unordered categorical values, which would lose the ordinal information.

**Training setup:**
- 80/20 train/test split (`random_state=42`)
- `GridSearchCV` with `cv=5`, optimizing for **neg_mean_absolute_error** (MAE chosen over RMSE because purchase amounts don't have extreme outliers that would warrant penalizing large errors more heavily)
- Hyperparameter grid: `n_estimators` ∈ {50, 100, 200}, `max_depth` ∈ {None, 10, 20}, `min_samples_split` ∈ {2, 5}, `min_samples_leaf` ∈ {1, 2}

**Evaluation metrics computed on test set:**
- Mean Absolute Error (MAE) — primary metric, same units as the target (USD)
- Root Mean Squared Error (RMSE) — penalizes large prediction errors
- R² Score — proportion of variance explained

> The full metric output is available by running `notebooks/02_purchase_model_training.ipynb`.

---

## 5. RAG Pipeline Design

### 5.1 Document processing

The 20 financial markdown documents are parsed into sentence-level chunks using LlamaIndex's ingestion pipeline. Sentence-level chunking was chosen over fixed-size chunking because financial documents contain dense, self-contained statements (e.g., a single sentence defining a KYC threshold) that should not be split mid-thought.

### 5.2 Two-stage retrieval

```
Query
  ├── BM25 (keyword index)    ─┐
  └── Vector similarity        ├─ Merge candidates
       (BAAI/bge-small-en)    ─┘
                │
                ▼
       CrossEncoder reranker
       (ms-marco-MiniLM-L12-v2)
                │
                ▼
       Top-3 chunks → LLM context
```

**Why hybrid?** Pure vector retrieval misses exact regulatory terms (e.g., "PCI DSS 3.2.1", "SAR filing threshold $10,000"). BM25 catches these keyword matches. The reranker then resolves conflicts and selects the most semantically relevant chunks from the combined candidate set.

### 5.3 Semantic caching

Before retrieval, each query is checked against previously answered queries using vector similarity. If a sufficiently similar query was answered within the last 3 days, the cached response is returned immediately — avoiding LLM inference costs entirely. This is particularly effective for a domain with repetitive regulatory questions.

---

## 6. Key Insights from the Data

**Fraud dataset (`fraud_dataset.csv`):**
- The dataset is synthetically balanced at 50% fraud / 50% legitimate. Real-world fraud rates are typically 0.1–2%, which fundamentally changes the modeling approach (threshold tuning, cost-sensitive learning, SMOTE become essential rather than optional).
- The most predictive features align with known fraud heuristics: `merchant_risk_score`, `shipping_address_match` (address mismatch), `failed_transactions_24h`, and `is_international`. These are also the features that domain experts would flag manually, which validates the model's feature importance as interpretable.
- The custom `brute_force_warning` flag (high velocity + high failures) reliably identifies credential-stuffing and card-testing patterns.

**Purchase dataset (`product_purchase_dataset.csv`):**
- Purchase amount correlates with membership tier (Platinum > Gold > Silver), income bracket, and transaction history depth — expected relationships that confirm the dataset is realistic.
- The `income_bracket` column required custom parsing because string ranges carry ordinal information that standard One-Hot Encoding would destroy.

---

## 7. Design Decisions & Trade-offs

### Local vs. cloud deployment

**Decision:** All components run locally — SQLite instead of a managed database, ChromaDB persisted to disk instead of a cloud vector store, Gemini API calls instead of a self-hosted LLM.

**Trade-off:** This eliminates cloud costs and deployment complexity for a prototype, but creates scalability ceilings. A production system would use:
- Databricks for training pipelines and MLflow for experiment tracking
- A managed vector database (Pinecone, Weaviate, or Databricks Vector Search)
- A serverless API layer (AWS Lambda / Azure Functions) for auto-scaling

### Model serialization at init time

**Decision:** ML models are trained offline in Jupyter notebooks and serialized as `.joblib` artifacts. The API loads them once at startup.

**Trade-off:** This eliminates training latency from inference (critical for a real-time agent) and makes inference deterministic. The downside is that model updates require re-running notebooks and redeploying the artifact — no online learning capability.

### Per-user memory in SQLite

**Decision:** Conversation history is persisted in SQLite, rather than held only in memory. The chatbot reconstructs its memory from `query_chatbots_logs` on every request. The agent keeps a live LlamaIndex workflow `Context` per user for low-latency follow-ups, but persists every turn to `agent_logs` and, on the first message after a restart, replays the user's prior turns from the database into a fresh `Context` memory buffer.

**Trade-off:** Persistence makes the system resilient to restarts and keeps the chatbot path safe for multiple Uvicorn workers. The agent's in-memory `Context` is per-process, so under multiple workers a user's live context is not shared across workers — but because every turn is persisted, any worker can rebuild full context from `agent_logs` on the next message. The cost is a database read when a context is first created (and per request for the chatbot). For high-concurrency production use, the in-memory layer would be replaced with Redis or a shared store.

### ReActAgent with max_iterations=10

**Decision:** The agent is capped at 10 tool calls per turn.

**Trade-off:** Prevents infinite reasoning loops and controls API cost, but may truncate genuinely complex multi-step analyses. The cap was set empirically — in practice, the agent resolves most queries in 2–4 tool calls.

### Two separate entry points (agent vs. chatbot)

**Decision:** The agent endpoint (`/api/v1/agent/chat`) and the RAG chatbot endpoint (`/api/v1/chatbot/*`) are kept separate rather than unified.

**Rationale:** The agent is stateless and tool-heavy (suited for analytical queries). The chatbot is streaming and context-aware (suited for conversational policy Q&A). Merging them would force unnecessary complexity into both. A future version could expose a single endpoint that internally routes based on query intent.

---

## 8. Future Improvements

Given more time and production requirements, the following upgrades would have the highest impact:

### Immediate (next sprint)

1. **SMOTE for imbalanced data** — The fraud model needs to be validated on realistic class distributions. Implementing `imbalanced-learn`'s SMOTE in the training pipeline and calibrating the classification threshold (not just optimizing recall) is the highest-priority model improvement.

2. **Actual metric benchmarking** — Run both notebooks against a holdout set and log metrics (classification report, ROC-AUC for fraud; MAE, RMSE, R² for purchase) to MLflow or a simple JSON artifact. The current architecture.md documents methodology but not final numbers.

3. **Input validation on ML tools** — The prediction tools currently accept free-text parameters that the LLM extracts. Adding Pydantic schema validation with sensible defaults and range checks would prevent inference errors on edge-case inputs.

### Medium-term (production readiness)

4. **Databricks migration** — Move training pipelines to Databricks notebooks with MLflow experiment tracking. Use Delta Lake for the transaction and customer datasets to support versioned, auditable data updates. Register models in MLflow Model Registry with staging/production environments.

5. **Real-time feature store** — Replace the static CSV-loaded SQLite tables with a streaming feature store (Databricks Feature Store or Feast) that ingests live transaction events via Kafka or Event Hubs. This enables genuine real-time fraud scoring rather than batch inference.

6. **Agent long-term memory** — Implement a memory module (e.g., LlamaIndex `VectorMemory`) that stores key facts extracted from past conversations (customer risk profiles, analyst notes) and retrieves them on subsequent turns. This would let the agent say "You asked about CUST7823 last week — their risk profile has changed."

7. **Evaluation harness** — Build an automated eval suite that runs the agent against a fixed set of benchmark queries (data analysis, prediction, knowledge) and checks response correctness. This is essential for catching regressions when the LLM or retrieval parameters change.

### Long-term (scale)

8. **Fraud model retraining pipeline** — Implement a drift detector (e.g., Evidently AI) that monitors incoming transaction distributions and triggers a retraining job in Databricks when feature drift exceeds a threshold.

9. **Explainability layer** — Add SHAP value computation to the `FraudPredictor` output so analysts receive not just a fraud probability but the specific features that drove the score (e.g., "international flag contributed +0.34 to fraud probability").

10. **Multi-modal input** — Extend the agent to accept document uploads (transaction reports, customer statements) and process them through the ingestion pipeline on the fly, rather than relying solely on pre-indexed documents.

---

## 9. Technology Choices Summary

| Component | Choice | Alternative considered | Reason for choice |
|---|---|---|---|
| API framework | FastAPI | Flask, Django REST | Async-native, automatic schema docs, minimal boilerplate |
| LLM | Google Gemini (flash-lite) | OpenAI GPT-4o-mini | Free tier sufficient for prototype; multimodal capability for future |
| Agent framework | LlamaIndex ReActAgent | LangChain AgentExecutor | Tighter LlamaIndex integration with query engines and RAG indices |
| Embeddings | BAAI/bge-small-en-v1.5 | OpenAI text-embedding-3-small | Runs locally, no API cost, strong benchmark performance for its size |
| Reranker | ms-marco-MiniLM-L12-v2 | Cohere Rerank | Runs locally, no API cost, cross-encoder quality for free |
| Vector store | ChromaDB | Pinecone, Weaviate | Zero infrastructure, persisted to disk, Python-native |
| Database | SQLite | PostgreSQL | No infrastructure needed, sufficient for prototype concurrency |
| ML framework | scikit-learn | XGBoost, LightGBM | Simpler pipeline API, sufficient for 100-row datasets, joblib-native |
