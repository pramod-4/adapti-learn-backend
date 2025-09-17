
from typing import Optional
from fastapi import Depends, HTTPException, status
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials

from src.auth.service import auth_service
from src.auth.model import TokenData, LoginRequest, Token
from src.entities.user import UserInDB, UserCreate
from src.database.postgres import postgres_repo
from src.exceptions import AuthenticationError, DatabaseError
from src.logger import logger


security = HTTPBearer()


class AuthController:
    """Authentication controller"""
    
    async def register_user(self, user_data: UserCreate) -> Token:
        """Register new user"""
        try:
            # Hash password
            hashed_password = auth_service.hash_password(user_data.password)
            
            # Create user in database
            user = await postgres_repo.create_user(user_data, hashed_password)
            
            # Create cognitive profile
            from src.cognitive.model import CognitiveProfile
            profile = CognitiveProfile()
            await postgres_repo.create_cognitive_profile(str(user.id), profile)
            
            # Generate token
            token = auth_service.create_access_token(user)
            
            logger.info(f"User registered: {user.email}")
            return token
            
        except DatabaseError as e:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=str(e)
            )
        except Exception as e:
            logger.error(f"Registration failed: {e}")
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail="Registration failed"
            )
    
    async def login_user(self, login_data: LoginRequest) -> Token:
        """Authenticate user and return token"""
        try:
            # Get user from database
            user = await postgres_repo.get_user_by_email(login_data.email)
            
            # Authenticate
            authenticated_user = auth_service.authenticate_user(user, login_data.password)
            if not authenticated_user:
                raise HTTPException(
                    status_code=status.HTTP_401_UNAUTHORIZED,
                    detail="Incorrect email or password"
                )
            
            if not authenticated_user.is_active:
                raise HTTPException(
                    status_code=status.HTTP_400_BAD_REQUEST,
                    detail="Inactive user account"
                )
            
            # Update last active
            await postgres_repo.update_last_active(str(authenticated_user.id))
            
            # Generate token
            token = auth_service.create_access_token(authenticated_user)
            
            logger.info(f"User logged in: {authenticated_user.email}")
            return token
            
        except HTTPException:
            raise
        except Exception as e:
            logger.error(f"Login failed: {e}")
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail="Login failed"
            )
    
    async def get_current_user(
        self, 
        credentials: HTTPAuthorizationCredentials = Depends(security)
    ) -> UserInDB:
        """Get current authenticated user"""
        try:
            # Verify token
            token_data = auth_service.verify_token(credentials.credentials)
            
            # Get user from database
            user = await postgres_repo.get_user_by_email(token_data.email)
            if not user:
                raise AuthenticationError("User not found")
            
            if not user.is_active:
                raise AuthenticationError("Inactive user account")
            
            return user
            
        except AuthenticationError as e:
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail=str(e),
                headers={"WWW-Authenticate": "Bearer"}
            )
        except Exception as e:
            logger.error(f"Token verification failed: {e}")
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Could not validate credentials",
                headers={"WWW-Authenticate": "Bearer"}
            )


# Global auth controller instance
auth_controller = AuthController()