from sklearn.base import BaseEstimator, TransformerMixin
import pandas as pd
import numpy as np

class IncomeBracketParser(BaseEstimator, TransformerMixin):
    """
    Personalized Transformer to parse 'income_bracket' feature into a numeric format that can be used by ML models.
    It handles formats like '50K-100K', '100K+', and '50K' and converts them into a single numeric value representing the estimated income.
    - '50K-100K' -> 75000
    """
    def __init__(self, plus_multiplier=1.2):
        self.plus_multiplier = plus_multiplier

    def fit(self, X, y=None):
        return self

    def transform(self, X):
        X_copy = X.copy()
        if 'income_bracket' in X_copy.columns:
            X_copy['income_numeric'] = X_copy['income_bracket'].apply(self._parse_income)
            X_copy = X_copy.drop(columns=['income_bracket'])
        return X_copy

    def _parse_income(self, val):
        if pd.isna(val): return 0
        val_str = str(val).strip()
        if '+' in val_str:
            base_val = float(val_str.replace('+', ''))
            return base_val * self.plus_multiplier
        elif '-' in val_str:
            parts = val_str.split('-')
            try: return (float(parts[0]) + float(parts[1])) / 2.0
            except ValueError: return 0
        else:
            try: return float(val_str)
            except ValueError: return 0

class FraudFeatureEngineer(BaseEstimator, TransformerMixin):
    """
    Personaliced Transformer to apply Feature Engineering to transaction data before feeding it to the classification model.
    """
    def fit(self, X, y=None):
        return self

    def transform(self, X):
        X_copy = X.copy()
        
        if 'transaction_velocity_24h' in X_copy.columns and 'failed_transactions_24h' in X_copy.columns:
            X_copy['failed_velocity_ratio'] = X_copy['failed_transactions_24h'] / (X_copy['transaction_velocity_24h'] + 1)
            X_copy['velocity_failure_index'] = X_copy['transaction_velocity_24h'] * X_copy['failed_transactions_24h']
            X_copy['brute_force_warning'] = np.where(
                (X_copy['transaction_velocity_24h'] >= 3) & (X_copy['failed_transactions_24h'] >= 2), 1, 0
            )
            
        return X_copy