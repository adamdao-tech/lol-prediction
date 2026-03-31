import secrets
import subprocess
from contextlib import asynccontextmanager
from typing import Annotated

from fastapi import Depends, FastAPI, HTTPException, status
from fastapi.middleware.cors import CORSMiddleware
from fastapi.security import HTTPBasic, HTTPBasicCredentials

from app.api.router import router as api_router
from app.config import settings
from app.scheduler import start_scheduler, stop_scheduler
from app.utils.logging import configure_logging, get_logger

configure_logging()
logger = get_logger(__name__)

security = HTTPBasic(auto_error=False)

def _verify_credentials(credentials: Annotated[HTTPBasicCredentials | None, Depends(security)]) -> str:
    if credentials is None:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Not authenticated",
            headers={"WWW-Authenticate": "Basic"},
        )
    for user in settings.ALLOWED_USERS:
        correct_username = secrets.compare_digest(credentials.username, user["username"])
        correct_password = secrets.compare_digest(credentials.password, user["password"])
        if correct_username and correct_password:
            return credentials.username
    raise HTTPException(
        status_code=status.HTTP_401_UNAUTHORIZED,
        detail="Invalid credentials",
        headers={"WWW-Authenticate": "Basic"},
    )


@asynccontextmanager
async def lifespan(app: FastAPI):
    logger.info("Starting up — running Alembic migrations")
    try:
        subprocess.run(
            ["alembic", "upgrade", "head"],
            check=True,
            capture_output=True,
            text=True,
        )
        logger.info("Alembic migrations applied")
    except subprocess.CalledProcessError as exc:
        logger.error("Alembic migration failed", stdout=exc.stdout, stderr=exc.stderr)

    start_scheduler()
    yield
    stop_scheduler()
    logger.info("Shutting down")

app = FastAPI(
    title="LoL Predictor API",
    version="0.1.0",
    description="Internal LoL esports prediction application",
    lifespan=lifespan,
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:5173", "http://127.0.0.1:5173"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


@app.get("/health", tags=["health"])
async def health_check():
    from sqlalchemy.ext.asyncio import create_async_engine
    from sqlalchemy import text

    db_status = "ok"
    try:
        tmp_engine = create_async_engine(settings.DATABASE_URL)
        async with tmp_engine.connect() as conn:
            await conn.execute(text("SELECT 1"))
        await tmp_engine.dispose()
    except Exception as exc:
        db_status = f"error: {exc}"

    return {"status": "ok", "db": db_status, "version": "0.1.0"}


AuthDep = Annotated[str, Depends(_verify_credentials)]

app.include_router(api_router, prefix="/api", dependencies=[Depends(_verify_credentials)])