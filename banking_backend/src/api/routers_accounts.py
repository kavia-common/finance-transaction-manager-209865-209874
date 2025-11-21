from typing import List

from fastapi import APIRouter, Depends
import asyncpg

from .schemas import Account, CreateAccountRequest
from .routers_auth import get_current_user
from .db import get_connection

router = APIRouter(prefix="/accounts", tags=["accounts"])


# PUBLIC_INTERFACE
@router.get("", response_model=List[Account], summary="List user accounts", description="List all accounts for the authenticated user.")
async def list_accounts(conn: asyncpg.Connection = Depends(get_connection), user=Depends(get_current_user)) -> List[Account]:
    """List accounts for the current user."""
    rows = await conn.fetch(
        "SELECT id, user_id, name, balance, currency, created_at FROM accounts WHERE user_id=$1 ORDER BY id",
        user.id,
    )
    return [
        Account(
            id=r["id"],
            user_id=r["user_id"],
            name=r["name"],
            balance=float(r["balance"]),
            currency=r["currency"],
            created_at=r["created_at"],
        )
        for r in rows
    ]


# PUBLIC_INTERFACE
@router.post("", response_model=Account, summary="Create an account", description="Create a new account for the authenticated user.")
async def create_account(payload: CreateAccountRequest, conn: asyncpg.Connection = Depends(get_connection), user=Depends(get_current_user)) -> Account:
    """Create a new account for the user."""
    row = await conn.fetchrow(
        "INSERT INTO accounts (user_id, name, balance, currency) VALUES ($1, $2, 0.00, $3) RETURNING id, user_id, name, balance, currency, created_at",
        user.id,
        payload.name,
        payload.currency,
    )
    return Account(
        id=row["id"],
        user_id=row["user_id"],
        name=row["name"],
        balance=float(row["balance"]),
        currency=row["currency"],
        created_at=row["created_at"],
    )
