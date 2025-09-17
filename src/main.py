
import asyncio
from contextlib import asynccontextmanager
from fastapi import FastAPI, HTTPException, Depends, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.middleware.trustedhost import TrustedHostMiddleware
from fastapi.responses import JSONResponse
import time

from src.config import settings
from src.logger import logger
from src.database.core import db_manager
from src.database.postgres import postgres_repo
from src.database.neo4j import neo4j_repo
from src.exceptions import TutoringSystemException

# Import routers
from src.api.graph_api import router as knowledge_router
from src.auth.controller import auth_controller
from src.cognitive.analyzer import cognitive_analyzer
from src.llm_core.interface import llm_interface
from src.llm_core.prompt_builder import prompt_builder
from src.feedback.tracker import feedback_tracker
from src.feedback.recommender import recommendation_engine

# Import API models
from src.api.models import (
    QueryRequest, TutoringResponse, FeedbackRequest, 
    ProfileResponse, RecommendationsResponse, HealthCheckResponse
)
from src.entities.user import UserInDB, UserCreate
from src.auth.model import LoginRequest, Token


@asynccontextmanager
async def lifespan(app: FastAPI):
    """Application lifespan manager"""
    # Startup
    logger.info("Starting Cognitive-Aware Adaptive Tutoring System")
    
    try:
        # Initialize databases
        await db_manager.initialize_all()
        
        # Create database tables
        await postgres_repo.create_tables()
        await neo4j_repo.create_constraints()
        
        # Check LLM providers
        health = await llm_interface.health_check()
        logger.info(f"LLM providers status: {health}")
        
        logger.info("System startup completed successfully")
        
    except Exception as e:
        logger.error(f"Startup failed: {e}")
        raise
    
    yield
    
    # Shutdown
    logger.info("Shutting down system")
    await db_manager.close_all()
    logger.info("System shutdown completed")


# Create FastAPI app
app = FastAPI(
    title=settings.APP_NAME,
    version=settings.APP_VERSION,
    description="AI-powered adaptive tutoring system for Computer Science education",
    lifespan=lifespan
)

# Add middleware
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # Configure properly for production
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.add_middleware(TrustedHostMiddleware, allowed_hosts=["*"])

# Request timing middleware
@app.middleware("http")
async def add_process_time_header(request: Request, call_next):
    start_time = time.time()
    response = await call_next(request)
    process_time = time.time() - start_time
    response.headers["X-Process-Time"] = str(process_time)
    return response

# Exception handlers
@app.exception_handler(TutoringSystemException)
async def tutoring_exception_handler(request: Request, exc: TutoringSystemException):
    logger.error(f"Tutoring system error: {exc.message} - Details: {exc.details}")
    return JSONResponse(
        status_code=400,
        content={"error": exc.message, "details": exc.details}
    )

@app.exception_handler(Exception)
async def general_exception_handler(request: Request, exc: Exception):
    logger.error(f"Unhandled exception: {str(exc)}", exc_info=True)
    return JSONResponse(
        status_code=500,
        content={"error": "Internal server error", "details": str(exc) if settings.DEBUG else "An unexpected error occurred"}
    )

# Include routers
app.include_router(knowledge_router, prefix=settings.API_PREFIX)

# Authentication endpoints
@app.post(f"{settings.API_PREFIX}/auth/register", response_model=Token, tags=["Authentication"])
async def register(user_data: UserCreate):
    """Register new user"""
    return await auth_controller.register_user(user_data)

@app.post(f"{settings.API_PREFIX}/auth/login", response_model=Token, tags=["Authentication"])
async def login(login_data: LoginRequest):
    """User login"""
    return await auth_controller.login_user(login_data)

# Main tutoring endpoint
@app.post(f"{settings.API_PREFIX}/query", response_model=TutoringResponse, tags=["Tutoring"])
async def process_query(
    query_request: QueryRequest,
    current_user: UserInDB = Depends(auth_controller.get_current_user)
):
    """Main tutoring query processing endpoint"""
    try:
        start_time = time.time()
        user_id = str(current_user.id)
        
        # Step 1: Analyze cognitive behavior
        logger.info(f"Processing query from user {user_id}")
        cognitive_profile = await cognitive_analyzer.analyze_interaction(
            user_id=user_id,
            query=query_request.query,
            domain=query_request.domain.value if query_request.domain else None,
            session_metadata=query_request.context
        )
        
        # Step 2: Search knowledge graph
        from src.entities.knowledge import SearchQuery
        search_query = SearchQuery(
            query_text=query_request.query,
            domain_filter=query_request.domain,
            limit=5
        )
        
        search_results = await neo4j_repo.search_concepts(search_query)
        
        # Step 3: Build context for LLM
        context = {
            "concepts": [result.concept for result in search_results],
            "prerequisites": search_results[0].prerequisites if search_results else [],
            "related_concepts": search_results[0].related_concepts if search_results else [],
            "domain": query_request.domain.value if query_request.domain else "Computer Science",
            "main_concept": search_results[0].concept.concept_name if search_results else None,
            "difficulty_level": search_results[0].concept.difficulty_level if search_results else 3
        }
        
        # Step 4: Generate adaptive prompt and get LLM response
        messages = await prompt_builder.build_adaptive_prompt(
            user_query=query_request.query,
            cognitive_profile=cognitive_profile,
            context=context
        )
        
        llm_response = await llm_interface.generate_response(messages)
        
        # Step 5: Build response
        processing_time = time.time() - start_time
        
        response = TutoringResponse(
            content=llm_response.content,
            format_type="adaptive_explanation",
            difficulty_level=context.get("difficulty_level", 3),
            estimated_read_time=max(1, len(llm_response.content.split()) // 200),
            follow_up_suggestions=_generate_follow_up_suggestions(cognitive_profile, context),
            concepts_referenced=[c.concept_name for c in context["concepts"][:3]],
            prerequisites=[p.concept_name for p in context["prerequisites"][:3]],
            related_topics=[r.concept_name for r in context["related_concepts"][:3]],
            response_time=processing_time,
            model_used=llm_response.model_used,
            confidence_score=cognitive_profile.confidence
        )
        
        # Step 6: Record interaction for analytics
        await postgres_repo.record_interaction(
            user_id=user_id,
            query=query_request.query,
            response=llm_response.content[:1000],  # Truncate for storage
            domain=query_request.domain.value if query_request.domain else "General",
            response_time=processing_time,
            session_id=query_request.session_id
        )
        
        logger.info(f"Query processed successfully for user {user_id} in {processing_time:.2f}s")
        return response
        
    except Exception as e:
        logger.error(f"Query processing failed for user {current_user.id}: {e}")
        raise HTTPException(status_code=500, detail=f"Query processing failed: {str(e)}")

def _generate_follow_up_suggestions(cognitive_profile, context) -> list:
    """Generate follow-up suggestions based on profile and context"""
    suggestions = []
    
    if cognitive_profile.active_vs_passive > 0.6:
        suggestions.extend([
            "Can you show me a practical example?",
            "How would you implement this?",
            "What are the trade-offs involved?"
        ])
    else:
        suggestions.extend([
            "Can you explain this in simpler terms?",
            "What should I study next?",
            "Are there any prerequisites I should know?"
        ])
    
    return suggestions[:3]

# Profile management endpoints
@app.get(f"{settings.API_PREFIX}/profile", response_model=ProfileResponse, tags=["Profile"])
async def get_profile(current_user: UserInDB = Depends(auth_controller.get_current_user)):
    """Get user's cognitive profile"""
    try:
        profile = await postgres_repo.get_cognitive_profile(str(current_user.id))
        if not profile:
            raise HTTPException(status_code=404, detail="Profile not found")
        
        # Interpret learning style
        learning_style = "Active Detailed" if (profile.active_vs_passive > 0.6 and profile.overview_vs_detailed > 0.6) else "Balanced"
        
        return ProfileResponse(
            active_vs_passive=profile.active_vs_passive,
            fast_vs_slow=profile.fast_vs_slow,
            overview_vs_detailed=profile.overview_vs_detailed,
            long_vs_short=profile.long_vs_short,
            confidence=profile.confidence,
            interaction_count=profile.interaction_count,
            learning_style=learning_style
        )
        
    except Exception as e:
        logger.error(f"Failed to get profile for user {current_user.id}: {e}")
        raise HTTPException(status_code=500, detail="Failed to retrieve profile")

# Feedback endpoint
@app.post(f"{settings.API_PREFIX}/feedback", tags=["Feedback"])
async def submit_feedback(
    feedback: FeedbackRequest,
    current_user: UserInDB = Depends(auth_controller.get_current_user)
):
    """Submit feedback on system response"""
    try:
        from src.feedback.tracker import InteractionFeedback
        
        feedback_obj = InteractionFeedback(
            interaction_id=feedback.interaction_id,
            user_id=str(current_user.id),
            rating=feedback.rating,
            feedback_type=feedback.feedback_type,
            comments=feedback.comments
        )
        
        success = await feedback_tracker.record_interaction_feedback(feedback_obj)
        
        if success:
            return {"message": "Feedback recorded successfully"}
        else:
            raise HTTPException(status_code=500, detail="Failed to record feedback")
            
    except Exception as e:
        logger.error(f"Failed to record feedback: {e}")
        raise HTTPException(status_code=500, detail="Failed to process feedback")

# Recommendations endpoint
@app.get(f"{settings.API_PREFIX}/recommendations", response_model=RecommendationsResponse, tags=["Recommendations"])
async def get_recommendations(current_user: UserInDB = Depends(auth_controller.get_current_user)):
    """Get personalized learning recommendations"""
    try:
        recommendations = await recommendation_engine.get_personalized_recommendations(str(current_user.id))
        
        return RecommendationsResponse(**recommendations)
        
    except Exception as e:
        logger.error(f"Failed to get recommendations for user {current_user.id}: {e}")
        raise HTTPException(status_code=500, detail="Failed to generate recommendations")

# Health check endpoint
@app.get(f"{settings.API_PREFIX}/health", response_model=HealthCheckResponse, tags=["System"])
async def health_check():
    """System health check"""
    try:
        # Check database connections
        postgres_status = "healthy"
        redis_status = "healthy" 
        neo4j_status = "healthy"
        
        try:
            async with db_manager.get_postgres_connection() as conn:
                await conn.fetchval("SELECT 1")
        except:
            postgres_status = "unhealthy"
        
        try:
            await db_manager.redis.ping()
        except:
            redis_status = "unhealthy"
        
        try:
            async with db_manager.get_neo4j_session() as session:
                await session.run("RETURN 1")
        except:
            neo4j_status = "unhealthy"
        
        # Check LLM providers
        llm_status = await llm_interface.health_check()
        
        # Determine overall status
        all_components = [postgres_status, redis_status, neo4j_status] + list(llm_status.values())
        overall_status = "healthy" if all(status != "unhealthy" for status in all_components) else "unhealthy"
        
        return HealthCheckResponse(
            status=overall_status,
            components={
                "postgres": postgres_status,
                "redis": redis_status,
                "neo4j": neo4j_status,
                **{f"llm_{provider}": "healthy" if healthy else "unhealthy" 
                   for provider, healthy in llm_status.items()}
            },
            version=settings.APP_VERSION
        )
        
    except Exception as e:
        logger.error(f"Health check failed: {e}")
        return HealthCheckResponse(
            status="unhealthy",
            components={"error": str(e)},
            version=settings.APP_VERSION
        )

# Root endpoint
@app.get("/")
async def root():
    """Root endpoint"""
    return {
        "message": "Cognitive-Aware Adaptive Tutoring System",
        "version": settings.APP_VERSION,
        "status": "running"
    }

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(
        "src.main:app",
        host=settings.HOST,
        port=settings.PORT,
        reload=settings.DEBUG,
        log_level=settings.LOG_LEVEL.lower()
    )