"""TMDB API endpoints"""

from fastapi import APIRouter, HTTPException
from typing import List, Dict, Any

from config import load_config
from tmdb import create_tmdb_client_from_config, TVShowMetadata
from webui.models.schemas import TMDBSearchRequest, TMDBSearchResponse, TMDBShowSearchResult, TMDBShowResponse
import logging

router = APIRouter(prefix="/api/tmdb", tags=["tmdb"])
logger = logging.getLogger(__name__)


@router.post("/search", response_model=TMDBSearchResponse)
async def search_tmdb(request: TMDBSearchRequest):
    """Search TMDB for TV shows"""
    try:
        config = load_config()
        tmdb_client = create_tmdb_client_from_config(config, logger)
        
        # Search TMDB
        results = tmdb_client.search_tv_show(request.query)
        
        # Convert to response format
        search_results = []
        for metadata in results:
            search_results.append(TMDBShowSearchResult(
                id=metadata.id,
                name=metadata.name,
                original_name=metadata.original_name,
                first_air_date=str(metadata.year) if metadata.year else None,
                overview=None,  # Could add if needed
                poster_path=None  # Could add if needed
            ))
        
        return TMDBSearchResponse(results=search_results)
    except Exception as e:
        logger.error(f"Error searching TMDB: {e}")
        raise HTTPException(status_code=500, detail=f"Failed to search TMDB: {str(e)}")


@router.get("/show/{tmdb_id}", response_model=TMDBShowResponse)
async def get_tmdb_show(tmdb_id: int):
    """Get full TMDB metadata for a show"""
    try:
        config = load_config()
        tmdb_client = create_tmdb_client_from_config(config, logger)
        
        # Get show details
        metadata = tmdb_client.get_tv_show_details(tmdb_id)
        
        if not metadata:
            raise HTTPException(status_code=404, detail="Show not found")
        
        # Convert to response format
        return TMDBShowResponse(
            id=metadata.id,
            name=metadata.name,
            original_name=metadata.original_name,
            overview=None,  # Could add if needed
            first_air_date=str(metadata.year) if metadata.year else None,
            poster_path=None,  # Could add if needed
            backdrop_path=None,  # Could add if needed
            seasons=metadata.to_dict().get('seasons')
        )
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error fetching TMDB show: {e}")
        raise HTTPException(status_code=500, detail=f"Failed to fetch show: {str(e)}")

