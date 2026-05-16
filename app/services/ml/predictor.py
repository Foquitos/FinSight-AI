import pandas as pd
import joblib
import os
from app.services.ml.transformers import IncomeBracketParser, FraudFeatureEngineer

class FraudPredictor:
    def __init__(self):
        current_dir = os.path.dirname(os.path.abspath(__file__))
        model_path = os.path.join(current_dir, '../models/fraud_pipeline.joblib')
        self.model = joblib.load(model_path)

    def predict(self, transaction_data: dict) -> dict:
        df_input = pd.DataFrame([transaction_data])
        
        prediction = self.model.predict(df_input)[0]
        probability = self.model.predict_proba(df_input)[0][1] 
        
        return {
            "is_fraud": bool(prediction == 1),
            "fraud_probability": round(float(probability), 4),
            "risk_level": "High" if probability > 0.7 else ("Medium" if probability > 0.4 else "Low"),
            "status": "Fraudulent" if prediction == 1 else "Legitimate"
        }

class PurchasePredictor:
    def __init__(self):
        current_dir = os.path.dirname(os.path.abspath(__file__))
        model_path = os.path.join(current_dir, '../models/purchase_predictor.joblib')
        self.model = joblib.load(model_path)

    def predict(self, customer_data: dict) -> dict:
        df_input = pd.DataFrame([customer_data])
        
        prediction = self.model.predict(df_input)[0]
        
        return {
            "predicted_purchase_amount": round(float(prediction), 2),
            "currency": "USD",
            "message": f"The predicted purchase amount for this profile is ${round(float(prediction), 2)}"
        }

# Example usage 
if __name__ == "__main__":
    fraud_predictor = FraudPredictor()
    sample_transaction = {
        "customer_age": 45,
        "account_age_days": 60,
        "transaction_amount": 1250,
        "merchant_category": "electronics",
        "country": "USA",
        "is_international": 1,
        "transaction_velocity_24h": 4,
        "failed_transactions_24h": 3,
        "transaction_type": "purchase",      
        "num_transactions_7d": 12,
        "ip_reputation_score": 0.85,      
        "account_balance": 5000.0,
        "hour_of_day": 14,
        "debt_to_income_ratio": 0.3,
        "is_recurring": 0,
        "cvv_match": 1,
        "shipping_address_match": 1,         
        "device_type": "mobile",
        "credit_limit": 10000.0,
        "card_present": 0,
        "day_of_week": 3,
        "num_transactions_24h": 5,
        "previous_fraud_reports": 0,
        "avg_transaction_amount_30d": 150.0,
        "merchant_risk_score": 0.40,
        "distance_from_last_transaction_km": 15.5,
        "customer_risk_score": 0.50, 
        "distance_from_home_km": 120.5,
        "billing_address_match": 1
    }
    
    print("Result of Fraud Prediction:", fraud_predictor.predict(sample_transaction))
    
    
    purchase_predictor = PurchasePredictor()
    sample_customer = {
        "age": 35,
        "gender": "F",
        "income_bracket": "60000-80000",
        "customer_tenure_days": 892,
        "membership_tier": "silver",
        "num_transactions_last_month": 12,
        "num_transactions_last_year": 98,
        "avg_transaction_value": 198.45,
        "total_spent_last_year": 19448.10,
        "preferred_category": "home_goods",
        "preferred_payment_method": "debit_card",
        "last_purchase_days_ago": 8,
        "cart_abandonment_rate": 0.12,
        "customer_satisfaction_score": 4.3,
        "loyalty_points": 4560,
        "email_engagement_rate": 0.51,
        "mobile_app_user": 1,
        "social_media_follower": 0,
        "location_type": "urban",
        "distance_to_nearest_store_km": 3.5,
        "has_credit_card": 1,
        "has_children": 1,
        "occupation_category": "professional",
        "education_level": "bachelors",
        "marital_status": "married",
        "owns_home": 1,
        "num_customer_service_contacts": 3,
        "product_return_rate": 0.10
    }
    print("Result of Purchase Prediction:", purchase_predictor.predict(sample_customer))