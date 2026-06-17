import os
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles
from contextlib import asynccontextmanager
from slowapi import _rate_limit_exceeded_handler
from slowapi.errors import RateLimitExceeded
from config import get_settings
from limiter import limiter
from models.database import init_db
from routes import predict, perfumes, notes

settings = get_settings()


@asynccontextmanager
async def lifespan(app: FastAPI):
    await init_db()
    yield


app = FastAPI(
    title="ScentScience API",
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
