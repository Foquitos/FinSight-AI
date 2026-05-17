import os
import logging
from contextlib import asynccontextmanager

from fastapi import FastAPI
from fastapi.responses import FileResponse

from app.config import settings  # noqa: F401 — initializes LlamaIndex Settings as side-effect
from app.services.database.database import sqlite_engine
from app.services.agent.orchestrator import FinancialAgent
from app.services.Rag_llm.llm import finsight
from app.api.routes import agent, chatbot

logging.basicConfig(level=logging.INFO, format="%(asctime)s %(name)s %(levelname)s %(message)s")
logger = logging.getLogger(__name__)


@asynccontextmanager
async def lifespan(app: FastAPI):
    logger.info("Starting up FinSight AI...")
    app.state.agent = FinancialAgent()
    app.state.chatbot = finsight(sql_engine=sqlite_engine, read_only=True)
    logger.info("All services initialized.")
    yield
    logger.info("Shutting down FinSight AI.")


app = FastAPI(
    title="FinSight AI",
    description="Financial fraud analysis agent with RAG and ML predictions.",
    version="1.0.0",
    lifespan=lifespan,
)

app.include_router(agent.router, prefix="/api/v1")
app.include_router(chatbot.router, prefix="/api/v1")

_FRONTEND = os.path.join(os.path.dirname(__file__), "..", "frontend", "index.html")


@app.get("/", include_in_schema=False)
def frontend():
    return FileResponse(_FRONTEND)


@app.get("/health", tags=["Health"])
def health():
    return {"status": "ok"}
