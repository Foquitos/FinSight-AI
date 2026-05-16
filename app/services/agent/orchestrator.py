import asyncio
import logging

from llama_index.core import Settings
from llama_index.core.agent.workflow import ReActAgent

from app.services.ml.transformers import FraudFeatureEngineer, IncomeBracketParser
from app.services.agent.tools import agent_tools

logger = logging.getLogger(__name__)


class FinancialAgent:
    """
    Orchestrator that wraps the workflow-based ReActAgent for the fraud analyst.
    """

    SYSTEM_PROMPT = """You are an advanced AI Financial Assistant designed for fraud analysts at Lovelytics.
Your goal is to answer complex questions by breaking them down and using the appropriate tools.

You have access to:
1. Knowledge Base Tool: For reading documentation about financial policies, KYC, AML, and PCI DSS.
2. Data Analysis Tool: To query databases and CSVs for aggregations, averages, and historical data.
3. Prediction Tools: To evaluate specific transactions or customer behaviors using Machine Learning.

Rules:
- ALWAYS think step-by-step.
- If a user asks a complex question (e.g., "Analyze customer X and tell me if their recent transaction is fraud based on our policies"), you must:
    Step 1: Use Data Analysis to get the customer's transaction history.
    Step 2: Use the Prediction tool to check the specific transaction.
    Step 3: Use the Knowledge Base to check policy alignment.
- Be precise, analytical, and professional.
"""

    def __init__(self):
        logger.info("Initializing the ReAct Financial Agent...")

        if not Settings.llm:
            raise ValueError("Global LLM is not configured. Ensure LlamaIndex is initialized first.")

        self.agent = ReActAgent(
            tools=agent_tools,
            llm=Settings.llm,
            system_prompt=self.SYSTEM_PROMPT,
            verbose=False,
            max_iterations=10,
        )
        self._loop = asyncio.new_event_loop()

    async def achat(self, user_query: str) -> str:
        """Async entry point — preferred."""
        logger.info(f"Processing user query: {user_query}")
        try:
            handler = self.agent.run(user_query)
            response = await handler
            return str(response)
        except Exception as e:
            logger.error(f"Error during agent execution: {e}")
            return f"I'm sorry, an error occurred while processing the request: {e}"

    def chat(self, user_query: str) -> str:
        """Sync wrapper for environments that aren't async."""
        return self._loop.run_until_complete(self.achat(user_query))


# ==========================================
# Helper function for quick testing
# ==========================================
if __name__ == "__main__":
    from app.config import settings 

    async def _run_tests():
        orchestrator = FinancialAgent()

        print("\n--- TEST 1: Theoretical Question (Should use RAG) ---")
        print(await orchestrator.achat("What are the common indicators of credit card fraud?"))

        print("\n--- TEST 2: ML Prediction (Should use tool_fraud_prediction) ---")
        print(await orchestrator.achat(
            "Predict if this transaction is fraudulent: $1,250 purchase at electronics store, "
            "international, 3am, from a 2-month-old account."
        ))

        print("\n--- TEST 3: Purchase Prediction (Should use tool_purchase_prediction) ---")
        print(await orchestrator.achat(
            """What's the expected purchase amount for a 45-year-old customer with
            Platinum membership who made 20 transactions last month in the Home
            category?"""
        ))
        
        print("\n--- TEST 4: Data Analysis Questions ---")
        print(await orchestrator.achat(
            """How many international transactions are in the dataset?"""
        ))
        
        print("\n--- TEST 5: Data Analysis Questions ---")
        print(await orchestrator.achat(
            """How many transactions had more than 3 failed attempts in 24 hours?"""
        ))
        
        print("\n--- TEST 6: Complex Analytical Questions: ---")
        print(await orchestrator.achat(
            """Which transactions look suspicious and why? Show me the top 5 with
            explanations"""
        ))

    asyncio.run(_run_tests())