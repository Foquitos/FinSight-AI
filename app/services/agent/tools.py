import pandas as pd
from llama_index.core.tools import FunctionTool
from app.services.Rag_llm.llm import finsight
from app.services.database.database import sqlite_engine
from app.services.data_analysis.analyser import data_analyser
from app.services.ml.predictor import FraudPredictor_instance, PurchasePredictor_instance
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
def analyze_fraud_dataset(query: str) -> str:
    """
    USE THIS TOOL to analyze the TRANSACTION FRAUD dataset.
    This dataset contains information about specific transactions, merchant risk, 
    IP reputation, transaction velocities, failed attempts, and fraud labels.
    Query example: "What is the average transaction amount for fraudulent transactions?"
    """
    try:
        return data_analyser.query_fraud_data(query)
    except Exception as e:
        return f"Error querying fraud data: {str(e)}"

def analyze_purchase_dataset(query: str) -> str:
    """
    USE THIS TOOL to analyze the CUSTOMER PURCHASE dataset.
    This dataset contains information about customer demographics, membership tiers 
    (Gold, Silver, Platinum), loyalty points, income brackets, and spending patterns.
    Query example: "Compare purchase patterns between Gold and Silver membership tiers"
    """
    try:
        return data_analyser.query_purchase_data(query)
    except Exception as e:
        return f"Error querying purchase data: {str(e)}"

tool_fraud_analysis = FunctionTool.from_defaults(fn=analyze_fraud_dataset)
tool_purchase_analysis = FunctionTool.from_defaults(fn=analyze_purchase_dataset)


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
agent_tools = [tool_knowledge, tool_fraud_analysis, tool_purchase_analysis, tool_fraud_prediction, tool_purchase_prediction]