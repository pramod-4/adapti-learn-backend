
from datetime import datetime, timedelta
from typing import Optional
from jose import JWTError, jwt
from passlib.context import CryptContext

from src.config import settings
from src.auth.model import Token, TokenData
from src.entities.user import UserInDB
from src.exceptions import AuthenticationError
from src.logger import logger


class AuthService:
    """Authentication service for JWT tokens and password hashing"""
    
    def __init__(self):
        self.pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")
        self.secret_key = settings.SECRET_KEY
        self.algorithm = settings.JWT_ALGORITHM
        self.expire_minutes = settings.JWT_EXPIRE_MINUTES
    
    def hash_password(self, password: str) -> str:
        """Hash password"""
        return self.pwd_context.hash(password)
    
    def verify_password(self, plain_password: str, hashed_password: str) -> bool:
        """Verify password against hash"""
        return self.pwd_context.verify(plain_password, hashed_password)
    
    def create_access_token(self, user: UserInDB) -> Token:
        """Create JWT access token"""
        expire = datetime.utcnow() + timedelta(minutes=self.expire_minutes)
        
        payload = {
            "user_id": str(user.id),
            "email": user.email,
            "role": user.role,
            "exp": expire,
            "iat": datetime.utcnow()
        }
        
        encoded_jwt = jwt.encode(payload, self.secret_key, algorithm=self.algorithm)
        
        return Token(
            access_token=encoded_jwt,
            expires_in=self.expire_minutes * 60
        )
    
    def verify_token(self, token: str) -> TokenData:
        """Verify and decode JWT token"""
        try:
            payload = jwt.decode(token, self.secret_key, algorithms=[self.algorithm])
            user_id: str = payload.get("user_id")
            email: str = payload.get("email")
            
            if user_id is None or email is None:
                raise AuthenticationError("Invalid token payload")
            
            return TokenData(user_id=user_id, email=email)
        
        except JWTError as e:
            logger.warning(f"JWT verification failed: {e}")
            raise AuthenticationError("Could not validate credentials")
    
    def authenticate_user(self, user: Optional[UserInDB], password: str) -> Optional[UserInDB]:
        """Authenticate user with password"""
        if not user:
            return None
        if not self.verify_password(password, user.hashed_password):
            return None
        return user


# Global auth service instance
auth_service = AuthService()