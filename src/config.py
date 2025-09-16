import os
from pydantic_settings import BaseSettings
from typing import Optional

class Settings(BaseSettings):
    # Neo4j Configuration
    neo4j_uri: str = os.getenv('NEO4J_URI', 'bolt://localhost:7687')
    neo4j_username: str = os.getenv('NEO4J_USERNAME', 'neo4j')
    neo4j_password: str = os.getenv('NEO4J_PASSWORD', 'password')
    neo4j_database: str = os.getenv('NEO4J_DATABASE', 'neo4j')
    
    # API Configuration
    api_title: str = "Cognitive Learning Assistant"
    api_version: str = "1.0.0"
    debug: bool = os.getenv('DEBUG', 'False').lower() == 'true'
    
    # LLM Configuration
    openai_api_key: Optional[str] = os.getenv('OPENAI_API_KEY')
    
    class Config:
        env_file = ".env"

settings = Settings()