
from typing import List, Optional, Dict, Any
from datetime import datetime
import asyncpg
import json

from src.database.core import db_manager
from src.entities.user import User, UserCreate, UserInDB, UserUpdate
from src.entities.profile import CognitiveProfile, ProfileAnalytics
from src.exceptions import DatabaseError
from src.logger import logger


class PostgreSQLRepository:
    """PostgreSQL repository for user data and cognitive profiles"""
    
    async def create_tables(self):
        """Create database tables"""
        async with db_manager.get_postgres_connection() as conn:
            # Users table
            await conn.execute("""
                CREATE TABLE IF NOT EXISTS users (
                    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
                    email VARCHAR(255) UNIQUE NOT NULL,
                    full_name VARCHAR(255) NOT NULL,
                    hashed_password VARCHAR(255) NOT NULL,
                    role VARCHAR(50) NOT NULL DEFAULT 'student',
                    academic_level VARCHAR(50),
                    preferred_domains JSONB DEFAULT '[]',
                    is_active BOOLEAN DEFAULT true,
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    last_active TIMESTAMP
                )
            """)
            
            # Cognitive profiles table
            await conn.execute("""
                CREATE TABLE IF NOT EXISTS cognitive_profiles (
                    user_id UUID PRIMARY KEY REFERENCES users(id) ON DELETE CASCADE,
                    active_vs_passive FLOAT DEFAULT 0.5,
                    fast_vs_slow FLOAT DEFAULT 0.5,
                    overview_vs_detailed FLOAT DEFAULT 0.5,
                    long_vs_short FLOAT DEFAULT 0.5,
                    confidence FLOAT DEFAULT 0.1,
                    interaction_count INTEGER DEFAULT 0,
                    avg_session_duration FLOAT,
                    avg_questions_per_session FLOAT,
                    preferred_difficulty_level INTEGER,
                    last_updated TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
                )
            """)
            
            # User sessions table
            await conn.execute("""
                CREATE TABLE IF NOT EXISTS user_sessions (
                    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
                    user_id UUID NOT NULL REFERENCES users(id) ON DELETE CASCADE,
                    session_token VARCHAR(255) UNIQUE NOT NULL,
                    started_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    ended_at TIMESTAMP,
                    is_active BOOLEAN DEFAULT true
                )
            """)
            
            # Interactions table
            await conn.execute("""
                CREATE TABLE IF NOT EXISTS interactions (
                    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
                    user_id UUID NOT NULL REFERENCES users(id) ON DELETE CASCADE,
                    session_id UUID REFERENCES user_sessions(id),
                    query_text TEXT NOT NULL,
                    response_text TEXT,
                    domain VARCHAR(100),
                    response_time FLOAT,
                    satisfaction_rating INTEGER,
                    metadata JSONB DEFAULT '{}',
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
                )
            """)
            
            logger.info("Database tables created successfully")
    
    # User operations
    async def create_user(self, user: UserCreate, hashed_password: str) -> UserInDB:
        """Create new user"""
        async with db_manager.get_postgres_connection() as conn:
            try:
                row = await conn.fetchrow("""
                    INSERT INTO users (email, full_name, hashed_password, role, academic_level, preferred_domains)
                    VALUES ($1, $2, $3, $4, $5, $6)
                    RETURNING *
                """, user.email, user.full_name, hashed_password, user.role.value,
                    user.academic_level.value if user.academic_level else None,
                    json.dumps([d.value for d in user.preferred_domains]))
                
                return UserInDB(**dict(row))
            except asyncpg.UniqueViolationError:
                raise DatabaseError("User with this email already exists")
    
    async def get_user_by_email(self, email: str) -> Optional[UserInDB]:
        """Get user by email"""
        async with db_manager.get_postgres_connection() as conn:
            row = await conn.fetchrow("SELECT * FROM users WHERE email = $1", email)
            return UserInDB(**dict(row)) if row else None
    
    async def get_user_by_id(self, user_id: str) -> Optional[User]:
        """Get user by ID"""
        async with db_manager.get_postgres_connection() as conn:
            row = await conn.fetchrow("SELECT * FROM users WHERE id = $1", user_id)
            return User(**dict(row)) if row else None
    
    async def update_user(self, user_id: str, user_update: UserUpdate) -> Optional[User]:
        """Update user"""
        async with db_manager.get_postgres_connection() as conn:
            update_data = user_update.dict(exclude_unset=True)
            if not update_data:
                return await self.get_user_by_id(user_id)
            
            # Build dynamic query
            set_clauses = []
            values = []
            for i, (key, value) in enumerate(update_data.items(), 2):
                if key == 'preferred_domains':
                    value = json.dumps([d.value for d in value])
                elif hasattr(value, 'value'):
                    value = value.value
                set_clauses.append(f"{key} = ${i}")
                values.append(value)
            
            query = f"""
                UPDATE users SET {', '.join(set_clauses)}
                WHERE id = $1 RETURNING *
            """
            
            row = await conn.fetchrow(query, user_id, *values)
            return User(**dict(row)) if row else None
    
    async def update_last_active(self, user_id: str):
        """Update user's last active timestamp"""
        async with db_manager.get_postgres_connection() as conn:
            await conn.execute(
                "UPDATE users SET last_active = CURRENT_TIMESTAMP WHERE id = $1",
                user_id
            )
    
    # Cognitive profile operations
    async def create_cognitive_profile(self, user_id: str, profile: CognitiveProfile) -> CognitiveProfile:
        """Create cognitive profile for user"""
        async with db_manager.get_postgres_connection() as conn:
            await conn.execute("""
                INSERT INTO cognitive_profiles 
                (user_id, active_vs_passive, fast_vs_slow, overview_vs_detailed, 
                 long_vs_short, confidence, interaction_count, avg_session_duration,
                 avg_questions_per_session, preferred_difficulty_level)
                VALUES ($1, $2, $3, $4, $5, $6, $7, $8, $9, $10)
            """, user_id, profile.active_vs_passive, profile.fast_vs_slow,
                profile.overview_vs_detailed, profile.long_vs_short, profile.confidence,
                profile.interaction_count, profile.avg_session_duration,
                profile.avg_questions_per_session, profile.preferred_difficulty_level)
            
            return profile
    
    async def get_cognitive_profile(self, user_id: str) -> Optional[CognitiveProfile]:
        """Get user's cognitive profile"""
        async with db_manager.get_postgres_connection() as conn:
            row = await conn.fetchrow(
                "SELECT * FROM cognitive_profiles WHERE user_id = $1", user_id
            )
            return CognitiveProfile(**dict(row)) if row else None
    
    async def update_cognitive_profile(self, user_id: str, profile: CognitiveProfile) -> CognitiveProfile:
        """Update cognitive profile"""
        async with db_manager.get_postgres_connection() as conn:
            await conn.execute("""
                UPDATE cognitive_profiles SET
                    active_vs_passive = $2,
                    fast_vs_slow = $3,
                    overview_vs_detailed = $4,
                    long_vs_short = $5,
                    confidence = $6,
                    interaction_count = $7,
                    avg_session_duration = $8,
                    avg_questions_per_session = $9,
                    preferred_difficulty_level = $10,
                    last_updated = CURRENT_TIMESTAMP
                WHERE user_id = $1
            """, user_id, profile.active_vs_passive, profile.fast_vs_slow,
                profile.overview_vs_detailed, profile.long_vs_short, profile.confidence,
                profile.interaction_count, profile.avg_session_duration,
                profile.avg_questions_per_session, profile.preferred_difficulty_level)
            
            return profile
    
    async def record_interaction(self, user_id: str, query: str, response: str, 
                               domain: str, response_time: float, 
                               session_id: Optional[str] = None,
                               metadata: Optional[Dict[str, Any]] = None) -> str:
        """Record user interaction"""
        async with db_manager.get_postgres_connection() as conn:
            interaction_id = await conn.fetchval("""
                INSERT INTO interactions 
                (user_id, session_id, query_text, response_text, domain, response_time, metadata)
                VALUES ($1, $2, $3, $4, $5, $6, $7)
                RETURNING id
            """, user_id, session_id, query, response, domain, response_time,
                json.dumps(metadata or {}))
            
            return str(interaction_id)


# Global repository instance
postgres_repo = PostgreSQLRepository()