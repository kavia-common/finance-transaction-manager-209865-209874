from fastapi import APIRouter, Depends, HTTPException
import asyncpg

from .schemas import DepositRequest, WithdrawRequest, TransferRequest, Transaction
from .routers_auth import get_current_user
from .db import get_connection

router = APIRouter(prefix="/transactions", tags=["transactions"])


async def _get_account_for_user(conn: asyncpg.Connection, account_id: int, user_id: int):
    return await conn.fetchrow("SELECT id, user_id, name, balance, currency, created_at FROM accounts WHERE id=$1 AND user_id=$2", account_id, user_id)


# PUBLIC_INTERFACE
@router.post("/deposit", response_model=Transaction, summary="Deposit funds", description="Deposit funds into an account. Returns a transaction record.")
async def deposit(payload: DepositRequest, conn: asyncpg.Connection = Depends(get_connection), user=Depends(get_current_user)) -> Transaction:
    """Deposit funds into the specified account within a transaction."""
    async with conn.transaction():
        acc = await _get_account_for_user(conn, payload.account_id, user.id)
        if not acc:
            raise HTTPException(status_code=404, detail="Account not found")
        new_balance = float(acc["balance"]) + float(payload.amount)
        await conn.execute("UPDATE accounts SET balance=$1 WHERE id=$2", new_balance, payload.account_id)
        tx = await conn.fetchrow(
            "INSERT INTO transactions (account_id, type, amount, description) VALUES ($1, 'deposit', $2, $3) RETURNING id, account_id, type, amount, description, related_account_id, created_at",
            payload.account_id,
            payload.amount,
            payload.description,
        )
    return Transaction(
        id=tx["id"],
        account_id=tx["account_id"],
        type=tx["type"],
        amount=float(tx["amount"]),
        description=tx["description"],
        related_account_id=tx["related_account_id"],
        created_at=tx["created_at"],
    )


# PUBLIC_INTERFACE
@router.post("/withdraw", response_model=Transaction, summary="Withdraw funds", description="Withdraw funds from an account. Returns a transaction record.")
async def withdraw(payload: WithdrawRequest, conn: asyncpg.Connection = Depends(get_connection), user=Depends(get_current_user)) -> Transaction:
    """Withdraw funds from the specified account within a transaction."""
    async with conn.transaction():
        acc = await _get_account_for_user(conn, payload.account_id, user.id)
        if not acc:
            raise HTTPException(status_code=404, detail="Account not found")
        current_balance = float(acc["balance"])
        if payload.amount > current_balance:
            raise HTTPException(status_code=400, detail="Insufficient funds")
        new_balance = current_balance - float(payload.amount)
        await conn.execute("UPDATE accounts SET balance=$1 WHERE id=$2", new_balance, payload.account_id)
        tx = await conn.fetchrow(
            "INSERT INTO transactions (account_id, type, amount, description) VALUES ($1, 'withdraw', $2, $3) RETURNING id, account_id, type, amount, description, related_account_id, created_at",
            payload.account_id,
            payload.amount,
            payload.description,
        )
    return Transaction(
        id=tx["id"],
        account_id=tx["account_id"],
        type=tx["type"],
        amount=float(tx["amount"]),
        description=tx["description"],
        related_account_id=tx["related_account_id"],
        created_at=tx["created_at"],
    )


# PUBLIC_INTERFACE
@router.post("/transfer", response_model=Transaction, summary="Transfer funds", description="Transfer funds between two accounts owned by the authenticated user.")
async def transfer(payload: TransferRequest, conn: asyncpg.Connection = Depends(get_connection), user=Depends(get_current_user)) -> Transaction:
    """Transfer funds between two accounts, ensuring atomic updates across both accounts and creating paired transactions."""
    if payload.from_account_id == payload.to_account_id:
        raise HTTPException(status_code=400, detail="Cannot transfer to the same account")

    async with conn.transaction():
        src = await _get_account_for_user(conn, payload.from_account_id, user.id)
        dst = await _get_account_for_user(conn, payload.to_account_id, user.id)
        if not src or not dst:
            raise HTTPException(status_code=404, detail="One or both accounts not found")
        src_balance = float(src["balance"])
        if payload.amount > src_balance:
            raise HTTPException(status_code=400, detail="Insufficient funds")
        # Update balances
        await conn.execute("UPDATE accounts SET balance=$1 WHERE id=$2", src_balance - float(payload.amount), payload.from_account_id)
        await conn.execute("UPDATE accounts SET balance=$1 WHERE id=$2", float(dst["balance"]) + float(payload.amount), payload.to_account_id)
        # Create transactions (out and in)
        out_tx = await conn.fetchrow(
            "INSERT INTO transactions (account_id, type, amount, description, related_account_id) VALUES ($1, 'transfer_out', $2, $3, $4) RETURNING id, account_id, type, amount, description, related_account_id, created_at",
            payload.from_account_id, payload.amount, payload.description, payload.to_account_id
        )
        await conn.fetchrow(
            "INSERT INTO transactions (account_id, type, amount, description, related_account_id) VALUES ($1, 'transfer_in', $2, $3, $4) RETURNING id",
            payload.to_account_id, payload.amount, payload.description, payload.from_account_id
        )

    return Transaction(
        id=out_tx["id"],
        account_id=out_tx["account_id"],
        type=out_tx["type"],
        amount=float(out_tx["amount"]),
        description=out_tx["description"],
        related_account_id=out_tx["related_account_id"],
        created_at=out_tx["created_at"],
    )
