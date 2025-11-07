import os
from dotenv import load_dotenv

load_dotenv()

class Settings:
    DATABASE_URL = os.getenv("DATABASE_URL","")
    FRONTEND_URL = os.getenv("FRONTEND_URL")

settings = Settings()
