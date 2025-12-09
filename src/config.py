import os
from dotenv import load_dotenv
from groq import Groq

load_dotenv()

class Settings:
    DATABASE_URL = os.getenv("DATABASE_URL","")
    FRONTEND_URL = os.getenv("FRONTEND_URL")
    GROQ_API_KEY = os.getenv("GROQ_API_KEY","")
    GROQ_API_KEY = os.getenv("GROQ_API_KEY", "")
    GROQ_MODEL = os.getenv("GROQ_MODEL", "openai/gpt-oss-20b")

settings = Settings()

def get_groq_client() -> Groq:
    if not settings.GROQ_API_KEY:
        raise ValueError("GROQ_API_KEY is not set in environment variables.")
    return Groq(api_key=settings.GROQ_API_KEY)