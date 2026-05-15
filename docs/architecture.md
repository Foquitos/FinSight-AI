# FinSight AI: Financial Agent Prototype

## 1. Overview
This project is a prototype of an AI-powered conversational assistant designed for financial fraud analysts. The system acts as an intelligent orchestrator capable of querying structured databases for data analysis, executing real-time Machine Learning inferences, and retrieving domain-specific financial knowledge (e.g., KYC, PCI DSS policies) using a Retrieval-Augmented Generation (RAG) pipeline.

## 2. System Architecture
The application follows a modular, tool-based architecture:
* **Orchestrator (Agent):** The core LLM router that evaluates user intent and dispatches queries to the appropriate specialized tools.
* **Knowledge Retrieval (RAG Module):** Processes financial Markdown documents to accurately answer policy and regulatory compliance questions.
* **Predictive Analytics (ML Module):** Exposes serialized Scikit-Learn models to evaluate individual transactions for fraud risk and project customer purchase amounts.
* **Structured Query (Data Module):** An interface to query the simulated database for aggregated historical patterns and data analysis.

## 3. Model Selection & Performance
### 3.1. Fraud Detection (Binary Classification)
* **Model:** Random Forest Classifier.
* **Rationale:** Selected for its robustness against non-linear relationships, native interpretability (Feature Importance), and minimal preprocessing requirements, making it ideal for rapid prototyping.
* **Feature Engineering:** Created composite variables such as `failed_velocity_ratio` and `brute_force_warning` to capture real-world brute-force attack heuristics.
* **Metrics:** * Recall: 1.00 (Cross-Validation). 
  * *Context Note:* The perfect recall score is a byproduct of the synthetic and perfectly balanced nature (50% fraud / 50% legitimate) of the 100-row prototype dataset.

### 3.2. Purchase Prediction (Regression)
* **Model:** [PLACEHOLDER, e.g., Random Forest Regressor]
* **Rationale:** [PLACEHOLDER]
* **Metrics:** [PLACEHOLDER - e.g., MAE / RMSE]

## 4. Key Insights Discovered
* **Fraud Patterns:** Within this dataset, anomalous transactions are heavily dictated by the `merchant_risk_score` and discrepancies in shipping addresses (`shipping_address_match`).
* **Data Distribution:** The provided dataset presents an unrealistic balance (50/50). In a real-world scenario, fraud datasets are highly imbalanced (typically <2% fraud), which significantly alters the training approach.

## 5. Design Decisions & Trade-offs
* **Local vs. Cloud Deployment:** Adhering to the guideline of prioritizing documentation over costly deployments, components (LLM, Vector Store) are simulated and executed locally.
* **Model Serialization:** To optimize agent latency, ML models are not trained at runtime. Instead, they are trained offline in notebooks (`.ipynb`) and exported as static artifacts (`.joblib`).
* **Inference Column Alignment (Reindexing):** Implemented strict dataframe reindexing in the `Predictor` class. This ensures that missing categorical variables in single-transaction inferences do not break the One-Hot Encoding pipeline at runtime.

## 6. Future Improvements
Given more time and resources, the system would be upgraded with:
* **Cloud-Native Architecture:** Migrating the training pipeline to **Databricks** and utilizing MLflow for robust experiment tracking and model versioning.
* **Handling Imbalanced Data:** Implementing synthetic oversampling techniques (like SMOTE) to prepare the classification pipeline for real-world, heavily skewed data distributions.
* **Agent Memory:** Implementing short and long-term memory buffers in the orchestrator to maintain context across complex, multi-turn analytical conversations.