from fastapi import FastAPI , Depends
from sqlalchemy import text
from sqlalchemy.orm import Session
from fastapi.middleware.cors import CORSMiddleware
from .database import Base, engine , get_db
from .config import settings

# Auto-create database tables
Base.metadata.create_all(bind=engine)

app = FastAPI(title="AdaptiLearn Backend")

origins = [settings.FRONTEND_URL] if settings.FRONTEND_URL else ["*"]

app.add_middleware(
    CORSMiddleware,
    allow_origins=origins,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


@app.get("/")
def home():
    return {"message": "AdaptiLearn Backend is running"}

@app.get("/test-db")
def test_database_connection(db: Session = Depends(get_db)):
    try:
        db.execute(text("SELECT 1"))
        return {"status": "✅ Database connected successfully"}
    except Exception as e:
        return {"status": "❌ Database connection failed", "error": str(e)}
