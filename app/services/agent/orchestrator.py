from llama_index.core.agent import ReActAgent
from llama_index.core import Settings
from app.services.agent.tools import agent_tools
import logging

logger = logging.getLogger(__name__)

class FinancialAgent:
    """
    Orchestrator class that initializes the ReAct Agent with the 
    necessary tools for the fraud analyst.
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
        
        # Ensure the global LLM (Gemini) is configured in LlamaIndex
        if not Settings.llm:
            raise ValueError("Global LLM is not configured. Ensure LlamaIndex is initialized first.")
            
        # Create the Agent
        self.agent = ReActAgent.from_tools( # type: ignore[reportAttributeAccessIssue]
            tools=agent_tools,
            llm=Settings.llm,
            system_prompt=self.SYSTEM_PROMPT,
            verbose=True, # Crucial: Shows the Thought, Action, Observation process
            max_iterations=10 # Prevents infinite loops
        )
        
    def chat(self, user_query: str) -> str:
        """
        Main method to communicate with the agent.
        """
        logger.info(f"Processing user query: {user_query}")
        try:
            response = self.agent.chat(user_query)
            return str(response)
        except Exception as e:
            logger.error(f"Error during agent execution: {e}")
            return f"I'm sorry, an error occurred while processing the request: {str(e)}"

# ==========================================
# Helper function for quick testing
# ==========================================
if __name__ == "__main__":
    # Import your main config settings here to ensure Gemini is ready
    # from app.config import settings
    
    orchestrator = FinancialAgent()
    
    print("\n--- TEST 1: Theoretical Question (Should use RAG) ---")
    response_1 = orchestrator.chat("What are the common indicators of credit card fraud?")
    print(response_1)
    
    print("\n--- TEST 2: ML Prediction (Should use tool_fraud_prediction) ---")
    response_2 = orchestrator.chat("Predict if this transaction is fraudulent: $1,250 purchase at electronics store, international, 3am, from a 2-month-old account.")
    print(response_2)

    print("\n--- TEST 3: Purchase Prediction (Should use tool_purchase_prediction) ---")
    response_3 = orchestrator.chat("Predict the purchase amount for this customer: $500 purchase at clothing store, domestic, 2pm, from a 1-year-old account.")
    print(response_3)