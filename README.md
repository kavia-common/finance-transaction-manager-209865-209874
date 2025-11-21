# Banking Backend (FastAPI)

Handles business logic, transaction processing, user authentication, and database access for the banking app.

## Prerequisites

- Python 3.10+
- A running PostgreSQL instance. The companion database container defaults:
  - DB: myapp
  - User: appuser
  - Password: dbuser123
  - Port: 5000
  - URL: postgresql://appuser:dbuser123@localhost:5000/myapp

Start the DB using the database container scripts:
- cd ../finance-transaction-manager-209865-209875/banking_database
- bash startup.sh

This will also write db_visualizer/postgres.env with the same values.

## Configure environment

Create a `.env` in this directory (a default has been committed for local dev):

Required variables:
- DATABASE_URL
- SECRET_KEY
- ACCESS_TOKEN_EXPIRE_MINUTES
- CORS_ALLOW_ORIGINS

Example:
```
DATABASE_URL=postgresql://appuser:dbuser123@localhost:5000/myapp
SECRET_KEY=dev-secret-change-me
ACCESS_TOKEN_EXPIRE_MINUTES=60
CORS_ALLOW_ORIGINS=http://localhost:3000
```

## Install and run

```
cd banking_backend
python -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
export PYTHONPATH=.
uvicorn src.api.main:app --host 0.0.0.0 --port 8000 --reload
```

Health check:
- GET http://localhost:8000/

Auth flow (seeded user):
- username: demo
- password: password

Endpoints:
- POST /auth/login (OAuth2 form: username, password)
- GET /auth/me
- GET /accounts
- POST /accounts
- POST /transactions/deposit
- POST /transactions/withdraw
- POST /transactions/transfer

## Database connectivity validation

On startup and first request, the backend:
- Creates tables if not present
- Seeds a demo user (demo/password)
- Seeds a Checking account with 1000.00 USD

Manual check:
- POST /auth/login with form fields username=demo, password=password
- Use bearer token to GET /accounts
- POST /transactions/deposit with { "account_id": <id>, "amount": 10.5 } then verify updated balance via GET /accounts

## Regenerate OpenAPI

If routes or models change:
```
cd banking_backend
python -m src.api.generate_openapi
```
OpenAPI will be written to `interfaces/openapi.json`.
