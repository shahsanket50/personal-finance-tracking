from fastapi import FastAPI
from dotenv import load_dotenv
from pathlib import Path
from starlette.middleware.cors import CORSMiddleware
import logging
import os
from datetime import datetime

ROOT_DIR = Path(__file__).parent
load_dotenv(ROOT_DIR / '.env')

logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)

# Import database to establish connection
from database import client

# Import all route modules
from routes.auth_routes import router as auth_router
from routes.accounts import router as accounts_router
from routes.categories import router as categories_router
from routes.transactions import router as transactions_router
from routes.analytics import router as analytics_router
from routes.upload import router as upload_router
from routes.accounting import router as accounting_router
from routes.ai import router as ai_router
from routes.backup import router as backup_router
from routes.email_sync import router as email_sync_router

app = FastAPI()

# Include all routers
app.include_router(auth_router)
app.include_router(accounts_router)
app.include_router(categories_router)
app.include_router(transactions_router)
app.include_router(analytics_router)
app.include_router(upload_router)
app.include_router(accounting_router)
app.include_router(ai_router)
app.include_router(backup_router)
app.include_router(email_sync_router)

app.add_middleware(
    CORSMiddleware,
    allow_credentials=True,
    allow_origins=os.environ.get("ALLOWED_ORIGINS", "*").split(","),
    allow_methods=["*"],
    allow_headers=["*"],
)


@app.get("/health")
async def health_check():
    return {"status": "ok", "timestamp": datetime.utcnow().isoformat()}

@app.on_event("shutdown")
async def shutdown_db_client():
    client.close()
