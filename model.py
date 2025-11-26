#!/usr/bin/env python3
"""
Data models for TV Show Organizer
Defines the data structures used to represent TV shows, seasons, and episodes.
"""

from pathlib import Path
from typing import List, Optional, TYPE_CHECKING
from dataclasses import dataclass, field
from enum import Enum

if TYPE_CHECKING:
    from tmdb import TVShowMetadata


class FolderType(Enum):
    DIRECT_FILES = "direct_files"  # Case 1: Media files directly in show folder
    SEASON_SUBFOLDERS = "season_subfolders"  # Case 2: Season subfolders


@dataclass
class Episode:
    """Represents a single episode file"""
    original_path: Path
    show_name: str
    season_number: int
    episode_number: int
    title: str = ""
    extension: str = ""
    end_episode_number: Optional[int] = None  # For multi-episode files (e.g., S01E01-S01E02)
    tmdb_title: Optional[str] = None  # Episode title from TMDB (if available)
    
    def __post_init__(self):
        if not self.extension:
            self.extension = self.original_path.suffix
        if not self.title:
            if self.end_episode_number:
                self.title = f"Episode {self.episode_number:02d}-{self.end_episode_number:02d}"
            else:
                self.title = f"Episode {self.episode_number:02d}"


@dataclass
class Season:
    """Represents a season with its episodes"""
    show_name: str
    season_number: int
    episodes: List[Episode]
    original_folder: Path


@dataclass
class FolderStructure:
    """Represents the structure of a folder (cached to avoid re-scanning)"""
    folder_path: Path
    folder_type: FolderType
    video_files: List[Path] = field(default_factory=list)
    subdirs: List[Path] = field(default_factory=list)
    first_file: Optional[Path] = None  # First video file for quick access
    first_file_name: Optional[str] = None  # First file name for LLM context


@dataclass
class TVShow:
    """Represents a complete TV show with all seasons"""
    name: str
    seasons: List[Season]
    original_folder: Path
    folder_type: FolderType
    tmdb_metadata: Optional['TVShowMetadata'] = None  # Full TMDB metadata
    cn_name: Optional[str] = None  # Chinese name from LLM/TMDB
    en_name: Optional[str] = None  # English name from LLM/TMDB
    year: Optional[int] = None  # Release year
    tmdb_id: Optional[int] = None  # TMDB ID
    match_confidence: Optional[str] = None  # Confidence level (high/medium/low)
    category: Optional[str] = None  # Category classification (e.g., 国产剧, 日番, 纪录片)

