
from contextlib import asynccontextmanager
from typing import AsyncGenerator
import asyncpg
import redis.asyncio as redis
from neo4j import AsyncGraphDatabase, AsyncDriver

from src.config import settings
from src.logger import logger
from src.exceptions import DatabaseError


class DatabaseManager:
    """Centralized database connection manager"""
    
    def __init__(self):
        self._postgres_pool: Optional[asyncpg.Pool] = None
        self._redis_client: Optional[redis.Redis] = None
        self._neo4j_driver: Optional[AsyncDriver] = None
    
    async def initialize_postgres(self):
        """Initialize PostgreSQL connection pool"""
        try:
            self._postgres_pool = await asyncpg.create_pool(
                settings.postgres_url,
                min_size=5,
                max_size=20,
                command_timeout=60
            )
            logger.info("PostgreSQL connection pool initialized")
        except Exception as e:
            logger.error(f"Failed to initialize PostgreSQL: {e}")
            raise DatabaseError(f"PostgreSQL initialization failed: {e}")
    
    async def initialize_redis(self):
        """Initialize Redis connection"""
        try:
            self._redis_client = redis.from_url(
                settings.redis_url,
                encoding="utf-8",
                decode_responses=True
            )
            await self._redis_client.ping()
            logger.info("Redis connection initialized")
        except Exception as e:
            logger.error(f"Failed to initialize Redis: {e}")
            raise DatabaseError(f"Redis initialization failed: {e}")
    
    async def initialize_neo4j(self):
        """Initialize Neo4j connection"""
        try:
            self._neo4j_driver = AsyncGraphDatabase.driver(
                settings.NEO4J_URI,
                auth=(settings.NEO4J_USER, settings.NEO4J_PASSWORD)
            )
            # Test connection
            async with self._neo4j_driver.session() as session:
                await session.run("RETURN 1")
            logger.info("Neo4j connection initialized")
        except Exception as e:
            logger.error(f"Failed to initialize Neo4j: {e}")
            raise DatabaseError(f"Neo4j initialization failed: {e}")
    
    async def initialize_all(self):
        """Initialize all database connections"""
        await self.initialize_postgres()
        await self.initialize_redis()
        await self.initialize_neo4j()
    
    @asynccontextmanager
    async def get_postgres_connection(self) -> AsyncGenerator[asyncpg.Connection, None]:
        """Get PostgreSQL connection from pool"""
        if not self._postgres_pool:
            raise DatabaseError("PostgreSQL pool not initialized")
        
        async with self._postgres_pool.acquire() as conn:
            yield conn
    
    @property
    def redis(self) -> redis.Redis:
        """Get Redis client"""
        if not self._redis_client:
            raise DatabaseError("Redis client not initialized")
        return self._redis_client
    
    @asynccontextmanager
    async def get_neo4j_session(self):
        """Get Neo4j session"""
        if not self._neo4j_driver:
            raise DatabaseError("Neo4j driver not initialized")
        
        async with self._neo4j_driver.session() as session:
            yield session
    
    async def close_all(self):
        """Close all database connections"""
        if self._postgres_pool:
            await self._postgres_pool.close()
            logger.info("PostgreSQL pool closed")
        
        if self._redis_client:
            await self._redis_client.close()
            logger.info("Redis connection closed")
        
        if self._neo4j_driver:
            await self._neo4j_driver.close()
            logger.info("Neo4j driver closed")


# Global database manager instance
db_manager = DatabaseManager()
