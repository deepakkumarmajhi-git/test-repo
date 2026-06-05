import logging
from fastapi import FastAPI
from database import Base, engine, get_db, SessionLocal
from model.user import User
from model.repo import Repo
from model.commits import Commit
from router.webhook import router as webhook_router

# Configure centralized logging format and level
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s"
)

logger = logging.getLogger("app.main")
logger.info("Initializing Standalone GitHub Webhook FastAPI Application...")

app = FastAPI(title="Standalone GitHub Webhook Integration Module")

logger.info("Registering router endpoints...")
app.include_router(webhook_router)

logger.info("Synchronizing database tables...")
try:
    Base.metadata.create_all(bind=engine)
    logger.info("Database tables synchronized successfully.")
except Exception as e:
    logger.exception("Failed to synchronize database tables.")
    

@app.get("/")
def home():
    logger.info("Accessing home endpoint.")
    return {
        "status": "online",
        "message": "Standalone GitHub Webhook receiver is running!",
        "integration_endpoint": "/webhooks/github"
    }


if __name__ == "__main__":
    import uvicorn
    # Start the local development server on port 8001
    logger.info("🚀 Starting Standalone Webhook server on http://127.0.0.1:8001...")
    uvicorn.run("main:app", host="127.0.0.1", port=8001, reload=True)
