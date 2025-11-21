from typing import Optional
from pydantic import BaseModel, Field
from datetime import datetime


class Token(BaseModel):
    access_token: str = Field(..., description="JWT access token")
    token_type: str = Field("bearer", description="Token type")


class User(BaseModel):
    id: int = Field(..., description="User ID")
    username: str = Field(..., description="Username")
    created_at: datetime = Field(..., description="User creation timestamp")


class LoginRequest(BaseModel):
    username: str = Field(..., description="Username")
    password: str = Field(..., description="Plain text password")


class Account(BaseModel):
    id: int = Field(..., description="Account ID")
    user_id: int = Field(..., description="Owner user ID")
    name: str = Field(..., description="Account name")
    balance: float = Field(..., description="Current balance")
    currency: str = Field(..., description="Currency code")
    created_at: datetime = Field(..., description="Created time")


class CreateAccountRequest(BaseModel):
    name: str = Field(..., description="Account name")
    currency: str = Field("USD", description="Currency code")


class Transaction(BaseModel):
    id: int = Field(..., description="Transaction ID")
    account_id: int = Field(..., description="Related account ID")
    type: str = Field(..., description="Transaction type")
    amount: float = Field(..., description="Transaction amount")
    description: Optional[str] = Field(None, description="Description")
    related_account_id: Optional[int] = Field(None, description="Related account in transfer")
    created_at: datetime = Field(..., description="Created time")


class DepositRequest(BaseModel):
    account_id: int = Field(..., description="Account to deposit to")
    amount: float = Field(..., description="Amount to deposit", gt=0)
    description: Optional[str] = Field(None, description="Optional description")


class WithdrawRequest(BaseModel):
    account_id: int = Field(..., description="Account to withdraw from")
    amount: float = Field(..., description="Amount to withdraw", gt=0)
    description: Optional[str] = Field(None, description="Optional description")


class TransferRequest(BaseModel):
    from_account_id: int = Field(..., description="Source account ID")
    to_account_id: int = Field(..., description="Destination account ID")
    amount: float = Field(..., description="Amount to transfer", gt=0)
    description: Optional[str] = Field(None, description="Optional description")
