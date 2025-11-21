"""Pydantic schemas for API request/response models"""

from typing import Optional, List, Dict, Any
from pydantic import BaseModel, Field


# Configuration schemas
class LLMConfigSchema(BaseModel):
    api_key: str = Field(default="", description="LLM API key")
    base_url: str = Field(default="", description="Base URL for API")
    model: str = Field(default="", description="Model name")
    batch_size: int = Field(default=50, description="Batch size")
    rate_limit: int = Field(default=2, description="Rate limit per second")


class TMDBConfigSchema(BaseModel):
    api_key: str = Field(default="", description="TMDB API key")
    languages: List[str] = Field(default_factory=lambda: ["zh-CN", "zh-SG", "zh-TW", "zh-HK"])
    rate_limit: int = Field(default=40, description="Rate limit per second")


class ProxyConfigSchema(BaseModel):
    host: str = Field(default="http://127.0.0.1", description="Proxy host")
    port: int = Field(default=8080, description="Proxy port")


class ConfigSchema(BaseModel):
    llm: LLMConfigSchema
    tmdb: TMDBConfigSchema
    proxy: Optional[ProxyConfigSchema] = None


# Folder schemas
class FolderItemSchema(BaseModel):
    name: str
    path: str
    is_directory: bool
    children: Optional[List['FolderItemSchema']] = None


class ScanFoldersRequest(BaseModel):
    source_folder: str = Field(..., description="Source folder path")


class ScanFoldersResponse(BaseModel):
    folders: List[str] = Field(..., description="List of folder names found")


# TMDB schemas
class TMDBShowSearchResult(BaseModel):
    id: int
    name: str
    original_name: Optional[str] = None
    first_air_date: Optional[str] = None
    overview: Optional[str] = None
    poster_path: Optional[str] = None


class TMDBSearchRequest(BaseModel):
    query: str = Field(..., description="Search query")
    language: Optional[str] = None


class TMDBSearchResponse(BaseModel):
    results: List[TMDBShowSearchResult]


class TMDBShowResponse(BaseModel):
    id: int
    name: str
    original_name: Optional[str] = None
    overview: Optional[str] = None
    first_air_date: Optional[str] = None
    poster_path: Optional[str] = None
    backdrop_path: Optional[str] = None
    seasons: Optional[List[Dict[str, Any]]] = None


# Organization schemas
class EpisodePreviewSchema(BaseModel):
    episode_number: int
    original_file: str
    original_path: str
    new_file: str
    new_path: str
    status: str


class SeasonPreviewSchema(BaseModel):
    season_number: int
    episodes: List[EpisodePreviewSchema]
    original_folder: Optional[str] = None  # Original season folder path (for season_subfolders type)


class ShowPreviewSchema(BaseModel):
    folder_name: str
    detected_name: Optional[str] = None
    cn_name: Optional[str] = None
    en_name: Optional[str] = None
    tmdb_match: Optional[Dict[str, Any]] = None
    match_confidence: Optional[str] = None
    selected: bool = True
    seasons: List[SeasonPreviewSchema]
    original_folder: str
    folder_type: str


class DryRunRequest(BaseModel):
    source_folder: str = Field(..., description="Source folder path")
    target_folder: str = Field(..., description="Target folder path")


class DryRunResponse(BaseModel):
    job_id: str
    status: str
    message: str


class PreviewResponse(BaseModel):
    job_id: str
    shows: List[ShowPreviewSchema]
    stats: Dict[str, Any]


class ExecuteRequest(BaseModel):
    job_id: str = Field(..., description="Job ID from dry-run")
    selected_folders: List[str] = Field(..., description="List of folder names to process")
    manual_matches: Optional[Dict[str, int]] = Field(default=None, description="Manual TMDB ID overrides")


class ExecuteResponse(BaseModel):
    job_id: str
    status: str
    message: str


class JobStatusResponse(BaseModel):
    job_id: str
    status: str  # pending, running, completed, failed, cancelled
    progress: Optional[Dict[str, Any]] = None
    message: Optional[str] = None
    error: Optional[str] = None


# Update match schema
class UpdateMatchRequest(BaseModel):
    folder_name: str = Field(..., description="Folder name")
    tmdb_id: int = Field(..., description="TMDB ID to use")


class UpdateMatchResponse(BaseModel):
    success: bool
    message: str
