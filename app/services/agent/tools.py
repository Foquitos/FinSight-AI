import pandas as pd
from llama_index.core.tools import FunctionTool
from app.services.Rag_llm.llm import finsight
from app.services.database.database import sqlite_engine
# from app.services.ml.predictor import FraudPredictor, PurchasePredictor (To be implemented)

# ==========================================
# 1. RAG Tool (Knowledge Base)
# ==========================================
knowledge_bot = finsight(sql_engine=sqlite_engine, read_only=False)

def query_knowledge_base(question: str) -> str:
    """
    USE EXCLUSIVELY to answer theoretical questions, definitions, 
    procedures, and financial regulations (e.g., fraud, AML, KYC, PCI DSS).
    DO NOT use this tool to analyze transaction data or predict metrics.
    """
    result = knowledge_bot.query(query_text=question, user_id=1, task_id="agent")
    return result["response"]

tool_knowledge = FunctionTool.from_defaults(fn=query_knowledge_base)


# ==========================================
# 2. Data Analysis Tool (CSVs)
# ==========================================
def analyze_csv_data(query: str) -> str:
    """
    Useful for obtaining statistics, averages, and counts regarding 
    transaction and customer purchase datasets.
    Use it when the user asks "what is the average", "how many transactions", 
    "compare groups", etc.
    """
    # NOTE: You can implement a LlamaIndex PandasQueryEngine here 
    # or write a simple function that uses pandas to return the answer.
    # df = pd.read_csv('data/fraud_dataset.csv')
    # ... pandas logic ...
    
    return "Pandas analysis result... (To be implemented)"

tool_data_analysis = FunctionTool.from_defaults(fn=analyze_csv_data)


# ==========================================
# 3. Prediction Tools (ML Models)
# ==========================================
def predict_fraud(amount: float, merchant_category: str, is_international: bool, customer_age: int) -> str:
    """
    Useful for predicting the fraud probability of a SINGLE specific transaction.
    You must extract the parameters (amount, category, is_international, and age) 
    from the user's question.
    """
    # Implementation example:
    # predictor = FraudPredictor('app/models/fraud_model.pkl')
    # pred = predictor.predict(amount, merchant_category, is_international, customer_age)
    
    return f"Simulation: The ${amount} transaction has an 85% probability of being fraudulent."

tool_fraud_prediction = FunctionTool.from_defaults(fn=predict_fraud)


# ==========================================
# 3. Prediction Tools (ML Models)
# ==========================================
def predict_purchase_amount(amount: float, merchant_category: str, is_international: bool, customer_age: int) -> str:
    """
    Useful for predicting the purchase amount of a SINGLE specific transaction.
    You must extract the parameters (amount, category, is_international, and age) 
    from the user's question.
    """
    # Implementation example:
    # predictor = FraudPredictor('app/models/fraud_model.pkl')
    # pred = predictor.predict(amount, merchant_category, is_international, customer_age)
    
    return f"Simulation: The ${amount} transaction has an 85% probability of being fraudulent."

tool_purchase_prediction = FunctionTool.from_defaults(fn=predict_purchase_amount)
# ==========================================
# Export all tools
# ==========================================
agent_tools = [tool_knowledge, tool_data_analysis, tool_fraud_prediction, tool_purchase_prediction]