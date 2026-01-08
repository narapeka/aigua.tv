"""
API Data Models
Pydantic schemas for request/response data
"""

from pydantic import BaseModel, Field
from typing import Optional, List, Dict, Any
from datetime import datetime
from enum import Enum


class JobStatus(str, Enum):
    """Job status enumeration"""
    PENDING = "pending"
    RUNNING = "running"
    COMPLETED = "completed"
    FAILED = "failed"
    CANCELLED = "cancelled"


class DryRunRequest(BaseModel):
    """Request to start a dry-run"""
    input_dir: str = Field(..., description="Input directory containing TV show folders")
    output_dir: str = Field(..., description="Output directory for organized files")
    config_overrides: Optional[Dict[str, Any]] = Field(None, description="Optional config overrides")


class DryRunResponse(BaseModel):
    """Response from dry-run start"""
    job_id: str = Field(..., description="Unique job identifier")
    status: JobStatus = Field(..., description="Current job status")


class TMDBMetadataResponse(BaseModel):
    """TMDB metadata for a show"""
    id: int
    name: str
    original_name: Optional[str] = None
    year: Optional[int] = None
    match_confidence: Optional[str] = None
    genre_ids: Optional[List[int]] = None
    origin_country: Optional[List[str]] = None
    poster_path: Optional[str] = None
    overview: Optional[str] = None


class EpisodeData(BaseModel):
    """Episode information"""
    episode_number: int
    original_file: str
    original_path: str
    new_file: str
    new_path: str
    status: str
    selected: bool = True
    tmdb_title: Optional[str] = None
    error: Optional[str] = None


class SeasonData(BaseModel):
    """Season information with episodes"""
    season_number: int
    episodes: List[EpisodeData]
    selected: bool = True
    original_folder: Optional[str] = None


class ShowData(BaseModel):
    """Complete show information"""
    id: str = Field(..., description="Unique show identifier for this job")
    name: str
    category: Optional[str] = None
    folder_type: str
    original_folder: str
    tmdb_metadata: Optional[TMDBMetadataResponse] = None
    confidence: str
    seasons: List[SeasonData]
    selected: bool = True
    cn_name: Optional[str] = None
    en_name: Optional[str] = None
    year: Optional[int] = None
    tmdb_id: Optional[int] = None


class UnprocessedShow(BaseModel):
    """Information about unprocessed shows"""
    folder_name: str
    reason: str


class JobResult(BaseModel):
    """Complete job result with all shows"""
    job_id: str
    status: JobStatus
    input_dir: str
    output_dir: str
    stats: Dict[str, int]
    processed_shows: List[ShowData]
    unprocessed_shows: List[Dict[str, str]]
    created_at: datetime
    updated_at: datetime
    error: Optional[str] = None


class TMDBSearchRequest(BaseModel):
    """Request to search TMDB"""
    query: str = Field(..., min_length=1, description="Search query")
    year: Optional[int] = Field(None, description="Optional year filter")


class TMDBSearchResult(BaseModel):
    """Single TMDB search result"""
    id: int
    name: str
    original_name: str
    first_air_date: Optional[str] = None
    overview: Optional[str] = None
    poster_path: Optional[str] = None
    vote_average: Optional[float] = None
    origin_country: Optional[List[str]] = None


class TMDBSearchResponse(BaseModel):
    """Response from TMDB search"""
    results: List[TMDBSearchResult]


class ReassignTMDBRequest(BaseModel):
    """Request to reassign TMDB match"""
    tmdb_id: int = Field(..., description="New TMDB ID to assign")


class CategoryUpdateRequest(BaseModel):
    """Request to update show category"""
    category: str = Field(..., description="New category")


class SelectionUpdateRequest(BaseModel):
    """Request to update selection state"""
    selected: bool = Field(..., description="Selection state")


class ConfigResponse(BaseModel):
    """Current configuration"""
    llm: Dict[str, Any]
    tmdb: Dict[str, Any]
    proxy: Optional[Dict[str, Any]] = None
    category: Optional[Dict[str, Any]] = None


class ConfigUpdateRequest(BaseModel):
    """Request to update configuration"""
    llm: Optional[Dict[str, Any]] = None
    tmdb: Optional[Dict[str, Any]] = None
    proxy: Optional[Dict[str, Any]] = None
    category: Optional[Dict[str, Any]] = None


class ExecuteRequest(BaseModel):
    """Request to execute organization"""
    # No body needed - uses cached job data with selection flags


class ProgressMessage(BaseModel):
    """WebSocket progress message"""
    type: str = Field(..., description="Message type: progress, log, status, completed, error")
    data: Dict[str, Any] = Field(..., description="Message data")


class ErrorResponse(BaseModel):
    """Error response"""
    detail: str = Field(..., description="Error message")
    error_type: Optional[str] = None
