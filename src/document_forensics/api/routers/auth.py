"""Authentication router for the document forensics API."""

import logging
from typing import Dict, Any

from fastapi import APIRouter, Depends, HTTPException, status, Request
from fastapi.security import OAuth2PasswordRequestForm
from pydantic import BaseModel
from slowapi import Limiter
from slowapi.util import get_remote_address

from ..auth import (
    authenticate_user, create_token_pair, refresh_access_token,
    Token, User, get_current_active_user
)
from ..exceptions import AuthenticationError

logger = logging.getLogger(__name__)
router = APIRouter()
limiter = Limiter(key_func=get_remote_address)


class LoginRequest(BaseModel):
    """Login request model."""
    username: str
    password: str


class RefreshRequest(BaseModel):
    """Token refresh request model."""
    refresh_token: str


class UserResponse(BaseModel):
    """User response model."""
    user_id: str
    username: str
    email: str
    is_active: bool
    scopes: list[str]


@router.post("/login", response_model=Token)
@limiter.limit("5/minute")
async def login(request: Request, form_data: OAuth2PasswordRequestForm = Depends()):
    """
    Authenticate user and return JWT tokens.
    
    Rate limited to 5 attempts per minute per IP address.
    """
    try:
        user = authenticate_user(form_data.username, form_data.password)
        if not user:
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Incorrect username or password",
                headers={"WWW-Authenticate": "Bearer"},
            )
        
        if not user.is_active:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Inactive user account"
            )
        
        token_pair = create_token_pair(user)
        
        logger.info(f"User {user.username} logged in successfully")
        return token_pair
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Login error: {str(e)}")
        raise AuthenticationError("Login failed")


@router.post("/refresh", response_model=Token)
@limiter.limit("10/minute")
async def refresh_token(request: Request, refresh_request: RefreshRequest):
    """
    Refresh access token using refresh token.
    
    Rate limited to 10 attempts per minute per IP address.
    """
    try:
        new_token_pair = await refresh_access_token(refresh_request.refresh_token)
        if not new_token_pair:
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Invalid refresh token"
            )
        
        logger.info("Token refreshed successfully")
        return new_token_pair
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Token refresh error: {str(e)}")
        raise AuthenticationError("Token refresh failed")


@router.get("/me", response_model=UserResponse)
async def get_current_user_info(current_user: User = Depends(get_current_active_user)):
    """Get current user information."""
    return UserResponse(
        user_id=current_user.user_id,
        username=current_user.username,
        email=current_user.email or "",
        is_active=current_user.is_active,
        scopes=current_user.scopes
    )


@router.post("/logout")
async def logout(current_user: User = Depends(get_current_active_user)):
    """
    Logout user (client-side token invalidation).
    
    Note: In a production system, you would maintain a token blacklist
    or use shorter-lived tokens with a token store.
    """
    logger.info(f"User {current_user.username} logged out")
    return {"message": "Successfully logged out"}


@router.get("/permissions")
async def get_user_permissions(current_user: User = Depends(get_current_active_user)):
    """Get current user's permissions and scopes."""
    return {
        "user_id": current_user.user_id,
        "scopes": current_user.scopes,
        "permissions": {
            "can_read": "read" in current_user.scopes or "write" in current_user.scopes or "admin" in current_user.scopes,
            "can_write": "write" in current_user.scopes or "admin" in current_user.scopes,
            "can_admin": "admin" in current_user.scopes,
            "can_upload": "write" in current_user.scopes or "admin" in current_user.scopes,
            "can_analyze": "write" in current_user.scopes or "admin" in current_user.scopes,
            "can_batch_process": "write" in current_user.scopes or "admin" in current_user.scopes
        }
    }