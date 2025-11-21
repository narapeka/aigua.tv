"""FastAPI application entry point"""

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles
from pathlib import Path

from webui.api import config, folders, tmdb, organize, preview

app = FastAPI(
    title="TV Show Organizer Web UI",
    description="Web interface for TV Show Media Library Organizer",
    version="1.0.0"
)

# CORS middleware
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # In production, restrict this
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Include routers
app.include_router(config.router)
app.include_router(folders.router)
app.include_router(tmdb.router)
app.include_router(organize.router)
app.include_router(preview.router)


@app.get("/")
async def root():
    """Root endpoint"""
    return {"message": "TV Show Organizer Web UI API"}


@app.get("/health")
async def health():
    """Health check endpoint"""
    return {"status": "healthy"}


# Mount static files if they exist
static_dir = Path(__file__).parent / "static"
if static_dir.exists():
    app.mount("/", StaticFiles(directory=str(static_dir), html=True), name="static")


if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000)

