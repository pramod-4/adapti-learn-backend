from fastapi import FastAPI , Depends
from sqlalchemy import text , inspect
from sqlalchemy.orm import Session
from fastapi.middleware.cors import CORSMiddleware
from .database import Base, engine , get_db
from .config import settings
from .routers import auth





# models.Base.metadata.create_all(bind=engine)

app = FastAPI(title="AdaptiLearn Backend")

origins = [settings.FRONTEND_URL] if settings.FRONTEND_URL else ["*"]
print(f"CORS Origins: {origins}")


app.add_middleware(
    CORSMiddleware,
    allow_origins=origins,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(auth.router)

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
    
@app.get("/check-tables")
def check_tables():
    inspector = inspect(engine)
    tables = inspector.get_table_names()
    return {"tables": tables}
