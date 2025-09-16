from fastapi import APIRouter

# Import individual routers
from .graph_api import router as graph_router
# from .user_api import router as user_router
# from .auth_api import router as auth_router
# from .llm_api import router as llm_router

# Main API router for the whole project
api_router = APIRouter()

# Include each module’s router
api_router.include_router(graph_router)
# api_router.include_router(user_router)
# api_router.include_router(auth_router)
# api_router.include_router(llm_router)

__all__ = ["api_router"]
