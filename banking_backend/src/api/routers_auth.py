from typing import Optional

from fastapi import APIRouter, Depends, HTTPException, status
from fastapi.security import OAuth2PasswordBearer, OAuth2PasswordRequestForm
import asyncpg
from jose import JWTError

from .schemas import Token, User
from .security import create_access_token, verify_password
from .db import get_connection

router = APIRouter(prefix="/auth", tags=["auth"])

oauth2_scheme = OAuth2PasswordBearer(tokenUrl="/auth/login")


async def _get_user_by_username(conn: asyncpg.Connection, username: str) -> Optional[asyncpg.Record]:
    return await conn.fetchrow("SELECT id, username, password_hash, created_at FROM users WHERE username=$1", username)


# PUBLIC_INTERFACE
@router.post("/login", response_model=Token, summary="Login and get JWT", description="Authenticate user with username and password to receive a JWT access token.")
async def login(form_data: OAuth2PasswordRequestForm = Depends(), conn: asyncpg.Connection = Depends(get_connection)) -> Token:
    """Login endpoint using OAuth2PasswordRequestForm for compatibility."""
    user = await _get_user_by_username(conn, form_data.username)
    if not user or not verify_password(form_data.password, user["password_hash"]):
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Incorrect username or password")
    token = create_access_token(subject=user["username"])
    return Token(access_token=token, token_type="bearer")


async def get_current_user(token: str = Depends(oauth2_scheme), conn: asyncpg.Connection = Depends(get_connection)) -> User:
    """Resolve and return the current user from the JWT token."""
    from .security import decode_access_token
    try:
        payload = decode_access_token(token)
        username: str = payload.get("sub")  # type: ignore
        if username is None:
            raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Invalid token")
    except JWTError:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Invalid token")
    record = await _get_user_by_username(conn, username)
    if not record:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="User not found")
    return User(id=record["id"], username=record["username"], created_at=record["created_at"])


# PUBLIC_INTERFACE
@router.get("/me", response_model=User, summary="Get current user", description="Return details of the authenticated user.")
async def me(user: User = Depends(get_current_user)) -> User:
    """Return the current authenticated user's information."""
    return user
