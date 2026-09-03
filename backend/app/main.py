"""
Recovr FastAPI application entry point.

Cross-origin cookie configuration:
- allow_origins explicitly lists http://localhost:5173 (never "*" for credentialed requests)
- allow_credentials=True is required so the browser sends the refresh_token httpOnly cookie
"""
from fastapi import FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware
from slowapi import Limiter, _rate_limit_exceeded_handler
from slowapi.errors import RateLimitExceeded
from slowapi.util import get_remote_address

from app.core.config import settings

# ---------------------------------------------------------------------------
# Rate limiter (slowapi / limits)
# ---------------------------------------------------------------------------
limiter = Limiter(key_func=get_remote_address, default_limits=["200/minute"])

app = FastAPI(
    title="Recovr API",
    description="AI Revenue Recovery agent for Razorpay's AI Buildathon (Track 3)",
    version="0.1.0",
    docs_url="/docs",
    redoc_url="/redoc",
)

app.state.limiter = limiter
app.add_exception_handler(RateLimitExceeded, _rate_limit_exceeded_handler)

# ---------------------------------------------------------------------------
# CORS — explicit origins required for credentialed cross-origin requests.
# Using "*" with allow_credentials=True is rejected by browsers (CORS spec).
# ⚠️  Add your production domain here before deploying.
# ---------------------------------------------------------------------------
app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:5173", "http://localhost:3000"],
    allow_credentials=True,   # Required: lets browser send the refresh_token cookie
    allow_methods=["*"],
    allow_headers=["*"],
    expose_headers=["X-Request-ID"],
)


@app.get("/health", tags=["System"])
async def health_check():
    """Health check endpoint — verify API is alive."""
    return {
        "status": "ok",
        "service": "recovr-api",
        "environment": settings.ENVIRONMENT,
        "version": "0.1.0",
    }


@app.get("/", tags=["System"])
async def root():
    return {"message": "Recovr API — see /docs for endpoints"}


# ---------------------------------------------------------------------------
# Routers
# ---------------------------------------------------------------------------
from app.api.auth_routes import router as auth_router
from app.api.endpoints import router as api_router

app.include_router(auth_router)
app.include_router(api_router)
