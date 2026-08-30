from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.core.config import settings

app = FastAPI(
    title="Recovr API",
    description="AI Revenue Recovery agent for Razorpay's AI Buildathon (Track 3)",
    version="0.1.0",
    docs_url="/docs",
    redoc_url="/redoc",
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:5173", "http://localhost:3000"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
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

from app.api.endpoints import router as api_router
app.include_router(api_router)
