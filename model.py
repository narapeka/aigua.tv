#!/usr/bin/env python3
"""
Data models for TV Show Organizer
Defines the data structures used to represent TV shows, seasons, and episodes.
"""

from pathlib import Path
from typing import List, Optional
from dataclasses import dataclass
from enum import Enum


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
class TVShow:
    """Represents a complete TV show with all seasons"""
    name: str
    seasons: List[Season]
    original_folder: Path
    folder_type: FolderType

