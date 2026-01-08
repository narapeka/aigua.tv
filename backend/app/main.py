"""
aigua.tv WebUI Backend
FastAPI application for TV show organizer web interface
"""

import os
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse

from app.services.cache_service import get_cache_service
from app.models.api_models import ErrorResponse

# Initialize FastAPI app
app = FastAPI(
    title="aigua.tv WebUI API",
    description="Web interface API for TV show organizer",
    version="1.0.0"
)

# Configure CORS
app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:5173", "http://localhost:3000"],  # Vite dev server
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Initialize cache service on startup
@app.on_event("startup")
async def startup_event():
    """Initialize services on startup"""
    redis_url = os.getenv("REDIS_URL")
    get_cache_service(redis_url)
    print("✓ aigua.tv WebUI backend started")


@app.get("/", tags=["Health"])
async def root():
    """Root endpoint - health check"""
    return {
        "status": "ok",
        "message": "aigua.tv WebUI API",
        "version": "1.0.0"
    }


@app.get("/api/health", tags=["Health"])
async def health_check():
    """Health check endpoint"""
    return {"status": "healthy"}


# Custom exception handler
@app.exception_handler(Exception)
async def global_exception_handler(request, exc):
    """Global exception handler"""
    return JSONResponse(
        status_code=500,
        content=ErrorResponse(
            detail=str(exc),
            error_type=type(exc).__name__
        ).dict()
    )


# Import and include routers
from app.api.routes import jobs, config, tmdb, websocket

app.include_router(jobs.router, prefix="/api", tags=["Jobs"])
app.include_router(config.router, prefix="/api", tags=["Configuration"])
app.include_router(tmdb.router, prefix="/api", tags=["TMDB"])
app.include_router(websocket.router, prefix="/api", tags=["WebSocket"])


if __name__ == "__main__":
    import uvicorn
    uvicorn.run(
        "app.main:app",
        host="0.0.0.0",
        port=8000,
        reload=True
    )
