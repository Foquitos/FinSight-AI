from pydantic_settings import BaseSettings
from llama_index.core import Settings as LlamaIndexSettings
from llama_index.llms.gemini import Gemini

class Settings(BaseSettings):
    GEMINI_CHATBOT_API_KEY: str | None = None
    
    class Config:
        env_file = '.env'
        env_file_encoding = 'utf-8'
        extra = 'ignore'

settings = Settings()

# Inicializamos el LLM globalmente para LlamaIndex
if settings.GEMINI_CHATBOT_API_KEY:
    LlamaIndexSettings.llm = Gemini(
        model="models/gemini-3.1-flash-lite",
        api_key=settings.GEMINI_CHATBOT_API_KEY
    )
