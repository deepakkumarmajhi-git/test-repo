import hashlib
import hmac
import json
import logging
import os
from datetime import datetime
from typing import Any, Dict, List, Optional
from dotenv import load_dotenv
from fastapi import APIRouter, Header, HTTPException, Request, status, Depends
from sqlalchemy.orm import Session
from database import get_db
from model.user import User
from model.repo import Repo
from model.commits import Commit

logger = logging.getLogger("app.webhook")
logger.info("GitHub webhook router module loaded.")

# Router definition to easily mount onto any FastAPI app instance
router = APIRouter(prefix="/webhooks", tags=["webhooks"])


# def get_webhook_secret() -> Optional[str]:
#     """
#     Retrieves the webhook secret from the environment.
    
#     Replace or configure this function to match your project's settings system.
#     """
#     secret = os.getenv("GITHUB_WEBHOOK_SECRET")
#     if not secret:
#         logger.debug("GITHUB_WEBHOOK_SECRET environment variable is empty or not set.")
#     return secret
    

# async def verify_signature(request: Request, x_hub_signature_256: Optional[str]) -> None:
#     """
#     Validates that the incoming request is authentic and originated from GitHub.

#     Computes the HMAC hex digest using the configured secret and compares it
#     with the signature provided in the headers using a constant-time comparison.

#     Args:
#         request: The raw FastAPI request object containing the body payload.
#         x_hub_signature_256: The signature header string sent by GitHub.

#     Raises:
#         HTTPException: 401 Unauthorized if the signature header is missing.
#         HTTPException: 403 Forbidden if the signature validation fails.
#     """
#     logger.info("Verifying GitHub webhook signature...")
#     secret = get_webhook_secret()
    
#     if not secret:
#         logger.warning(
#             "SECURITY WARNING: GITHUB_WEBHOOK_SECRET environment variable is not set. "
#             "Skipping signature validation. DO NOT USE IN PRODUCTION."
#         )
#         return

#     if not x_hub_signature_256:
#         logger.error("Signature Validation Failed: Missing X-Hub-Signature-256 header.")
#         raise HTTPException(
#             status_code=status.HTTP_401_UNAUTHORIZED,
#             detail="Missing GitHub signature header (X-Hub-Signature-256)",
#         )

#     # Read the raw request body bytes for checksum calculation
#     try:
#         body_bytes = await request.body()
#     except Exception as e:
#         logger.exception("Failed to read raw request body for signature verification.")
#         raise HTTPException(
#             status_code=status.HTTP_400_BAD_REQUEST,
#             detail="Could not read request body"
#         )

    # Generate standard expected HMAC SHA-256 signature
    # hmac_obj = hmac.new(
    #     key=secret.encode("utf-8"),
    #     msg=body_bytes,
    #     digestmod=hashlib.sha256
    # )
    # expected_signature = f"sha256={hmac_obj.hexdigest()}"

    # Perform timing-attack resistant comparison
    # if not hmac.compare_digest(expected_signature, x_hub_signature_256):
    #     logger.error("Signature Validation Failed: HMAC SHA-256 signature mismatch.")
    #     raise HTTPException(
    #         status_code=status.HTTP_403_FORBIDDEN,
    #         detail="Invalid webhook signature validation failed",
    #     )
    # logger.info("GitHub webhook signature successfully verified.")

def process_webhook_payload(payload: Dict[str, Any]) -> None:
    """
    PLACEHOLDER: Custom business logic hook.
    
    Integrators should replace the contents of this function with their own 
    database persistence layer, queuing mechanism, or event dispatchers.
    
    Args:
        payload: The parsed GitHub webhook JSON payload dictionary.
    """
    logger.info("Custom Logic Hook: Received validated payload ready for processing.")
    try:
        repo_name = payload.get("repository", {}).get("full_name", "unknown")
        logger.info(f"Custom Logic Hook: Processing commits for repository '{repo_name}'")
    except Exception as e:
        logger.exception("Failed to process custom business logic on payload.")
        raise e


@router.post("/github")
async def github_webhook_receiver(
    request: Request,
    x_github_event: Optional[str] = Header(None),
    x_hub_signature_256: Optional[str] = Header(None),
    db: Session = Depends(get_db)
) -> Dict[str, Any]:
    """
    Ingestion gateway endpoint for GitHub Webhook events.

    Listens for:
      - 'ping': A handshake check triggered during webhook registration on GitHub.
      - 'push': Real-time commit push notifications. Extracts commit messages, 
                timestamps, authors, and writes them to a local JSON file.

    Args:
        request: FastAPI HTTP request wrapper.
        x_github_event: Custom header identifying the GitHub event type.
        x_hub_signature_256: HMAC security hash signature.
        db: SQLAlchemy database session.

    Returns:
        A structured JSON response detailing the outcome of the webhook execution.
    """
    logger.info(f"Received webhook request. Event: '{x_github_event}'")

    # 1. Enforce payload security signatures
    # logger.info("Running signature validation...")
    # await verify_signature(request, x_hub_signature_256)

    # 2. Extract Event Header
    if not x_github_event:
        logger.error("Webhook processing aborted: Missing X-GitHub-Event header.")
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Missing X-GitHub-Event header",
        )

    # 3. Handle Ping Handshake
    if x_github_event == "ping":
        logger.info("GitHub Webhook handshake successful: Received ping event.")
        return {
            "status": "success",
            "message": "Connection established successfully. Webhook receiver is listening."
        }

    # 4. Handle Push Notification
    if x_github_event == "push":
        try:
            payload = await request.json()
        except Exception as e:
            logger.exception("Failed to parse incoming request body as JSON.")
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Request body must be a valid JSON payload",
            )

        repo_data = payload.get("repository", {})
        repo_name = repo_data.get("full_name", "")
        short_repo_name = repo_data.get("name", "unknown_repo")

        if not repo_name:
            logger.error("Webhook processing aborted: Invalid payload repository structure (missing name).")
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Invalid payload structure: missing repository identifiers"
            )

        # Extract branch name from payload 'ref' (e.g. 'refs/heads/main' -> 'main')
        ref = payload.get("ref", "")
        branch = ref.split("/")[-1] if ref else "unknown_branch"

        logger.info(f"Processing GitHub push event for repository: {repo_name}, branch: {branch}")

        # -------------------------------------------------------------
        # Log to Local Sandbox JSON file (reponame_branch_day_timestamp.json)
        # -------------------------------------------------------------
        incoming_commits = payload.get("commits", [])
        simplified_commits = []
        
        logger.info(f"Parsing {len(incoming_commits)} commits from payload...")
        for item in incoming_commits:
            message = item.get("message", "No message provided")
            timestamp = item.get("timestamp", "")
            author_data = item.get("author", {})
            author_name = author_data.get("name") or author_data.get("username") or "Unknown Author"
            
            # Extract lists of affected files
            added_files = item.get("added", [])
            modified_files = item.get("modified", [])
            removed_files = item.get("removed", [])
            
            simplified_commits.append({
                "commit_sha": item.get("id"),
                "commit_message": message,
                "timestamp": timestamp,
                "author": author_name,
                "changes_summary": {
                    "files_added": added_files,
                    "files_modified": modified_files,
                    "files_removed": removed_files
                }
            })

        # Calculate time metadata
        now = datetime.now()
        day_name = now.strftime("%A")
        timestamp_str = now.strftime("%Y-%m-%d_%H-%M-%S")
        
        # Prevent directory traversal anomalies in file system writing
        safe_repo_name = short_repo_name.replace("/", "_").replace("\\", "_")
        filename = f"{safe_repo_name}_{branch}_{day_name}_{timestamp_str}.json"
        
        # Build path to saved_payloads directory relative to this folder
        base_dir = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
        saved_dir = os.path.join(base_dir, "saved_payloads")
        
        try:
            os.makedirs(saved_dir, exist_ok=True)
            filepath = os.path.join(saved_dir, filename)
        except Exception as e:
            logger.exception(f"Failed to create directory {saved_dir} for payload saving.")
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail="Could not create folder for saved payloads"
            )
        
        output_payload = {
            "repository": repo_name,
            "branch": branch,
            "total_commits": len(simplified_commits),
            "commits": simplified_commits
        }
        
        try:
            with open(filepath, "w", encoding="utf-8") as f:
                json.dump(output_payload, f, indent=2, ensure_ascii=False)
            logger.info(f"Sandbox Logging: Wrote webhook payload log to {filepath}")
        except Exception as exc_file:
            logger.exception(f"Sandbox Logging Failure: Could not write file: {exc_file}")
        # -------------------------------------------------------------

        # -------------------------------------------------------------
        # Log to PostgreSQL Database
        # -------------------------------------------------------------
        logger.info("Database Logging: Attempting to insert push payload into PostgreSQL...")
        try:
            # 1. Resolve repository owner user
            owner_username = "unknown_owner"
            if "/" in repo_name:
                owner_username = repo_name.split("/")[0]
            else:
                owner_username = repo_data.get("owner", {}).get("login") or "unknown_owner"

            db_owner = db.query(User).filter(User.username == owner_username).first()
            if not db_owner:
                logger.info(f"Database Logging: Creating owner user: {owner_username}")
                db_owner = User(username=owner_username, email=None)
                db.add(db_owner)
                db.flush()

            # 2. Resolve repository
            db_repo = db.query(Repo).filter(Repo.name == repo_name).first()
            if not db_repo:
                logger.info(f"Database Logging: Creating repository: {repo_name}")
                db_repo = Repo(name=repo_name, user_id=db_owner.id)
                db.add(db_repo)
                db.flush()

            # 3. Resolve pusher/sender user
            sender_username = payload.get("sender", {}).get("login")
            if not sender_username:
                if incoming_commits:
                    author_data = incoming_commits[0].get("author", {})
                    sender_username = author_data.get("username") or author_data.get("name") or owner_username
                else:
                    sender_username = owner_username

            db_pusher = db.query(User).filter(User.username == sender_username).first()
            if not db_pusher:
                logger.info(f"Database Logging: Creating pusher user: {sender_username}")
                pusher_email = payload.get("sender", {}).get("email")
                if not pusher_email and incoming_commits:
                    pusher_email = incoming_commits[0].get("author", {}).get("email")
                db_pusher = User(username=sender_username, email=pusher_email)
                db.add(db_pusher)
                db.flush()

            # 4. Construct message mapping
            commit_messages_map = {}
            for item in incoming_commits:
                sha = item.get("id") or item.get("commit_sha") or "unknown_sha"
                msg = item.get("message") or item.get("commit_message") or "No message"
                commit_messages_map[sha] = msg

            # 5. Extract timestamp
            push_timestamp = datetime.now()
            if incoming_commits:
                ts_str = incoming_commits[0].get("timestamp")
                if ts_str:
                    try:
                        push_timestamp = datetime.fromisoformat(ts_str.replace("Z", "+00:00"))
                    except Exception:
                        logger.warning(f"Database Logging: Failed to parse timestamp: {ts_str}")

            # 6. Create Commit entry
            db_commit = Commit(
                repo_id=db_repo.id,
                user_id=db_pusher.id,
                branch=branch,
                message=commit_messages_map,
                total_commit=len(incoming_commits),
                timestamp=push_timestamp
            )
            db.add(db_commit)
            db.commit()
            logger.info("Database Logging: Successfully inserted push payload into PostgreSQL.")
        except Exception as db_err:
            db.rollback()
            logger.exception("Database Logging Failure: Rollback executed.")
        # -------------------------------------------------------------

        # 5. Dispatch payload to custom business logic hook
        logger.info("Executing custom business logic hook process_webhook_payload...")
        try:
            process_webhook_payload(payload)
        except Exception as e:
            logger.exception("Error occurred in custom webhook payload processor.")

        return {
            "status": "success",
            "message": f"Successfully parsed {len(simplified_commits)} commits.",
            "repository": repo_name,
            "branch": branch,
            "saved_file": filename,
            "payload": output_payload
        }

    # Graceful fallback for unsupported webhooks
    logger.info(f"Ignored webhook event: Event type '{x_github_event}' is currently unhandled.")
    return {
        "status": "ignored",
        "message": f"Webhook event '{x_github_event}' is currently unhandled."
    }
