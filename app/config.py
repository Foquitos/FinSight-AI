from pydantic_settings import BaseSettings

class Settings(BaseSettings):
    GEMINI_CHATBOT_API_KEY: str | None = None
    
    class Config:
        env_file = '.env'
        env_file_encoding = 'utf-8'
        extra = 'ignore'

settings = Settings()
