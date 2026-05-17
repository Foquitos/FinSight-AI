import asyncio
import logging
from typing import Optional

import sqlalchemy
from sqlalchemy import text

from llama_index.core import Settings
from llama_index.core.agent.workflow import ReActAgent
from llama_index.core.workflow import Context
from llama_index.core.memory import ChatMemoryBuffer
from llama_index.core.llms import ChatMessage, MessageRole

from app.services.ml.transformers import FraudFeatureEngineer, IncomeBracketParser
from app.services.agent.tools import agent_tools

logger = logging.getLogger(__name__)


class FinancialAgent:
    """
    Orchestrator that wraps the workflow-based ReActAgent for the fraud analyst.
    Maintains per-user conversation context so the agent behaves like a chatbot.
    """

    SYSTEM_PROMPT = """You are an advanced AI Financial Assistant designed for fraud analysts at Lovelytics.
You maintain the full conversation history of each session and can refer to previous exchanges
when answering follow-up questions (e.g. "what about that transaction?" or "explain further").

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
- When you use the Knowledge Base Tool, ALWAYS preserve its "Sources" line
  (the list of document filenames) verbatim at the end of your answer, so the
  analyst can audit exactly which financial documents the answer came from.
"""

    # How many previous turns to replay into the agent's working memory.
    HISTORY_LIMIT = 20

    def __init__(self, sql_engine: Optional[sqlalchemy.engine.base.Engine] = None):
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
        self.sql_engine = sql_engine
        # Per-user workflow contexts — each Context holds the live conversation
        # memory. The source of truth across restarts is the agent_logs table.
        self._user_contexts: dict[int, Context] = {}
        self._loop = asyncio.new_event_loop()

    # ── Persistence helpers ────────────────────────────────────────────────

    def _load_history_rows(self, user_id: int) -> list:
        """Returns [(query, response), ...] for a user, oldest first."""
        if not self.sql_engine:
            return []
        try:
            with self.sql_engine.connect() as conn:
                rows = conn.execute(
                    text("""
                        SELECT query, response
                        FROM agent_logs
                        WHERE user_id = :uid AND active = 1
                        ORDER BY date DESC, id DESC
                        LIMIT :limit
                    """),
                    {"uid": user_id, "limit": self.HISTORY_LIMIT},
                ).fetchall()
            return list(reversed(rows))
        except Exception as e:
            logger.error(f"Error loading agent history for user {user_id}: {e}")
            return []

    def _save_turn(self, user_id: int, query: str, response: str) -> None:
        if not self.sql_engine:
            return
        try:
            with self.sql_engine.begin() as conn:
                conn.execute(
                    text("""
                        INSERT INTO agent_logs (user_id, query, response)
                        VALUES (:uid, :q, :r)
                    """),
                    {"uid": user_id, "q": query, "r": response},
                )
        except Exception as e:
            logger.error(f"Error saving agent turn for user {user_id}: {e}")

    async def _get_context(self, user_id: int) -> Context:
        """
        Returns the user's workflow context, creating it on first use.
        When created, the conversation is replayed from the database so the
        agent keeps prior context even after a server restart.
        """
        ctx = self._user_contexts.get(user_id)
        if ctx is not None:
            return ctx

        ctx = Context(self.agent)
        rows = self._load_history_rows(user_id)
        if rows:
            messages: list[ChatMessage] = []
            for q, r in rows:
                if q:
                    messages.append(ChatMessage(role=MessageRole.USER, content=str(q)))
                if r:
                    messages.append(ChatMessage(role=MessageRole.ASSISTANT, content=str(r)))
            memory = ChatMemoryBuffer.from_defaults(chat_history=messages, token_limit=3000)
            await ctx.store.set("memory", memory)
            logger.info(f"Restored {len(rows)} prior turn(s) for user {user_id} from DB.")
        else:
            logger.info(f"Created fresh conversation context for user {user_id}.")

        self._user_contexts[user_id] = ctx
        return ctx

    # ── Public API ─────────────────────────────────────────────────────────

    async def achat(self, user_query: str, user_id: int = 1) -> str:
        """Async entry point — preferred. Passes the user's persistent context to the agent."""
        logger.info(f"[user={user_id}] Processing: {user_query[:80]}")
        ctx = await self._get_context(user_id)
        try:
            handler = self.agent.run(ctx=ctx, user_msg=user_query)
            response = await handler
            response_str = str(response)
        except Exception as e:
            logger.error(f"Error during agent execution: {e}")
            return f"I'm sorry, an error occurred while processing the request: {e}"

        self._save_turn(user_id, user_query, response_str)
        return response_str

    async def get_history(self, user_id: int) -> list[dict]:
        """
        Returns the conversation the agent takes into account, read from the
        database so it survives restarts. The stored responses are already the
        clean final answers (the ReAct scratchpad is never persisted).
        """
        history: list[dict] = []
        for q, r in self._load_history_rows(user_id):
            if q:
                history.append({"role": "user", "content": str(q)})
            if r:
                history.append({"role": "bot", "content": str(r)})
        return history

    def clear_history(self, user_id: int) -> None:
        """Drops the in-memory context and soft-deletes the user's DB history."""
        self._user_contexts.pop(user_id, None)
        if not self.sql_engine:
            return
        try:
            with self.sql_engine.begin() as conn:
                conn.execute(
                    text("UPDATE agent_logs SET active = 0 WHERE user_id = :uid"),
                    {"uid": user_id},
                )
            logger.info(f"Cleared agent history for user {user_id}.")
        except Exception as e:
            logger.error(f"Error clearing agent history for user {user_id}: {e}")

    def chat(self, user_query: str, user_id: int = 1) -> str:
        """Sync wrapper for environments that aren't async."""
        return self._loop.run_until_complete(self.achat(user_query, user_id))


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