import pandas as pd
from llama_index.experimental.query_engine import PandasQueryEngine

class FinancialDataAnalyser:
    def __init__(self):
        self.df_fraud = pd.read_csv('data/fraud_dataset.csv')
        self.df_purchase = pd.read_csv('data/product_purchase_dataset.csv')
        
        self.fraud_query_engine = PandasQueryEngine(df=self.df_fraud, verbose=True)
        self.purchase_query_engine = PandasQueryEngine(df=self.df_purchase, verbose=True)

    def query_fraud_data(self, query: str) -> str:
        """Execute a query on the fraud dataset."""
        response = self.fraud_query_engine.query(query)
        return str(response)

    def query_purchase_data(self, query: str) -> str:
        """Execute a query on the purchase dataset."""
        response = self.purchase_query_engine.query(query)
        return str(response)

# Global instance of the FinancialDataAnalyser to be used across the application
data_analyser = FinancialDataAnalyser()