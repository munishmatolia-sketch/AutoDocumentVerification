"""Authentication and authorization utilities for the API."""

import logging
from datetime import datetime, timedelta
from typing import Optional, Dict, Any

from fastapi import Depends, HTTPException, status
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
from jose import JWTError, jwt
from passlib.context import CryptContext
from pydantic import BaseModel

from ..core.config import settings

logger = logging.getLogger(__name__)

# Password hashing
pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")

# JWT token scheme
security = HTTPBearer()

# Token configuration
ALGORITHM = "HS256"
ACCESS_TOKEN_EXPIRE_MINUTES = 30
REFRESH_TOKEN_EXPIRE_DAYS = 7


class Token(BaseModel):
    """Token response model."""
    access_token: str
    refresh_token: str
    token_type: str = "bearer"
    expires_in: int


class TokenData(BaseModel):
    """Token data model."""
    user_id: Optional[str] = None
    scopes: list[str] = []


class User(BaseModel):
    """User model."""
    user_id: str
    username: str
    email: Optional[str] = None
    is_active: bool = True
    scopes: list[str] = []


class UserInDB(User):
    """User model with hashed password."""
    hashed_password: str


# Mock user database (in production, this would be a real database)
fake_users_db = {
    "admin": {
        "user_id": "admin",
        "username": "admin",
        "email": "admin@example.com",
        "hashed_password": "$2b$12$EixZaYVK1fsbw1ZfbX3OXePaWxn96p36WQoeG6Lruj3vjPGga31lW",  # "secret"
        "is_active": True,
        "scopes": ["read", "write", "admin"]
    },
    "analyst": {
        "user_id": "analyst",
        "username": "analyst",
        "email": "analyst@example.com",
        "hashed_password": "$2b$12$EixZaYVK1fsbw1ZfbX3OXePaWxn96p36WQoeG6Lruj3vjPGga31lW",  # "secret"
        "is_active": True,
        "scopes": ["read", "write"]
    },
    "viewer": {
        "user_id": "viewer",
        "username": "viewer",
        "email": "viewer@example.com",
        "hashed_password": "$2b$12$EixZaYVK1fsbw1ZfbX3OXePaWxn96p36WQoeG6Lruj3vjPGga31lW",  # "secret"
        "is_active": True,
        "scopes": ["read"]
    }
}


def verify_password(plain_password: str, hashed_password: str) -> bool:
    """Verify a password against its hash."""
    return pwd_context.verify(plain_password, hashed_password)


def get_password_hash(password: str) -> str:
    """Generate password hash."""
    return pwd_context.hash(password)


def get_user(username: str) -> Optional[UserInDB]:
    """Get user from database."""
    if username in fake_users_db:
        user_dict = fake_users_db[username]
        return UserInDB(**user_dict)
    return None


def authenticate_user(username: str, password: str) -> Optional[UserInDB]:
    """Authenticate user credentials."""
    user = get_user(username)
    if not user:
        return None
    if not verify_password(password, user.hashed_password):
        return None
    return user


def create_access_token(data: Dict[str, Any], expires_delta: Optional[timedelta] = None) -> str:
    """Create JWT access token."""
    to_encode = data.copy()
    if expires_delta:
        expire = datetime.utcnow() + expires_delta
    else:
        expire = datetime.utcnow() + timedelta(minutes=ACCESS_TOKEN_EXPIRE_MINUTES)
    
    to_encode.update({"exp": expire, "type": "access"})
    encoded_jwt = jwt.encode(to_encode, settings.secret_key, algorithm=ALGORITHM)
    return encoded_jwt


def create_refresh_token(data: Dict[str, Any]) -> str:
    """Create JWT refresh token."""
    to_encode = data.copy()
    expire = datetime.utcnow() + timedelta(days=REFRESH_TOKEN_EXPIRE_DAYS)
    to_encode.update({"exp": expire, "type": "refresh"})
    encoded_jwt = jwt.encode(to_encode, settings.secret_key, algorithm=ALGORITHM)
    return encoded_jwt


def verify_token(token: str, token_type: str = "access") -> Optional[TokenData]:
    """Verify and decode JWT token."""
    try:
        payload = jwt.decode(token, settings.secret_key, algorithms=[ALGORITHM])
        
        # Check token type
        if payload.get("type") != token_type:
            return None
        
        user_id: str = payload.get("sub")
        scopes: list = payload.get("scopes", [])
        
        if user_id is None:
            return None
        
        return TokenData(user_id=user_id, scopes=scopes)
    
    except JWTError:
        return None


async def get_current_user(credentials: HTTPAuthorizationCredentials = Depends(security)) -> User:
    """Get current authenticated user."""
    credentials_exception = HTTPException(
        status_code=status.HTTP_401_UNAUTHORIZED,
        detail="Could not validate credentials",
        headers={"WWW-Authenticate": "Bearer"},
    )
    
    token_data = verify_token(credentials.credentials)
    if token_data is None:
        raise credentials_exception
    
    user = get_user(token_data.user_id)
    if user is None:
        raise credentials_exception
    
    if not user.is_active:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Inactive user"
        )
    
    return User(
        user_id=user.user_id,
        username=user.username,
        email=user.email,
        is_active=user.is_active,
        scopes=user.scopes
    )


async def get_current_active_user(current_user: User = Depends(get_current_user)) -> User:
    """Get current active user."""
    if not current_user.is_active:
        raise HTTPException(status_code=400, detail="Inactive user")
    return current_user


class RequireScopes:
    """Dependency class for requiring specific scopes."""
    
    def __init__(self, *required_scopes: str):
        self.required_scopes = required_scopes
    
    def __call__(self, current_user: User = Depends(get_current_active_user)) -> User:
        """Check if user has required scopes."""
        if not any(scope in current_user.scopes for scope in self.required_scopes):
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail=f"Operation requires one of: {', '.join(self.required_scopes)}"
            )
        return current_user


# Common permission dependencies
require_read = RequireScopes("read", "write", "admin")
require_write = RequireScopes("write", "admin")
require_admin = RequireScopes("admin")


def create_token_pair(user: UserInDB) -> Token:
    """Create access and refresh token pair."""
    access_token_expires = timedelta(minutes=ACCESS_TOKEN_EXPIRE_MINUTES)
    
    token_data = {
        "sub": user.user_id,
        "scopes": user.scopes,
        "username": user.username
    }
    
    access_token = create_access_token(
        data=token_data,
        expires_delta=access_token_expires
    )
    
    refresh_token = create_refresh_token(data=token_data)
    
    return Token(
        access_token=access_token,
        refresh_token=refresh_token,
        expires_in=ACCESS_TOKEN_EXPIRE_MINUTES * 60
    )


async def refresh_access_token(refresh_token: str) -> Optional[Token]:
    """Refresh access token using refresh token."""
    token_data = verify_token(refresh_token, token_type="refresh")
    if token_data is None:
        return None
    
    user = get_user(token_data.user_id)
    if user is None or not user.is_active:
        return None
    
    return create_token_pair(user)