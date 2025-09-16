from dotenv import load_dotenv
load_dotenv()

from fastapi import FastAPI
from contextlib import asynccontextmanager
from .api import api_router
from .config import settings
from .knowledge_graph.retriever import KnowledgeGraphRetriever
from .logger import logger

# Global retriever instance
retriever = None

@asynccontextmanager
async def lifespan(app: FastAPI):
    # Startup
    global retriever
    logger.info("Starting Cognitive Learning Assistant...")
    retriever = KnowledgeGraphRetriever()
    logger.info("Neo4j connection established")
    yield
    # Shutdown
    if retriever:
        retriever.close()
        logger.info("Neo4j connection closed")

app = FastAPI(
    title=settings.api_title,
    version=settings.api_version,
    debug=settings.debug,
    lifespan=lifespan
)

# Register all API routers
app.include_router(api_router, prefix="/api/v1")