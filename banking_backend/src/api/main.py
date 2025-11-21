from typing import List

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse

from .db import get_settings
from .routers_auth import router as auth_router
from .routers_accounts import router as accounts_router
from .routers_transactions import router as transactions_router

app = FastAPI(
    title="Banking Backend API",
    description="Handles business logic, transaction processing, user authentication, and database access for the banking app.",
    version="1.0.0",
    openapi_tags=[
        {"name": "auth", "description": "Authentication endpoints"},
        {"name": "accounts", "description": "Accounts management"},
        {"name": "transactions", "description": "Funds movements and transfers"},
    ],
)

# Configure CORS (safe even if .env not present)
settings = get_settings()
allow_origins: List[str] = [o.strip() for o in settings.cors_allow_origins.split(",") if o.strip()]
app.add_middleware(
    CORSMiddleware,
    allow_origins=allow_origins,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


@app.get("/", summary="Health Check", tags=["auth"])
def health_check():
    """Basic health check endpoint to verify service is running."""
    return {"message": "Healthy"}


# Register routers
app.include_router(auth_router)
app.include_router(accounts_router)
app.include_router(transactions_router)


@app.get("/docs/websocket", summary="WebSocket usage", tags=["auth"])
def websocket_usage():
    """Provide WebSocket usage notes (no websocket endpoints currently)."""
    return JSONResponse(
        {
            "note": "No WebSocket endpoints are currently available. This endpoint is a placeholder for documentation completeness."
        }
    )
