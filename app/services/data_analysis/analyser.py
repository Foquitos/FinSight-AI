import logging
from llama_index.core import SQLDatabase
from llama_index.core.query_engine import NLSQLTableQueryEngine
from app.services.database.database import sqlite_engine

logger = logging.getLogger(__name__)


class FinancialDataAnalyser:
    def __init__(self):
        self._engine = sqlite_engine
        # Query engines built lazily — Settings.llm is not ready at import time
        self._fraud_query_engine = None
        self._purchase_query_engine = None

    def _build_fraud_engine(self) -> NLSQLTableQueryEngine:
        sql_db = SQLDatabase(self._engine, include_tables=["transactions"])
        return NLSQLTableQueryEngine(sql_database=sql_db, tables=["transactions"])

    def _build_purchase_engine(self) -> NLSQLTableQueryEngine:
        sql_db = SQLDatabase(self._engine, include_tables=["customers"])
        return NLSQLTableQueryEngine(sql_database=sql_db, tables=["customers"])

    def query_fraud_data(self, query: str) -> str:
        """Execute a natural-language query on the fraud transactions table."""
        if self._fraud_query_engine is None:
            self._fraud_query_engine = self._build_fraud_engine()
        return str(self._fraud_query_engine.query(query))

    def query_purchase_data(self, query: str) -> str:
        """Execute a natural-language query on the customer purchase table."""
        if self._purchase_query_engine is None:
            self._purchase_query_engine = self._build_purchase_engine()
        return str(self._purchase_query_engine.query(query))


data_analyser = FinancialDataAnalyser()
