import pandas as pd
from llama_index.core.tools import FunctionTool
from app.services.Rag_llm.llm import finsight
from app.services.database.database import sqlite_engine
from app.services.data_analysis.analyser import data_analyser
from app.services.ml.predictor import FraudPredictor_instance, PurchasePredictor_instance
from typing import Optional

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

def predict_transaction_fraud(
    transaction_amount: float, 
    merchant_category: Optional[str] = None, 
    is_international: Optional[int] = None, 
    hour_of_day: Optional[int] = None, 
    account_age_days: Optional[int] = None
) -> str:
    """
    Use this tool when the user asks to predict if a specific transaction is fraudulent.
    Example: "Predict if a $1250 purchase at an electronics store, international, at 3am from a 60-day old account is fraud."
    
    Args:
        transaction_amount (float): The transaction amount (e.g., 1250.0).
        merchant_category (str): The merchant category (e.g., 'electronics', 'grocery').
        is_international (int): 1 if international, 0 if domestic.
        hour_of_day (int): The hour of the transaction (0-23).
        account_age_days (int): How many days the account has been open.
    """
    # 1. Define an "Average Transaction/Customer" (Baseline) to prevent model errors
    baseline_data = {
        "customer_age": 35,
        "transaction_type": "purchase",
        "country": "USA",
        "transaction_velocity_24h": 2,
        "failed_transactions_24h": 0,
        "num_transactions_7d": 10,
        "ip_reputation_score": 0.85,
        "account_balance": 5000.0,
        "debt_to_income_ratio": 0.3,
        "is_recurring": 0,
        "cvv_match": 1,
        "shipping_address_match": 1,
        "device_type": "mobile",
        "credit_limit": 10000.0,
        "card_present": 0,
        "day_of_week": 3,
        "num_transactions_24h": 3,
        "previous_fraud_reports": 0,
        "avg_transaction_amount_30d": 200.0,
        "merchant_risk_score": 0.20,
        "distance_from_last_transaction_km": 5.0,
        "customer_risk_score": 0.10,
        "distance_from_home_km": 10.0,
        "billing_address_match": 1,
        "transaction_amount": 100.0, 
        "merchant_category": "grocery",
        "is_international": 0,
        "hour_of_day": 12,
        "account_age_days": 365
    }
    
    if transaction_amount is not None:
        baseline_data["transaction_amount"] = transaction_amount
        
    if merchant_category is not None:
        baseline_data["merchant_category"] = merchant_category.lower()
        
    if is_international is not None:
        baseline_data["is_international"] = is_international
        
    if hour_of_day is not None:
        baseline_data["hour_of_day"] = hour_of_day
        
    if account_age_days is not None:
        baseline_data["account_age_days"] = account_age_days
    
    try:
        result = FraudPredictor_instance.predict(baseline_data)
        
        status = "Fraudulent" if result.get('is_fraud', False) else "Legitimate"
        probability = result.get('fraud_probability', 0.0) * 100
        
        return f"Prediction Result: The transaction appears to be {status} with a fraud probability of {probability:.2f}%."
    except Exception as e:
        return f"Error executing the fraud prediction model: {str(e)}"

tool_fraud_prediction = FunctionTool.from_defaults(fn=predict_transaction_fraud)


# ==========================================
# 2. Purchase Prediction Tool (Regression)
# ==========================================
def predict_customer_purchase(
    age: Optional[int] = None, 
    membership_tier: Optional[str] = None, 
    num_transactions_last_month: Optional[int] = None,
    preferred_category: Optional[str] = None
) -> str:
    """
    Use this tool to predict the EXPECTED PURCHASE AMOUNT for a single customer.
    Example: "Calculate the expected purchase amount for a 45-year-old Platinum customer with 20 transactions who prefers electronics."
    
    Args:
        age (int): The age of the customer.
        membership_tier (str): The tier (e.g., 'gold', 'silver', 'platinum', 'bronze').
        num_transactions_last_month (int): Transactions made in the last month.
        preferred_category (str): Their preferred category (e.g., 'electronics', 'fashion', 'home_goods').
    """
    # 1. Define an "Average Customer" based on product_purchase_dataset.csv
    baseline_data = {
        "gender": "F",
        "income_bracket": "60000-80000",
        "customer_tenure_days": 1000,
        "num_transactions_last_year": 120,
        "avg_transaction_value": 250.0,
        "total_spent_last_year": 30000.0,
        "preferred_payment_method": "credit_card",
        "last_purchase_days_ago": 7,
        "cart_abandonment_rate": 0.15,
        "customer_satisfaction_score": 4.5,
        "loyalty_points": 5000,
        "email_engagement_rate": 0.50,
        "mobile_app_user": 1,
        "social_media_follower": 1,
        "location_type": "urban",
        "distance_to_nearest_store_km": 5.0,
        "has_credit_card": 1,
        "has_children": 1,
        "occupation_category": "professional",
        "education_level": "bachelors",
        "marital_status": "married",
        "owns_home": 1,
        "num_customer_service_contacts": 2,
        "product_return_rate": 0.08,
        "age": 35,
        "membership_tier": "silver",
        "num_transactions_last_month": 10,
        "preferred_category": "home_goods"
    }
    
    if age is not None:
        baseline_data["age"] = age
        
    if membership_tier is not None:
        baseline_data["membership_tier"] = membership_tier.lower()
        
    if num_transactions_last_month is not None:
        baseline_data["num_transactions_last_month"] = num_transactions_last_month
        
    if preferred_category is not None:
        baseline_data["preferred_category"] = preferred_category.lower()
    
    try:
        prediction_result = PurchasePredictor_instance.predict(baseline_data)
        predicted_amount = prediction_result.get("predicted_purchase_amount", 0.0)
        
        return f"Prediction Result: The expected purchase amount for this customer profile is ${predicted_amount:.2f}."
    except Exception as e:
        return f"Error executing the purchase regression model: {str(e)}"

tool_purchase_prediction = FunctionTool.from_defaults(fn=predict_customer_purchase)
# ==========================================
# Export all tools
# ==========================================
agent_tools = [tool_knowledge, tool_fraud_analysis, tool_purchase_analysis, tool_fraud_prediction, tool_purchase_prediction]