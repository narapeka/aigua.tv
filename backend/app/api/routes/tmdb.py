"""
TMDB API Routes
Endpoints for TMDB search operations
"""

import sys
from pathlib import Path
from fastapi import APIRouter, HTTPException

# Add parent directory to path
sys.path.insert(0, str(Path(__file__).parent.parent.parent.parent.parent))

from app.models.api_models import TMDBSearchRequest, TMDBSearchResponse, TMDBSearchResult
from config import load_config
from tmdb import TMDBClient

router = APIRouter()


@router.post("/tmdb/search", response_model=TMDBSearchResponse)
async def search_tmdb(request: TMDBSearchRequest):
    """
    Search TMDB for TV shows

    Searches The Movie Database for TV shows matching the query.
    Optionally filter by year.
    """
    try:
        # Load config and create TMDB client
        config = load_config()
        tmdb_client = TMDBClient(config.tmdb)

        # Search TMDB
        results = tmdb_client.search_tv_show(request.query, year=request.year)

        # Convert to API response format
        search_results = []
        for result in results[:10]:  # Limit to top 10 results
            search_results.append(TMDBSearchResult(
                id=result.id,
                name=result.name,
                original_name=result.original_name,
                first_air_date=getattr(result, 'first_air_date', None),
                overview=getattr(result, 'overview', None),
                poster_path=getattr(result, 'poster_path', None),
                vote_average=getattr(result, 'vote_average', None),
                origin_country=getattr(result, 'origin_country', None)
            ))

        return TMDBSearchResponse(results=search_results)

    except Exception as e:
        raise HTTPException(
            status_code=500,
            detail=f"TMDB search failed: {str(e)}"
        )


@router.get("/tmdb/show/{tmdb_id}")
async def get_tmdb_show(tmdb_id: int):
    """
    Get detailed TMDB information for a show

    Returns complete metadata for a specific TMDB show.
    """
    try:
        # Load config and create TMDB client
        config = load_config()
        tmdb_client = TMDBClient(config.tmdb)

        # Get show details
        metadata = tmdb_client.get_tv_show_details(tmdb_id)

        if not metadata:
            raise HTTPException(
                status_code=404,
                detail=f"Show with TMDB ID {tmdb_id} not found"
            )

        # Convert to dict
        return {
            "id": metadata.id,
            "name": metadata.name,
            "original_name": metadata.original_name,
            "year": metadata.year,
            "genre_ids": metadata.genre_ids,
            "origin_country": metadata.origin_country,
            "poster_path": getattr(metadata, 'poster_path', None),
            "overview": getattr(metadata, 'overview', None),
            "number_of_seasons": len(metadata.seasons) if metadata.seasons else 0
        }

    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(
            status_code=500,
            detail=f"Failed to get TMDB show: {str(e)}"
        )
