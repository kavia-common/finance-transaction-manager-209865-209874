import os
from typing import Optional, AsyncGenerator

from pydantic import BaseModel, Field
from dotenv import load_dotenv, find_dotenv

from contextlib import asynccontextmanager

import asyncpg

# Try to load environment from a .env if present in working dir or parents.
# This is safe in all environments and will no-op if .env is absent.
load_dotenv(find_dotenv(usecwd=True), override=False)

# Database pool singleton
_pool: Optional[asyncpg.Pool] = None


class Settings(BaseModel):
    """Application settings loaded from environment variables."""
    database_url: Optional[str] = Field(None, description="PostgreSQL connection URL")
    secret_key: Optional[str] = Field(None, description="JWT Secret key for signing tokens")
    access_token_expire_minutes: int = Field(60, description="JWT access token expiry in minutes")
    cors_allow_origins: str = Field("http://localhost:3000", description="Comma separated allowed origins for CORS")


# PUBLIC_INTERFACE
def get_settings() -> Settings:
    """Load settings from environment variables without raising at import time.

    This function reads from os.environ and an optional .env (already loaded above).
    It defers strict validation to the call sites that actually require a given setting.
    """
    database_url = os.getenv("DATABASE_URL")
    secret_key = os.getenv("SECRET_KEY")
    access_token_expire_minutes_raw = os.getenv("ACCESS_TOKEN_EXPIRE_MINUTES", "60")
    try:
        access_token_expire_minutes = int(access_token_expire_minutes_raw)
    except ValueError:
        access_token_expire_minutes = 60
    cors_allow_origins = os.getenv("CORS_ALLOW_ORIGINS", "http://localhost:3000")

    return Settings(
        database_url=database_url,
        secret_key=secret_key,
        access_token_expire_minutes=access_token_expire_minutes,
        cors_allow_origins=cors_allow_origins,
    )


def _require_database_url(settings: Settings) -> str:
    """Return a valid database URL or raise a helpful, runtime error."""
    if not settings.database_url:
        raise RuntimeError(
            "DATABASE_URL is not configured. "
            "Set it in the environment or in a .env file at banking_backend/.env. "
            "Example: DATABASE_URL=postgresql://appuser:dbuser123@localhost:5000/myapp"
        )
    return settings.database_url


def _require_secret_key(settings: Settings) -> str:
    """Return a valid secret key or raise a helpful, runtime error."""
    if not settings.secret_key:
        raise RuntimeError(
            "SECRET_KEY is not configured. "
            "Set it in the environment or in a .env file at banking_backend/.env. "
            "Example: SECRET_KEY=dev-secret-change-me"
        )
    return settings.secret_key


# PUBLIC_INTERFACE
@asynccontextmanager
async def db_pool() -> AsyncGenerator[asyncpg.Pool, None]:
    """Provide a global asyncpg pool for database operations.

    Creates the pool on first use. Raises a clear error if DATABASE_URL is missing.
    """
    global _pool
    settings = get_settings()
    database_url = _require_database_url(settings)
    if _pool is None:
        _pool = await asyncpg.create_pool(database_url, min_size=1, max_size=10)
    try:
        yield _pool
    finally:
        # Keep pool for lifespan; do not close here
        pass


# PUBLIC_INTERFACE
async def get_connection() -> AsyncGenerator[asyncpg.Connection, None]:
    """Yield a database connection from the pool for request-scoped operations.

    Ensures schema on first acquisition.
    """
    global _pool
    settings = get_settings()
    database_url = _require_database_url(settings)
    if _pool is None:
        _pool = await asyncpg.create_pool(database_url, min_size=1, max_size=10)
    async with _pool.acquire() as conn:
        # Ensure necessary tables exist (idempotent)
        await ensure_schema(conn)
        yield conn


async def ensure_schema(conn: asyncpg.Connection) -> None:
    """Create tables if they do not exist. This is idempotent and lightweight."""
    # Users table (simple demo auth: username/password stored as password hash)
    await conn.execute(
        """
        CREATE TABLE IF NOT EXISTS users (
            id SERIAL PRIMARY KEY,
            username TEXT UNIQUE NOT NULL,
            password_hash TEXT NOT NULL,
            created_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
        );
        """
    )

    # Accounts table
    await conn.execute(
        """
        CREATE TABLE IF NOT EXISTS accounts (
            id SERIAL PRIMARY KEY,
            user_id INTEGER NOT NULL REFERENCES users(id) ON DELETE CASCADE,
            name TEXT NOT NULL,
            balance NUMERIC(18,2) NOT NULL DEFAULT 0.00,
            currency TEXT NOT NULL DEFAULT 'USD',
            created_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
        );
        """
    )

    # Transactions table
    await conn.execute(
        """
        CREATE TABLE IF NOT EXISTS transactions (
            id SERIAL PRIMARY KEY,
            account_id INTEGER NOT NULL REFERENCES accounts(id) ON DELETE CASCADE,
            type TEXT NOT NULL CHECK (type IN ('deposit','withdraw','transfer_in','transfer_out')),
            amount NUMERIC(18,2) NOT NULL CHECK (amount >= 0),
            description TEXT,
            related_account_id INTEGER,
            created_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
        );
        """
    )

    # Seed demo user if not exists
    await conn.execute(
        """
        INSERT INTO users (username, password_hash)
        VALUES ('demo', '$2b$12$0nBzI0dM0v9JX2j4aKkOsef2qg4m2Qm5n3ox7kYtqE5mQ9n8z6n6S') -- hash for 'password'
        ON CONFLICT (username) DO NOTHING;
        """
    )

    # Seed a demo account for the demo user
    await conn.execute(
        """
        INSERT INTO accounts (user_id, name, balance, currency)
        SELECT id, 'Checking', 1000.00, 'USD' FROM users WHERE username='demo'
        ON CONFLICT DO NOTHING;
        """
    )
