import asyncio
import logging
import os
from contextlib import asynccontextmanager
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles
from slowapi import _rate_limit_exceeded_handler
from slowapi.errors import RateLimitExceeded
from config import get_settings
from limiter import limiter
from models.database import init_db, AsyncSessionLocal
from routes import predict, perfumes, notes, chat

settings = get_settings()
logger = logging.getLogger(__name__)


@asynccontextmanager
async def lifespan(app: FastAPI):
    await init_db()
    try:
        from sqlalchemy import text
        from models.database import engine as _engine
        async with _engine.begin() as conn:
            await conn.execute(text("CREATE EXTENSION IF NOT EXISTS pg_trgm"))
            await conn.execute(text(
                "CREATE INDEX IF NOT EXISTS idx_perfumes_brand_name_trgm "
                "ON perfumes USING gin ((brand || ' ' || name) gin_trgm_ops)"
            ))
    except Exception as exc:
        logger.warning("pg_trgm setup failed (search will fall back to ILIKE): %s", exc)
    try:
        from sqlalchemy import select
        from models.perfume import Perfume
        from ml.brand_dna import initialize_brand_dna
        async with AsyncSessionLocal() as session:
            stmt = select(Perfume).where(
                (Perfume.top_notes.isnot(None)) |
                (Perfume.middle_notes.isnot(None)) |
                (Perfume.base_notes.isnot(None))
            )
            db_result = await session.execute(stmt)
            db_perfumes = db_result.scalars().all()
        perfume_dicts = [
            {
                "brand": p.brand,
                "top_notes": p.top_notes or [],
                "middle_notes": p.middle_notes or [],
                "base_notes": p.base_notes or [],
            }
            for p in db_perfumes
        ]
        await asyncio.to_thread(initialize_brand_dna, perfume_dicts)
    except Exception as exc:
        logger.warning("brand_dna startup init failed: %s", exc)
    yield


app = FastAPI(
    title="DecodeScents API",
    description="ML platform for perfume performance prediction",
    version="1.0.0",
    lifespan=lifespan,
)

app.state.limiter = limiter
app.add_exception_handler(RateLimitExceeded, _rate_limit_exceeded_handler)

app.add_middleware(
    CORSMiddleware,
    allow_origins=[settings.frontend_url, "http://localhost:5173", "http://localhost:3000"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(predict.router, prefix="/api")
app.include_router(perfumes.router, prefix="/api")
app.include_router(notes.router, prefix="/api")
app.include_router(chat.router, prefix="/api")


@app.get("/health")
async def health():
    return {"status": "ok", "version": settings.model_version}


@app.get("/api/health")
async def api_health():
    from routes.predict import _models_cache
    return {"status": "ok", "models_loaded": _models_cache is not None}


# Serve React frontend — must be mounted after all API/health routes
_frontend_dist = os.path.join(os.path.dirname(os.path.abspath(__file__)), "frontend", "dist")
if os.path.exists(_frontend_dist):
    app.mount("/", StaticFiles(directory=_frontend_dist, html=True), name="frontend")
