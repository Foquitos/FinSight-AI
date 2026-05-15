import pandas as pd
import numpy as np
import joblib
import os

class FraudPredictor:
    def __init__(self):
        """
        Inicializa el predictor cargando el modelo entrenado y la estructura 
        de columnas esperada para garantizar la consistencia en inferencia.
        """
        # obtain the current directory of this file to build paths to the model and columns
        current_dir = os.path.dirname(os.path.abspath(__file__))
        
        # routes to the model and expected columns (these files should have been created during training)
        model_path = os.path.join(current_dir, '../models/fraud_rf_model.joblib')
        columns_path = os.path.join(current_dir, '../models/fraud_model_columns.joblib')
        
        # load the model and expected columns
        self.model = joblib.load(model_path)
        self.expected_columns = joblib.load(columns_path)

    def predict(self, transaction_data: dict) -> dict:
        """
        Receives a dictionary with transaction data (coming from the Agent), applies Feature Engineering, aligns columns, and returns the prediction.
        """
        # 1. convert the input dictionary to a DataFrame (the model expects a DataFrame as input)
        df_input = pd.DataFrame([transaction_data])
        
        # 2. apply the same feature engineering steps as during training (only if the relevant columns are present in the input)
        if 'transaction_velocity_24h' in df_input.columns and 'failed_transactions_24h' in df_input.columns:
            df_input['failed_velocity_ratio'] = df_input['failed_transactions_24h'] / (df_input['transaction_velocity_24h'] + 1)
            df_input['velocity_failure_index'] = df_input['transaction_velocity_24h'] * df_input['failed_transactions_24h']
            df_input['brute_force_warning'] = np.where(
                (df_input['transaction_velocity_24h'] >= 3) & (df_input['failed_transactions_24h'] >= 2), 1, 0
            )
            
        # 3. Codify variables categóricas (One-Hot Encoding)
        df_encoded = pd.get_dummies(df_input)
        
        # 4. align columns with the model's expected input
        # a only transaction won't have all categories (e.g. if it's from "USA", the "Canada" column will be missing).
        # reindex refills with 0 the missing columns that the model does expect to see.
        df_final = df_encoded.reindex(columns=self.expected_columns, fill_value=0)
        
        # 5. Generate the prediction and probability of fraud
        prediction = self.model.predict(df_final)[0]
        probability = self.model.predict_proba(df_final)[0][1] # Probabilidad de ser fraude (clase 1)
        
        # 6. Estructure the result for llm
        return {
            "is_fraud": bool(prediction == 1),
            "fraud_probability": round(float(probability), 4),
            "risk_level": "High" if probability > 0.7 else ("Medium" if probability > 0.4 else "Low"),
            "status": "Fraudulent" if prediction == 1 else "Legitimate"
        }

# Example usage (this would be removed in production, but is useful for testing the predictor in isolation)
if __name__ == "__main__":
    predictor = FraudPredictor()
    
    # simulate a transaction input (this would come from the Agent in production)
    sample_transaction = {
        "customer_age": 45,
        "account_age_days": 60,
        "transaction_amount": 1250,
        "merchant_category": "electronics",
        "country": "USA",
        "is_international": 1,
        "transaction_velocity_24h": 4,
        "failed_transactions_24h": 3,
    }
    
    result = predictor.predict(sample_transaction)
    print("Resultado de la predicción:", result)