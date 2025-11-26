#!/usr/bin/env python3
"""
TV Show Media Library Organizer
Reorganizes TV show media files following Emby naming conventions.

Supports two folder structure cases:
1. Direct files in show folder (represents single season)
2. Season subfolders containing episode files

Author: Kilo Code
"""

import re
import shutil
import argparse
import logging
from pathlib import Path
from typing import List, Dict, Tuple, Optional
from datetime import datetime
from concurrent.futures import ThreadPoolExecutor, TimeoutError as FutureTimeoutError, as_completed

from logger import Colors, setup_logging
from report import generate_html_report
from model import FolderType, Episode, Season, TVShow, FolderStructure
from pattern import generate_filename, extract_season_number, extract_episode_info
from llm import LLMAgent, TVShowInfo
from tmdb import TMDBClient, TVShowMetadata, create_tmdb_client_from_config
from cache import TVShowCache, FolderStructureCache
from config import load_config
from category import CategoryHelper

class TVShowOrganizer:
    """Main class for organizing TV show media library"""
    
    # Supported media file extensions (video + subtitles)
    # Subtitle files are included so they go through the same episode/season detection logic
    MEDIA_EXTENSIONS = {
        # Video formats
        '.mp4', '.mkv', '.avi', '.mov', '.wmv', '.flv', '.webm', '.m4v', '.ts', '.m2ts',
        # Subtitle formats
        '.srt', '.ass', '.ssa', '.vtt', '.sub', '.idx', '.sup', '.pgs'
    }
    
    
    def __init__(self, input_dir: str, output_dir: str, dry_run: bool = False, verbose: bool = False, log_dir: Optional[str] = None):
        self.input_dir = Path(input_dir).resolve()
        self.output_dir = Path(output_dir).resolve()
        self.dry_run = dry_run
        self.verbose = verbose
        
        # Setup log directory - default to project root logs folder
        if log_dir:
            self.log_dir = Path(log_dir).resolve()
        else:
            # Use logs folder in project root (where this script is located)
            project_root = Path(__file__).parent
            self.log_dir = project_root / "logs"
        self.log_dir.mkdir(parents=True, exist_ok=True)
        
        # Generate log file names with timestamp
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        self.log_file = self.log_dir / f"tv_organizer_{timestamp}.log"
        self.report_file = self.log_dir / f"tv_organizer_report_{timestamp}.html"
        
        # Execution tracking
        self.start_time = datetime.now()
        self.processed_shows = []  # Store details of processed shows
        self.unprocessed_shows = []  # Track unprocessed shows with reasons
        
        # Setup logging
        self.logger = setup_logging(self.log_file, self.verbose)
        
        # Load configuration and initialize LLM agent, TMDB client, and cache
        try:
            self.config = load_config()
            self.llm_agent = LLMAgent(
                api_key=self.config.llm.api_key,
                base_url=self.config.llm.base_url,
                model=self.config.llm.model,
                batch_size=self.config.llm.batch_size,
                rate_limit=self.config.llm.rate_limit,
                logger=self.logger
            )
            self.tmdb_client = create_tmdb_client_from_config(self.config, self.logger)
            self.cache = TVShowCache()
            self.folder_cache = FolderStructureCache()
            
            # Initialize CategoryHelper for genre-based organization
            self.category_helper = None
            if self.config.category and self.config.category.enabled:
                category_path = Path(self.config.category.path) if self.config.category.path else None
                self.category_helper = CategoryHelper(category_path=category_path, logger=self.logger)
                if self.category_helper.is_enabled:
                    self.logger.info(f"{Colors.GREEN}Category classification enabled with {len(self.category_helper.tv_category_names)} categories{Colors.RESET}")
                else:
                    self.logger.info(f"{Colors.YELLOW}Category classification disabled (no category.yaml found){Colors.RESET}")
                    self.category_helper = None
            else:
                self.logger.info(f"{Colors.YELLOW}Category classification disabled in config{Colors.RESET}")
            
            self.logger.info(f"{Colors.GREEN}LLM Agent and TMDB Client initialized{Colors.RESET}")
        except Exception as e:
            self.logger.error(f"{Colors.RED}Failed to initialize LLM/TMDB: {e}{Colors.RESET}")
            raise
        
        # Statistics
        self.stats = {
            'shows_processed': 0,
            'seasons_processed': 0,
            'episodes_moved': 0,
            'errors': 0
        }
        
        # File operation timeout (60 seconds for network storage)
        self.file_operation_timeout = 60
        
        self.logger.info(f"{Colors.CYAN}TV Show Media Library Organizer{Colors.RESET}")
        self.logger.info(f"Input Directory: {Colors.YELLOW}{self.input_dir}{Colors.RESET}")
        self.logger.info(f"Output Directory: {Colors.YELLOW}{self.output_dir}{Colors.RESET}")
        self.logger.info(f"Mode: {Colors.MAGENTA}{'DRY RUN' if dry_run else 'LIVE'}{Colors.RESET}")
        self.logger.info(f"Log File: {Colors.CYAN}{self.log_file}{Colors.RESET}")
    
    def _cleanup_old_files(self, keep_count: int = 10):
        """
        Clean up old log and HTML report files, keeping only the most recent ones.
        
        Args:
            keep_count: Number of most recent files to keep (default: 10)
        """
        try:
            # Find all log files matching the pattern
            log_files = sorted(
                self.log_dir.glob("tv_organizer_*.log"),
                key=lambda p: p.stat().st_mtime,
                reverse=True
            )
            
            # Find all HTML report files matching the pattern
            html_files = sorted(
                self.log_dir.glob("tv_organizer_report_*.html"),
                key=lambda p: p.stat().st_mtime,
                reverse=True
            )
            
            # Delete old log files (keep only the most recent keep_count)
            deleted_logs = 0
            for old_log in log_files[keep_count:]:
                try:
                    old_log.unlink()
                    deleted_logs += 1
                except Exception as e:
                    # Silently continue if file deletion fails (might be in use)
                    pass
            
            # Delete old HTML files (keep only the most recent keep_count)
            deleted_html = 0
            for old_html in html_files[keep_count:]:
                try:
                    old_html.unlink()
                    deleted_html += 1
                except Exception as e:
                    # Silently continue if file deletion fails (might be in use)
                    pass
            
            # Log cleanup results (if logger is available, otherwise skip)
            if hasattr(self, 'logger') and self.logger:
                if deleted_logs > 0 or deleted_html > 0:
                    self.logger.info(f"{Colors.CYAN}Cleaned up old files: {deleted_logs} log files, {deleted_html} HTML reports (kept {keep_count} most recent of each){Colors.RESET}")
        except Exception as e:
            # Silently fail cleanup - don't break the main process
            # This could happen if log_dir doesn't exist or permissions are wrong
            pass
    
    def is_video_file(self, file_path: Path) -> bool:
        """Check if file is a supported media file (video or subtitle)"""
        return file_path.suffix.lower() in self.MEDIA_EXTENSIONS
    
    def get_video_files(self, directory: Path, recursive: bool = False) -> List[Path]:
        """
        Get all media files (video + subtitles) in a directory
        
        Args:
            directory: Path to the directory to scan
            recursive: If True, recursively scan all subdirectories. If False, only scan immediate directory.
        
        Returns:
            List of video file paths, sorted by name
        """
        if not directory.exists() or not directory.is_dir():
            return []
        
        video_files = []
        
        # Get files in immediate directory
        for file_path in directory.iterdir():
            if file_path.is_file() and self.is_video_file(file_path):
                video_files.append(file_path)
        
        # Recursively get files from subdirectories if requested
        if recursive:
            for subdir in directory.iterdir():
                if subdir.is_dir():
                    video_files.extend(self.get_video_files(subdir, recursive=True))
        
        return sorted(video_files, key=lambda x: x.name.lower())
    
    def normalize_show_name(self, name: str) -> str:
        """Normalize TV show name for consistent formatting"""
        # Remove special characters and normalize spacing
        name = re.sub(r'[^\w\s\-\.\(\)\u4e00-\u9fff]', '', name)  # Include Chinese characters
        name = re.sub(r'\s+', ' ', name)
        return name.strip()
    
    def scan_folders(self) -> List[Path]:
        """
        Scan input directory to get all subdirectories (potential TV shows)
        Also caches folder structures to avoid re-scanning later
        
        Returns:
            List of folder paths
        """
        if not self.input_dir.exists() or not self.input_dir.is_dir():
            return []
        
        show_folders = [d for d in self.input_dir.iterdir() if d.is_dir()]
        show_folders = sorted(show_folders, key=lambda x: x.name.lower())
        
        # Cache folder structures to avoid re-scanning
        self.logger.debug(f"Caching folder structures for {len(show_folders)} folders...")
        for folder_path in show_folders:
            self._cache_folder_structure(folder_path)
        
        return show_folders
    
    def _cache_folder_structure(self, folder_path: Path, recursive: bool = True) -> None:
        """
        Scan and cache folder structure to avoid re-scanning later
        
        Args:
            folder_path: Path to the folder to scan and cache
            recursive: If True, recursively cache all subdirectories. If False, only cache immediate folder.
        """
        cache_key = str(folder_path)
        
        # Check if already cached
        if self.folder_cache.get(cache_key):
            return
        
        try:
            # Determine folder type
            folder_type = self.determine_folder_type(folder_path)
            
            # Get video files and subdirectories
            video_files = self.get_video_files(folder_path)
            subdirs = [d for d in folder_path.iterdir() if d.is_dir()] if folder_path.exists() else []
            
            # Get first file for quick access (check immediate files first, then recursively)
            first_file = video_files[0] if video_files else None
            first_file_name = first_file.name if first_file else None
            
            # If no files in immediate folder and recursive is enabled, find first file recursively
            if not first_file and recursive and subdirs:
                first_file, first_file_name = self._find_first_file_recursive(folder_path)
            
            # Create and cache folder structure
            folder_structure = FolderStructure(
                folder_path=folder_path,
                folder_type=folder_type,
                video_files=video_files,
                subdirs=subdirs,
                first_file=first_file,
                first_file_name=first_file_name
            )
            
            self.folder_cache.put(cache_key, folder_structure)
            self.logger.debug(f"Cached folder structure for: {folder_path.name} (type: {folder_type.value}, files: {len(video_files)}, subdirs: {len(subdirs)})")
            
            # Recursively cache all subdirectories
            if recursive:
                for subdir in subdirs:
                    self._cache_folder_structure(subdir, recursive=True)
            
        except Exception as e:
            self.logger.warning(f"Error caching folder structure for {folder_path}: {e}")
            # Create minimal structure on error
            folder_structure = FolderStructure(
                folder_path=folder_path,
                folder_type=FolderType.DIRECT_FILES,
                video_files=[],
                subdirs=[],
                first_file=None,
                first_file_name=None
            )
            self.folder_cache.put(cache_key, folder_structure)
    
    def _find_first_file_recursive(self, folder_path: Path) -> Tuple[Optional[Path], Optional[str]]:
        """
        Recursively find the first video file in a folder tree
        
        Args:
            folder_path: Path to start searching from
            
        Returns:
            Tuple of (first_file_path, first_file_name) or (None, None) if no file found
        """
        try:
            # Check immediate files first
            video_files = self.get_video_files(folder_path)
            if video_files:
                first_file = video_files[0]
                return first_file, first_file.name
            
            # Recursively check subdirectories
            subdirs = [d for d in folder_path.iterdir() if d.is_dir()] if folder_path.exists() else []
            for subdir in sorted(subdirs, key=lambda x: x.name.lower()):
                first_file, first_file_name = self._find_first_file_recursive(subdir)
                if first_file:
                    return first_file, first_file_name
            
            return None, None
        except Exception as e:
            self.logger.debug(f"Error finding first file recursively in {folder_path}: {e}")
            return None, None
    
    def batch_extract_with_llm(self, folder_names: List[str]) -> List[TVShowInfo]:
        """
        Call LLM agent to batch extract TV show information from folder names
        
        Args:
            folder_names: List of folder names to extract information from
            
        Returns:
            List of TVShowInfo objects
        """
        if not folder_names:
            return []
        
        self.logger.info(f"Extracting TV show info for {len(folder_names)} folders using LLM...")
        try:
            results = self.llm_agent.extract_tvshow(folder_names)
            self.logger.info(f"Successfully extracted info for {len(results)} folders")
            return results
        except Exception as e:
            self.logger.error(f"Error extracting TV show info with LLM: {e}")
            return [TVShowInfo(folder_name=name) for name in folder_names]
    
    def _detect_season_from_folder(self, folder_path: Path) -> Tuple[Optional[str], Optional[int]]:
        """
        Detect folder type and season number from folder structure and files
        Uses cached folder structure if available to avoid re-scanning
        
        Args:
            folder_path: Path to the folder
            
        Returns:
            Tuple of (folder_type, detected_season) where:
            - folder_type: "direct_files" or "season_subfolders" or None
            - detected_season: Season number if detected, None otherwise
        """
        if not folder_path.exists() or not folder_path.is_dir():
            return None, None
        
        # Try to get from cache first
        cache_key = str(folder_path)
        cached_structure = self.folder_cache.get(cache_key)
        
        if cached_structure:
            folder_type = cached_structure.folder_type
            video_files = cached_structure.video_files
            first_file = cached_structure.first_file
        else:
            # Fallback to scanning if not cached
            folder_type = self.determine_folder_type(folder_path)
            video_files = self.get_video_files(folder_path)
            first_file = video_files[0] if video_files else None
        
        if folder_type == FolderType.DIRECT_FILES:
            # Check folder name first for season number (e.g., "一人之下第二季", "The.Outcast.S02")
            # Use mode='folder' to exclude episode count patterns like "xx集"
            folder_season = extract_season_number(folder_path.name, None, mode='folder')
            
            # Validate folder_season - filter out unreasonable values
            if folder_season and not (1 <= folder_season <= 100):
                folder_season = None
            
            # Also check first file for season number
            file_season = None
            if first_file:
                detected_season, _, _ = extract_episode_info(first_file.name)
                if 1 <= detected_season <= 100:
                    file_season = detected_season
            
            # Use folder season if available and valid, otherwise use file season
            if folder_season:
                return "direct_files", folder_season
            elif file_season:
                return "direct_files", file_season
            else:
                return "direct_files", None
        else:
            return "season_subfolders", None
    
    def fetch_tmdb_metadata(self, tv_show_info: TVShowInfo, folder_path: Optional[Path] = None) -> Optional[TVShowMetadata]:
        """
        Call TMDB client to get metadata (with caching)
        
        Args:
            tv_show_info: TVShowInfo from LLM extraction
            folder_path: Optional path to folder for season detection
            
        Returns:
            TVShowMetadata if found, None otherwise
        """
        # Check cache first (by folder name or TMDB ID)
        cache_key = str(tv_show_info.tmdbid) if tv_show_info.tmdbid else tv_show_info.folder_name
        cached_metadata = self.cache.get(cache_key)
        if cached_metadata:
            self.logger.debug(f"Cache hit for: {tv_show_info.folder_name}")
            return cached_metadata
        
        # Detect folder type and season if folder_path provided
        folder_type = None
        detected_season = None
        if folder_path:
            folder_type, detected_season = self._detect_season_from_folder(folder_path)
            if folder_type and detected_season:
                self.logger.debug(f"Detected folder_type={folder_type}, season={detected_season} for {tv_show_info.folder_name}")
        
        # Fetch from TMDB
        self.logger.info(f"Fetching TMDB metadata for: {tv_show_info.folder_name}")
        try:
            metadata = self.tmdb_client.get_tv_show(
                folder_name=tv_show_info.folder_name,
                cn_name=tv_show_info.cn_name,
                en_name=tv_show_info.en_name,
                year=tv_show_info.year,
                tmdbid=tv_show_info.tmdbid,
                folder_type=folder_type,
                detected_season=detected_season
            )
            
            if metadata:
                # Store in cache
                cache_key = str(metadata.tmdbid) if metadata.tmdbid else tv_show_info.folder_name
                self.cache.put(cache_key, metadata)
                self.logger.info(f"Successfully fetched TMDB metadata for: {metadata.name} (ID: {metadata.id})")
            else:
                self.logger.warning(f"No TMDB metadata found for: {tv_show_info.folder_name}")
            
            return metadata
        except Exception as e:
            self.logger.error(f"Error fetching TMDB metadata for '{tv_show_info.folder_name}': {e}")
            return None
    
    def _file_operation_with_timeout(self, operation, *args, executor=None, **kwargs):
        """
        Execute file operation with timeout
        
        Args:
            operation: Function to execute
            *args: Positional arguments for operation
            executor: Optional ThreadPoolExecutor to reuse (if None, creates a new one)
            **kwargs: Keyword arguments for operation
            
        Returns:
            Result of operation
            
        Raises:
            FutureTimeoutError: If operation times out
        """
        import threading
        thread_id = threading.current_thread().ident
        op_name = operation.__name__ if hasattr(operation, '__name__') else str(operation)
        
        if executor is not None:
            # Check if we're already running in an executor thread to avoid deadlock
            # If we're in an executor thread and try to submit to the same executor, it will deadlock
            current_thread = threading.current_thread()
            is_in_executor_thread = any(
                current_thread is worker_thread 
                for worker_thread in getattr(executor, '_threads', set())
            )
            
            if is_in_executor_thread:
                # We're already in an executor thread - call operation directly with threading.Timer for timeout
                # This avoids deadlock from recursive executor submission
                self.logger.debug(f"      [DEBUG] _file_operation_with_timeout: {op_name} - Already in executor thread, calling directly with Timer timeout")
                
                result_container = {'result': None, 'exception': None, 'completed': False}
                
                def run_operation():
                    try:
                        result_container['result'] = operation(*args, **kwargs)
                    except Exception as e:
                        result_container['exception'] = e
                    finally:
                        result_container['completed'] = True
                
                # Start operation in a separate thread
                op_thread = threading.Thread(target=run_operation, daemon=True)
                op_thread.start()
                op_thread.join(timeout=self.file_operation_timeout)
                
                if not result_container['completed']:
                    self.logger.debug(f"      [DEBUG] _file_operation_with_timeout: {op_name} - TIMEOUT after {self.file_operation_timeout}s")
                    raise FutureTimeoutError(f"Operation {op_name} timed out after {self.file_operation_timeout}s")
                
                if result_container['exception']:
                    raise result_container['exception']
                
                return result_container['result']
            else:
                # Not in executor thread - safe to submit to executor
                self.logger.debug(f"      [DEBUG] _file_operation_with_timeout: {op_name} - Submitting to shared executor, Thread ID: {thread_id}")
                submit_start = datetime.now()
                future = executor.submit(operation, *args, **kwargs)
                submit_elapsed = (datetime.now() - submit_start).total_seconds()
                self.logger.debug(f"      [DEBUG] _file_operation_with_timeout: {op_name} - Submitted in {submit_elapsed:.4f}s, waiting for result (timeout={self.file_operation_timeout}s)")
                
                result_start = datetime.now()
                try:
                    result = future.result(timeout=self.file_operation_timeout)
                    result_elapsed = (datetime.now() - result_start).total_seconds()
                    self.logger.debug(f"      [DEBUG] _file_operation_with_timeout: {op_name} - Result received in {result_elapsed:.2f}s")
                    return result
                except FutureTimeoutError:
                    result_elapsed = (datetime.now() - result_start).total_seconds()
                    self.logger.debug(f"      [DEBUG] _file_operation_with_timeout: {op_name} - TIMEOUT after {result_elapsed:.2f}s (limit: {self.file_operation_timeout}s)")
                    raise
        else:
            # Create new executor for one-off operations
            self.logger.debug(f"      [DEBUG] _file_operation_with_timeout: {op_name} - Creating new executor (one-off operation)")
            with ThreadPoolExecutor(max_workers=1) as executor:
                future = executor.submit(operation, *args, **kwargs)
                return future.result(timeout=self.file_operation_timeout)
    
    def determine_folder_type(self, folder_path: Path) -> FolderType:
        """Determine if folder contains direct files or season subfolders"""
        if not folder_path.exists() or not folder_path.is_dir():
            return FolderType.DIRECT_FILES
        
        # Try to get from cache first
        cache_key = str(folder_path)
        cached_structure = self.folder_cache.get(cache_key)
        
        if cached_structure:
            # Use cached folder type
            return cached_structure.folder_type
        
        # Fallback to scanning if not cached
        # Count video files and subdirectories
        video_files = self.get_video_files(folder_path)
        subdirs = [d for d in folder_path.iterdir() if d.is_dir()]
        
        # If there are video files directly in the folder, it's direct files
        if video_files:
            return FolderType.DIRECT_FILES
        
        # If there are subdirectories with video files, it's season subfolders
        for subdir in subdirs:
            if self.get_video_files(subdir):
                return FolderType.SEASON_SUBFOLDERS
        
        return FolderType.DIRECT_FILES
    
    def process_direct_files_folder(self, folder_path: Path) -> Optional[TVShow]:
        """Process folder containing video files directly (Case 1)"""
        show_name = self.normalize_show_name(folder_path.name)
        video_files = self.get_video_files(folder_path)
        
        if not video_files:
            self.logger.warning(f"No video files found in {folder_path}")
            return None
        
        self.logger.info(f"Processing show: {Colors.CYAN}{show_name}{Colors.RESET} (Direct Files)")
        
        # For direct files, default to Season 1 unless we find clear season info
        # Try to extract season number from first file, but validate it
        first_file = video_files[0]
        detected_season, _, _ = extract_episode_info(first_file.name)
        
        # Only use detected season if it's reasonable (0-100), otherwise default to 1
        # Allow season 0 (Specials) if explicitly detected in filename
        # This prevents false matches from codec names (H265), years (2001), etc.
        if detected_season == 0:
            # Check if filename has explicit season 0 patterns (S00, Season 0, etc.)
            has_explicit_season_0 = bool(re.search(
                r'[Ss](?:eason\s*)?0{1,2}(?:[EePp]|\b)|第[零〇]季|零季',
                first_file.name, re.IGNORECASE
            ))
            if has_explicit_season_0:
                season_num = 0
            else:
                season_num = 1
                self.logger.debug(f"  Detected season 0 but no explicit pattern, defaulting to Season 1")
        elif 1 <= detected_season <= 100:
            season_num = detected_season
        else:
            season_num = 1
            self.logger.debug(f"  Detected season {detected_season} seems invalid, defaulting to Season 1")
        
        episodes = []
        for i, video_file in enumerate(video_files, 1):
            # Try to extract episode info, use position as fallback
            detected_season, detected_episode, end_episode = extract_episode_info(video_file.name, i)
            
            # Check if filename has explicit season pattern (S00, S01, Season 1, etc.)
            has_explicit_season = bool(re.search(
                r'[Ss](?:eason[.\s-]*)?\d+|[第][一二三四五六七八九十壹贰叁肆伍陆柒捌玖拾\d]+[季]',
                video_file.name, re.IGNORECASE
            ))
            
            # Validate detected season - allow season 0 if explicitly detected
            if detected_season == 0:
                # Check if filename has explicit season 0 patterns
                has_explicit_season_0 = bool(re.search(
                    r'[Ss](?:eason\s*)?0{1,2}(?:[EePp]|\b)|第[零〇]季|零季',
                    video_file.name, re.IGNORECASE
                ))
                if has_explicit_season_0:
                    # Use season 0 if explicitly detected
                    final_season = 0
                elif has_explicit_season:
                    # Has explicit season pattern but not 0, use detected season
                    final_season = detected_season if (1 <= detected_season <= 100) else season_num
                else:
                    final_season = season_num
            elif has_explicit_season and (1 <= detected_season <= 100):
                # File has explicit season pattern, use it (even if different from season_num)
                final_season = detected_season
            elif not (1 <= detected_season <= 100):
                # Invalid season, use default
                final_season = season_num
            else:
                # Valid season but no explicit pattern, use if consistent with season_num
                final_season = detected_season if detected_season == season_num else season_num
            
            final_episode = detected_episode if detected_episode != i else i
            
            episode = Episode(
                original_path=video_file,
                show_name=show_name,
                season_number=final_season,
                episode_number=final_episode,
                extension=video_file.suffix,
                end_episode_number=end_episode
            )
            episodes.append(episode)
            
            self.logger.debug(f"  Episode: {video_file.name} -> S{final_season:02d}E{final_episode:02d}")
        
        # Group episodes by season number to handle mixed seasons
        episodes_by_season = {}
        for episode in episodes:
            season_key = episode.season_number
            if season_key not in episodes_by_season:
                episodes_by_season[season_key] = []
            episodes_by_season[season_key].append(episode)
        
        # Create Season objects for each unique season
        seasons = []
        for season_num, season_episodes in sorted(episodes_by_season.items()):
            season = Season(
                show_name=show_name,
                season_number=season_num,
                episodes=season_episodes,
                original_folder=folder_path
            )
            seasons.append(season)
            self.logger.debug(f"  Created Season {season_num} with {len(season_episodes)} episodes")
        
        return TVShow(
            name=show_name,
            seasons=seasons,
            original_folder=folder_path,
            folder_type=FolderType.DIRECT_FILES
        )
    
    def process_season_subfolders(self, folder_path: Path) -> Optional[TVShow]:
        """Process folder containing season subfolders (Case 2)"""
        show_name = self.normalize_show_name(folder_path.name)
        subdirs = [d for d in folder_path.iterdir() if d.is_dir()]
        
        if not subdirs:
            self.logger.warning(f"No subdirectories found in {folder_path}")
            return None
        
        self.logger.info(f"Processing show: {Colors.CYAN}{show_name}{Colors.RESET} (Season Subfolders)")
        
        seasons = []
        for subdir in sorted(subdirs, key=lambda x: x.name.lower()):
            video_files = self.get_video_files(subdir)
            if not video_files:
                self.logger.debug(f"  Skipping {subdir.name} (no video files)")
                continue
            
            # Extract season number from folder name (initial attempt)
            # Use mode='folder' to exclude episode count patterns like "xx集"
            folder_season = extract_season_number(subdir.name, None, mode='folder')
            if folder_season:
                self.logger.debug(f"    Extracted season {folder_season} from folder name: {subdir.name}")
            
            # Validate folder_season - filter out unreasonable values
            # Allow season 0 (Specials) as it's a valid season number
            if folder_season is not None and not (0 <= folder_season <= 100):
                self.logger.debug(f"    Ignoring invalid season {folder_season} from folder name")
                folder_season = None
            
            # Check if files have more reliable season information
            file_seasons = []
            for video_file in video_files:
                file_season, _, _ = extract_episode_info(video_file.name)
                # Only consider reasonable season numbers (0-100)
                # For season 0 (Specials), only include if explicitly detected in filename
                if file_season == 0:
                    # Check if filename has explicit season 0 patterns (S00, Season 0, etc.)
                    # Pattern allows: S00, S0, Season 0, Season 00, S00E, S0E, etc.
                    has_explicit_season_0 = bool(re.search(
                        r'[Ss](?:eason\s*)?0{1,2}(?:[EePp]|\b)|第[零〇]季|零季',
                        video_file.name, re.IGNORECASE
                    ))
                    if has_explicit_season_0:
                        file_seasons.append(file_season)
                # For season 1, only include if explicitly detected in filename (not just default)
                elif file_season == 1:
                    # Check if filename has explicit season patterns (S01, Season 1, etc.)
                    # Pattern allows: S01, S1, Season 1, Season 01, S01E, S1E, etc.
                    # Note: (?=[EePp]|\b|\.) allows E/P, word boundary, or period after season number
                    has_explicit_season = bool(re.search(
                        r'[Ss](?:eason[.\s-]*)?0?1(?=[EePp]|\b|\.)|第[一壹]季|一季',
                        video_file.name, re.IGNORECASE
                    ))
                    if has_explicit_season:
                        file_seasons.append(file_season)
                elif 1 < file_season <= 100:
                    file_seasons.append(file_season)
            
            # Determine the most reliable season number
            if file_seasons:
                # Use file-based season if we have consistent season info from files
                unique_file_seasons = list(set(file_seasons))
                if len(unique_file_seasons) == 1:
                    # All files agree on season number
                    season_num = unique_file_seasons[0]
                    self.logger.debug(f"    Using season {season_num} from filenames (folder name unclear)")
                elif folder_season:
                    # Files inconsistent, but folder has season info
                    season_num = folder_season
                    self.logger.debug(f"    Using season {season_num} from folder name (files inconsistent)")
                else:
                    # Use most common season from files
                    season_num = max(set(file_seasons), key=file_seasons.count)
                    self.logger.debug(f"    Using most common season {season_num} from filenames")
            elif folder_season:
                # No file season info, use folder season
                season_num = folder_season
                self.logger.debug(f"    Using season {season_num} from folder name")
            else:
                # Fallback to position-based numbering
                season_num = len(seasons) + 1
                self.logger.debug(f"    Using fallback season {season_num} (no clear season info)")
            
            self.logger.info(f"  Processing Season {season_num}: {Colors.YELLOW}{subdir.name}{Colors.RESET}")
            
            episodes = []
            for i, video_file in enumerate(video_files, 1):
                # Extract episode info
                file_season, episode_num, end_episode = extract_episode_info(video_file.name, i)
                
                # Use the determined season number, not the one from individual files
                final_season = season_num
                
                episode = Episode(
                    original_path=video_file,
                    show_name=show_name,
                    season_number=final_season,
                    episode_number=episode_num,
                    extension=video_file.suffix,
                    end_episode_number=end_episode
                )
                episodes.append(episode)
                
                self.logger.debug(f"    Episode: {video_file.name} -> S{final_season:02d}E{episode_num:02d}")
            
            season = Season(
                show_name=show_name,
                season_number=season_num,
                episodes=episodes,
                original_folder=subdir
            )
            seasons.append(season)
        
        if not seasons:
            self.logger.warning(f"No valid seasons found in {folder_path}")
            return None
        
        return TVShow(
            name=show_name,
            seasons=seasons,
            original_folder=folder_path,
            folder_type=FolderType.SEASON_SUBFOLDERS
        )
    
    def _move_single_episode(self, episode: Episode, new_path: Path, tv_show: TVShow, 
                             show_folder: Path, folder_file_counts: Dict, executor: ThreadPoolExecutor) -> Dict:
        """
        Move a single episode file with timeout
        
        Args:
            episode: Episode to move
            new_path: Destination path for the file
            tv_show: TVShow object for context
            show_folder: Show folder path for tracking
            folder_file_counts: Dictionary tracking file counts per folder
            executor: ThreadPoolExecutor to use for timeout
        
        Returns:
            Dictionary with episode details and status
        """
        import threading
        thread_id = threading.current_thread().ident
        start_time = datetime.now()
        
        episode_details = {
            'episode_number': episode.episode_number,
            'original_file': episode.original_path.name,
            'original_path': str(episode.original_path),
            'new_file': new_path.name,
            'new_path': str(new_path.relative_to(self.output_dir)),
            'status': 'pending'
        }
        
        self.logger.debug(f"    [DEBUG] E{episode.episode_number:02d} START - Thread ID: {thread_id}, Source: {episode.original_path.name[:50]}...")
        
        try:
            # Check file size for logging
            file_size = 0
            try:
                if episode.original_path.exists():
                    file_size = episode.original_path.stat().st_size
                    self.logger.debug(f"    [DEBUG] E{episode.episode_number:02d} File size: {file_size / (1024*1024*1024):.2f}GB")
            except Exception as e:
                self.logger.debug(f"    [DEBUG] E{episode.episode_number:02d} Could not get file size: {e}")
            
            # Log executor status before operation
            if hasattr(executor, '_threads'):
                active_count = len([t for t in executor._threads if t.is_alive()])
                self.logger.debug(f"    [DEBUG] E{episode.episode_number:02d} Executor active threads: {active_count}/{executor._max_workers}")
            
            # Check if destination file already exists - skip if it does
            if new_path.exists():
                self.logger.warning(f"    {Colors.YELLOW}Destination file already exists, skipping: {new_path.name}{Colors.RESET}")
                self.logger.debug(f"    [DEBUG] E{episode.episode_number:02d} SKIPPED - File already exists at destination")
                episode_details['status'] = 'skipped'
                episode_details['error'] = 'Destination file already exists'
                # Do NOT count as moved - source file remains for user to decide later
                # Do NOT increment folder_file_counts - file stays in source location
                return episode_details
            
            # Move (rename) the file with timeout using shared executor
            self.logger.debug(f"    [DEBUG] E{episode.episode_number:02d} Calling _file_operation_with_timeout (timeout={self.file_operation_timeout}s)")
            move_start = datetime.now()
            self._file_operation_with_timeout(shutil.move, str(episode.original_path), str(new_path), executor=executor)
            move_elapsed = (datetime.now() - move_start).total_seconds()
            self.logger.debug(f"    [DEBUG] E{episode.episode_number:02d} Move completed in {move_elapsed:.2f}s")
            
            self.stats['episodes_moved'] += 1
            episode_details['status'] = 'moved'
            
            # Track successful move for folder cleanup (thread-safe increment)
            if tv_show.folder_type == FolderType.DIRECT_FILES:
                folder_file_counts[show_folder]['moved'] += 1
            else:
                episode_folder = episode.original_path.parent
                if episode_folder in folder_file_counts:
                    folder_file_counts[episode_folder]['moved'] += 1
            
            total_elapsed = (datetime.now() - start_time).total_seconds()
            self.logger.debug(f"    [DEBUG] E{episode.episode_number:02d} SUCCESS - Total time: {total_elapsed:.2f}s")
            
        except FutureTimeoutError as e:
            total_elapsed = (datetime.now() - start_time).total_seconds()
            self.logger.error(f"Timeout moving file: {episode.original_path}")
            self.logger.debug(f"    [DEBUG] E{episode.episode_number:02d} TIMEOUT - Elapsed: {total_elapsed:.2f}s, Timeout limit: {self.file_operation_timeout}s, Thread ID: {thread_id}")
            self.stats['errors'] += 1
            episode_details['status'] = 'timeout'
            episode_details['error'] = f'Timeout moving file (elapsed: {total_elapsed:.2f}s, limit: {self.file_operation_timeout}s)'
        except Exception as e:
            total_elapsed = (datetime.now() - start_time).total_seconds()
            self.logger.error(f"Failed to move {episode.original_path}: {e}")
            self.logger.debug(f"    [DEBUG] E{episode.episode_number:02d} ERROR - Type: {type(e).__name__}, Message: {str(e)}, Elapsed: {total_elapsed:.2f}s, Thread ID: {thread_id}")
            self.stats['errors'] += 1
            episode_details['status'] = 'error'
            episode_details['error'] = str(e)
        
        return episode_details
    
    def _match_episode_with_tmdb(self, episode: Episode, tmdb_metadata: TVShowMetadata) -> None:
        """
        Match episode with TMDB metadata and set TMDB title
        For multi-episode files, collects titles for all episodes in the range
        
        Args:
            episode: Episode to match
            tmdb_metadata: TMDB metadata with seasons and episodes
        """
        if not tmdb_metadata or not tmdb_metadata.seasons:
            return
        
        # Find matching season in TMDB metadata
        for tmdb_season in tmdb_metadata.seasons:
            if tmdb_season.season_number == episode.season_number:
                # Check if this is a multi-episode file
                if episode.end_episode_number:
                    # Multi-episode file: collect titles only for first and last episodes (from...to pattern)
                    titles = []
                    # Get title for first episode (episode_number)
                    for tmdb_episode in tmdb_season.episodes:
                        if tmdb_episode.episode_number == episode.episode_number:
                            titles.append(tmdb_episode.title)
                            self.logger.debug(f"  Matched S{episode.season_number:02d}E{episode.episode_number:02d} with TMDB title: {tmdb_episode.title}")
                            break
                    
                    # Get title for last episode (end_episode_number) - only if different from first
                    if episode.end_episode_number != episode.episode_number:
                        for tmdb_episode in tmdb_season.episodes:
                            if tmdb_episode.episode_number == episode.end_episode_number:
                                titles.append(tmdb_episode.title)
                                self.logger.debug(f"  Matched S{episode.season_number:02d}E{episode.end_episode_number:02d} with TMDB title: {tmdb_episode.title}")
                                break
                    
                    # Join titles with "-" separator (only first and last episode titles)
                    if titles:
                        episode.tmdb_title = "-".join(titles)
                        self.logger.debug(f"  Multi-episode S{episode.season_number:02d}E{episode.episode_number:02d}-E{episode.end_episode_number:02d} titles: {episode.tmdb_title}")
                else:
                    # Single episode: find matching episode in TMDB season
                    for tmdb_episode in tmdb_season.episodes:
                        if tmdb_episode.episode_number == episode.episode_number:
                            episode.tmdb_title = tmdb_episode.title
                            self.logger.debug(f"  Matched S{episode.season_number:02d}E{episode.episode_number:02d} with TMDB title: {tmdb_episode.title}")
                            return
                break
    
    def organize_show(self, tv_show: TVShow) -> bool:
        """Organize a TV show into Emby format using TMDB metadata"""
        # Create a single executor for all file operations in this show (optimization #3)
        # max_workers=2 to respect cloud storage thread limits (1 show × 2 episodes = 2 concurrent operations)
        file_operation_executor = ThreadPoolExecutor(max_workers=2) if not self.dry_run else None
        
        try:
            # Generate folder name using TMDB metadata: {tmdb_name} ({year}) {{tmdb-{tmdb_id}}}
            # Optionally add category subfolder: {output_dir}/{category}/{folder_name}
            category = None
            if tv_show.tmdb_metadata:
                # Always use TMDB metadata name for organizing
                show_name = tv_show.tmdb_metadata.name
                # Always use year from TMDB result
                year = tv_show.tmdb_metadata.year
                # Always use TMDB ID from TMDB result
                tmdb_id = tv_show.tmdb_metadata.id
                if year and tmdb_id:
                    folder_name = f"{show_name} ({year}) {{tmdb-{tmdb_id}}}"
                elif year:
                    folder_name = f"{show_name} ({year})"
                elif tmdb_id:
                    folder_name = f"{show_name} {{tmdb-{tmdb_id}}}"
                else:
                    folder_name = show_name
                tmdb_show_name = tv_show.tmdb_metadata.name
                
                # Determine category for this show
                if self.category_helper:
                    category = self.category_helper.get_tv_category(tv_show.tmdb_metadata)
                    if category:
                        self.logger.info(f"  Category: {Colors.CYAN}{category}{Colors.RESET}")
                
                # Match episodes with TMDB metadata to get episode titles
                for season in tv_show.seasons:
                    for episode in season.episodes:
                        self._match_episode_with_tmdb(episode, tv_show.tmdb_metadata)
            else:
                folder_name = tv_show.name
                tmdb_show_name = None
            
            # Build output path: {output_dir}/{category}/{folder_name} or {output_dir}/{folder_name}
            if category:
                show_output_dir = self.output_dir / category / folder_name
            else:
                show_output_dir = self.output_dir / folder_name
            show_details = {
                'name': tv_show.name,
                'folder_type': tv_show.folder_type.value,
                'original_folder': str(tv_show.original_folder),
                'category': category,
                'seasons': []
            }
            
            # Track files found and moved per folder for cleanup
            # Key: folder Path, Value: {'found': count, 'moved': count}
            folder_file_counts = {}
            
            # Get show folder for tracking (used in both folder types)
            show_folder = tv_show.original_folder
            
            # For direct files, also track the show folder
            if tv_show.folder_type == FolderType.DIRECT_FILES:
                total_episodes = sum(len(s.episodes) for s in tv_show.seasons)
                folder_file_counts[show_folder] = {'found': total_episodes, 'moved': 0}
            
            for season in tv_show.seasons:
                season_dir = show_output_dir / f"Season {season.season_number}"

                self.logger.info(f"  Organizing Season {season.season_number} -> {Colors.GREEN}{season_dir.relative_to(self.output_dir)}{Colors.RESET}")
                
                season_details = {
                    'season_number': season.season_number,
                    'episodes': []
                }
                
                # Track files in this season's original folder (for season subfolders case)
                season_folder = season.original_folder
                if tv_show.folder_type == FolderType.SEASON_SUBFOLDERS:
                    if season_folder not in folder_file_counts:
                        folder_file_counts[season_folder] = {'found': 0, 'moved': 0}
                    folder_file_counts[season_folder]['found'] = len(season.episodes)
                
                # Create season directory with timeout using shared executor
                if not self.dry_run:
                    try:
                        self._file_operation_with_timeout(season_dir.mkdir, parents=True, exist_ok=True, executor=file_operation_executor)
                    except FutureTimeoutError:
                        self.logger.error(f"Timeout creating season directory: {season_dir}")
                        self.stats['errors'] += 1
                        if file_operation_executor:
                            file_operation_executor.shutdown(wait=True)
                        return False
                    except Exception as e:
                        self.logger.error(f"Error creating season directory {season_dir}: {e}")
                        self.stats['errors'] += 1
                        if file_operation_executor:
                            file_operation_executor.shutdown(wait=True)
                        return False
                
                # Prepare episode move tasks (optimization #2: parallelize episode moves)
                episode_tasks = []
                for episode in season.episodes:
                    new_filename = generate_filename(episode, tmdb_show_name=tmdb_show_name)
                    new_path = season_dir / new_filename
                    
                    # Log the operation
                    self.logger.info(f"    {Colors.YELLOW}Moving:{Colors.RESET} {episode.original_path.name}")
                    self.logger.info(f"    {Colors.GREEN}To:{Colors.RESET} {new_path.relative_to(self.output_dir)}")
                    
                    episode_tasks.append((episode, new_path))
                
                # Process episodes in parallel (optimization #2)
                if not self.dry_run and file_operation_executor:
                    # Submit all episode moves in parallel
                    self.logger.debug(f"    [DEBUG] Submitting {len(episode_tasks)} episode move tasks to executor (max_workers=2)")
                    future_to_episode = {}
                    for idx, (episode, new_path) in enumerate(episode_tasks):
                        future = file_operation_executor.submit(
                            self._move_single_episode,
                            episode, new_path, tv_show, show_folder, folder_file_counts, file_operation_executor
                        )
                        future_to_episode[future] = (episode, new_path)
                        self.logger.debug(f"    [DEBUG] Submitted E{episode.episode_number:02d} to executor (task {idx+1}/{len(episode_tasks)})")
                    
                    # Log executor status
                    self.logger.debug(f"    [DEBUG] Executor active threads: {file_operation_executor._threads}, queue size: {file_operation_executor._work_queue.qsize() if hasattr(file_operation_executor._work_queue, 'qsize') else 'N/A'}")
                    
                    # Collect results as they complete (maintain order for reporting)
                    episode_results = {}
                    completed_count = 0
                    start_time = datetime.now()
                    for future in as_completed(future_to_episode):
                        episode, new_path = future_to_episode[future]
                        completed_count += 1
                        elapsed = (datetime.now() - start_time).total_seconds()
                        self.logger.debug(f"    [DEBUG] Future completed for E{episode.episode_number:02d} ({completed_count}/{len(episode_tasks)}), elapsed: {elapsed:.2f}s")
                        
                        try:
                            episode_details = future.result()
                            episode_results[episode.episode_number] = episode_details
                            self.logger.debug(f"    [DEBUG] E{episode.episode_number:02d} result: status={episode_details.get('status')}, error={episode_details.get('error', 'None')}")
                        except Exception as e:
                            self.logger.error(f"Unexpected error processing episode {episode.episode_number}: {e}")
                            self.logger.debug(f"    [DEBUG] E{episode.episode_number:02d} exception type: {type(e).__name__}, message: {str(e)}")
                            episode_results[episode.episode_number] = {
                                'episode_number': episode.episode_number,
                                'original_file': episode.original_path.name,
                                'original_path': str(episode.original_path),
                                'new_file': new_path.name,
                                'new_path': str(new_path.relative_to(self.output_dir)),
                                'status': 'error',
                                'error': str(e)
                            }
                    
                    # Add episode details in episode number order for consistent reporting
                    for episode, new_path in episode_tasks:
                        if episode.episode_number in episode_results:
                            season_details['episodes'].append(episode_results[episode.episode_number])
                        else:
                            # Fallback if episode not in results
                            season_details['episodes'].append({
                                'episode_number': episode.episode_number,
                                'original_file': episode.original_path.name,
                                'original_path': str(episode.original_path),
                                'new_file': new_path.name,
                                'new_path': str(new_path.relative_to(self.output_dir)),
                                'status': 'error',
                                'error': 'Episode processing failed'
                            })
                else:
                    # Dry-run mode: just create episode details without moving
                    for episode, new_path in episode_tasks:
                        self.stats['episodes_moved'] += 1
                        episode_details = {
                            'episode_number': episode.episode_number,
                            'original_file': episode.original_path.name,
                            'original_path': str(episode.original_path),
                            'new_file': new_path.name,
                            'new_path': str(new_path.relative_to(self.output_dir)),
                            'status': 'dry_run'
                        }
                        # In dry-run, also track for reporting
                        if tv_show.folder_type == FolderType.DIRECT_FILES:
                            folder_file_counts[show_folder]['moved'] += 1
                        else:
                            episode_folder = episode.original_path.parent
                            if episode_folder in folder_file_counts:
                                folder_file_counts[episode_folder]['moved'] += 1
                        season_details['episodes'].append(episode_details)
                
                # After processing all episodes in this season, check if folder is empty and remove it
                if not self.dry_run and tv_show.folder_type == FolderType.SEASON_SUBFOLDERS:
                    if season_folder in folder_file_counts:
                        counts = folder_file_counts[season_folder]
                        if counts['found'] > 0 and counts['found'] == counts['moved']:
                            try:
                                self._file_operation_with_timeout(season_folder.rmdir, executor=file_operation_executor)
                                self.logger.info(f"    {Colors.CYAN}Removed empty folder: {season_folder}{Colors.RESET}")
                            except FutureTimeoutError:
                                self.logger.warning(f"Timeout removing folder: {season_folder}")
                            except OSError:
                                # Folder not empty or doesn't exist, skip silently
                                pass
                
                show_details['seasons'].append(season_details)
                self.stats['seasons_processed'] += 1
            
            # After processing all seasons, check if show folder is empty and remove it
            if not self.dry_run:
                show_folder = tv_show.original_folder
                if tv_show.folder_type == FolderType.DIRECT_FILES:
                    # For direct files, check if all files from the show folder were moved
                    if show_folder in folder_file_counts:
                        counts = folder_file_counts[show_folder]
                        if counts['found'] > 0 and counts['found'] == counts['moved']:
                            try:
                                self._file_operation_with_timeout(show_folder.rmdir, executor=file_operation_executor)
                                self.logger.info(f"  {Colors.CYAN}Removed empty show folder: {show_folder}{Colors.RESET}")
                            except FutureTimeoutError:
                                self.logger.warning(f"Timeout removing show folder: {show_folder}")
                            except OSError:
                                # Folder not empty or doesn't exist, skip silently
                                pass
                else:
                    # For season subfolders, check if all season folders were removed
                    # Count how many season folders should have been removed
                    seasons_removed = 0
                    total_seasons = len(tv_show.seasons)
                    for season in tv_show.seasons:
                        season_folder = season.original_folder
                        if season_folder in folder_file_counts:
                            counts = folder_file_counts[season_folder]
                            if counts['found'] > 0 and counts['found'] == counts['moved']:
                                seasons_removed += 1
                    
                    # If all season folders were removed, the show folder should be empty
                    if seasons_removed == total_seasons and total_seasons > 0:
                        try:
                            self._file_operation_with_timeout(show_folder.rmdir, executor=file_operation_executor)
                            self.logger.info(f"  {Colors.CYAN}Removed empty show folder: {show_folder}{Colors.RESET}")
                        except FutureTimeoutError:
                            self.logger.warning(f"Timeout removing show folder: {show_folder}")
                        except OSError:
                            # Folder not empty or doesn't exist, skip silently
                            pass
            
            self.stats['shows_processed'] += 1
            self.processed_shows.append(show_details)
            
            # Shutdown executor (optimization #3)
            if file_operation_executor:
                file_operation_executor.shutdown(wait=True)
            
            return True
            
        except Exception as e:
            self.logger.error(f"Failed to organize show {tv_show.name}: {e}")
            self.stats['errors'] += 1
            # Ensure executor is shut down even on error
            if file_operation_executor:
                file_operation_executor.shutdown(wait=True)
            return False
    
    def scan_and_organize(self) -> bool:
        """Main method to scan input directory and organize all shows with LLM and TMDB integration"""
        if not self.input_dir.exists():
            self.logger.error(f"Input directory does not exist: {self.input_dir}")
            return False
        
        if not self.input_dir.is_dir():
            self.logger.error(f"Input path is not a directory: {self.input_dir}")
            return False
        
        # Create output directory if it doesn't exist
        if not self.dry_run:
            try:
                self._file_operation_with_timeout(self.output_dir.mkdir, parents=True, exist_ok=True)
            except FutureTimeoutError:
                self.logger.error(f"Timeout creating output directory: {self.output_dir}")
                return False
            except Exception as e:
                self.logger.error(f"Error creating output directory: {e}")
                return False
        
        self.logger.info(f"\n{Colors.BOLD}Scanning input directory...{Colors.RESET}")
        
        # Step 1: Scan input directory → get all subdirectories
        show_folders = self.scan_folders()
        
        if not show_folders:
            self.logger.warning("No subdirectories found in input directory")
            return False
        
        self.logger.info(f"Found {len(show_folders)} potential TV show folders")
        
        # Step 2: Batch extract TV show info using LLM agent (all folders at once)
        # Optionally include first file name for better context
        folder_names = [folder.name for folder in show_folders]
        # Get first file names from cache for LLM context (if available)
        folder_contexts = []
        for folder_path in show_folders:
            cache_key = str(folder_path)
            cached_structure = self.folder_cache.get(cache_key)
            if cached_structure and cached_structure.first_file_name:
                # Include first file name for better LLM context
                folder_contexts.append(f"{folder_path.name} | First file: {cached_structure.first_file_name}")
            else:
                folder_contexts.append(folder_path.name)
        
        tv_show_infos = self.batch_extract_with_llm(folder_contexts)
        
        # Create a mapping from folder name to TVShowInfo
        # Handle case where LLM might return enhanced context in folder_name
        folder_info_map = {}
        for info in tv_show_infos:
            # Extract original folder name (before "|" if present)
            original_folder_name = info.folder_name.split(" | ")[0] if " | " in info.folder_name else info.folder_name
            # Update folder_name to original for consistency
            info.folder_name = original_folder_name
            folder_info_map[original_folder_name] = info
        
        # Step 3: Fetch TMDB metadata for each show (with threading and caching)
        self.logger.info(f"\n{Colors.BOLD}Fetching TMDB metadata...{Colors.RESET}")
        metadata_map = {}  # folder_name -> TVShowMetadata
        
        def fetch_metadata_for_show(folder_path: Path) -> Tuple[str, Optional[TVShowMetadata]]:
            """Helper function to fetch metadata for a single show"""
            folder_name = folder_path.name
            tv_show_info = folder_info_map.get(folder_name, TVShowInfo(folder_name=folder_name))
            metadata = self.fetch_tmdb_metadata(tv_show_info, folder_path=folder_path)
            return folder_name, metadata
        
        # Fetch metadata sequentially (max_workers=1) with rate limit 50 req/sec
        # Sequential processing ensures no concurrent requests while rate limit
        # allows fast sequential processing without waiting
        with ThreadPoolExecutor(max_workers=1) as executor:
            future_to_folder = {executor.submit(fetch_metadata_for_show, folder): folder for folder in show_folders}
            for future in as_completed(future_to_folder):
                try:
                    folder_name, metadata = future.result()
                    metadata_map[folder_name] = metadata
                except Exception as e:
                    folder = future_to_folder[future]
                    self.logger.error(f"Error fetching metadata for {folder.name}: {e}")
                    metadata_map[folder.name] = None
        
        # Step 4: Process shows - filter by confidence and organize
        self.logger.info(f"\n{Colors.BOLD}Processing shows...{Colors.RESET}")
        
        # Separate shows into high-confidence (to process) and low/medium confidence (to skip)
        shows_to_process = []
        shows_to_skip = []
        
        for show_folder in show_folders:
            folder_name = show_folder.name
            tv_show_info = folder_info_map.get(folder_name, TVShowInfo(folder_name=folder_name))
            metadata = metadata_map.get(folder_name)
            
            # Check confidence level
            if metadata and metadata.match_confidence == "high":
                shows_to_process.append((show_folder, tv_show_info, metadata))
            else:
                reason = "no TMDB match" if not metadata else f"low/medium confidence ({metadata.match_confidence})"
                shows_to_skip.append((show_folder, reason))
                self.unprocessed_shows.append({
                    'folder_name': folder_name,
                    'reason': reason
                })
        
        self.logger.info(f"Found {len(shows_to_process)} shows with high confidence to process")
        self.logger.info(f"Found {len(shows_to_skip)} shows to skip (low/medium confidence or no TMDB match)")
        
        # Step 5: Organize files using TMDB metadata
        # Process shows sequentially (max_workers=1) to respect cloud storage thread limits
        # Combined with episode-level parallelism (max_workers=2), total = 1 show × 2 episodes = 2 concurrent operations
        success_count = 0
        
        def process_single_show(show_folder: Path, tv_show_info: TVShowInfo, metadata: TVShowMetadata) -> Tuple[str, bool]:
            """Helper function to process a single show"""
            try:
                # Determine folder structure type
                folder_type = self.determine_folder_type(show_folder)
                
                # Process based on folder type
                if folder_type == FolderType.DIRECT_FILES:
                    tv_show = self.process_direct_files_folder(show_folder)
                else:
                    tv_show = self.process_season_subfolders(show_folder)
                
                if not tv_show:
                    return show_folder.name, False
                
                # Attach TMDB metadata to TVShow
                tv_show.tmdb_metadata = metadata
                # Store LLM-extracted names for reference (not used for organizing)
                tv_show.cn_name = tv_show_info.cn_name
                tv_show.en_name = tv_show_info.en_name
                # Always use year from TMDB result
                tv_show.year = metadata.year if metadata else None
                # Always use TMDB ID from TMDB result
                tv_show.tmdb_id = metadata.id if metadata else None
                tv_show.match_confidence = metadata.match_confidence
                
                # Filter seasons: only process seasons that exist in files
                # (ignore TMDB seasons not present in file structure)
                file_season_numbers = {season.season_number for season in tv_show.seasons}
                if metadata.seasons:
                    # Filter TMDB seasons to only those that exist in files
                    filtered_tmdb_seasons = [
                        s for s in metadata.seasons 
                        if s.season_number in file_season_numbers
                    ]
                    metadata.seasons = filtered_tmdb_seasons
                
                # Organize the show
                success = self.organize_show(tv_show)
                return show_folder.name, success
            except Exception as e:
                self.logger.error(f"Error processing show {show_folder.name}: {e}")
                return show_folder.name, False
        
        # Process shows sequentially (max_workers=1) to respect cloud storage thread limits
        with ThreadPoolExecutor(max_workers=1) as executor:
            future_to_show = {
                executor.submit(process_single_show, folder, info, metadata): folder.name
                for folder, info, metadata in shows_to_process
            }
            
            for future in as_completed(future_to_show):
                try:
                    folder_name, success = future.result()
                    if success:
                        success_count += 1
                        self.logger.info(f"{Colors.GREEN}✓ Successfully processed: {folder_name}{Colors.RESET}")
                    else:
                        self.logger.error(f"{Colors.RED}✗ Failed to process: {folder_name}{Colors.RESET}")
                        self.unprocessed_shows.append({
                            'folder_name': folder_name,
                            'reason': 'processing error'
                        })
                except Exception as e:
                    folder_name = future_to_show[future]
                    self.logger.error(f"Error in parallel processing for {folder_name}: {e}")
                    self.unprocessed_shows.append({
                        'folder_name': folder_name,
                        'reason': f'error: {str(e)}'
                    })
        
        return success_count > 0
    
    def print_summary(self):
        """Print operation summary"""
        self.end_time = datetime.now()
        duration = self.end_time - self.start_time
        
        self.logger.info(f"\n{Colors.BOLD}{'='*60}{Colors.RESET}")
        self.logger.info(f"{Colors.BOLD}OPERATION SUMMARY{Colors.RESET}")
        self.logger.info(f"{Colors.BOLD}{'='*60}{Colors.RESET}")
        
        self.logger.info(f"Shows Processed: {Colors.CYAN}{self.stats['shows_processed']}{Colors.RESET}")
        self.logger.info(f"Seasons Processed: {Colors.CYAN}{self.stats['seasons_processed']}{Colors.RESET}")
        self.logger.info(f"Episodes Moved: {Colors.CYAN}{self.stats['episodes_moved']}{Colors.RESET}")
        
        if self.stats['errors'] > 0:
            self.logger.info(f"Errors: {Colors.RED}{self.stats['errors']}{Colors.RESET}")
        else:
            self.logger.info(f"Errors: {Colors.GREEN}0{Colors.RESET}")
        
        self.logger.info(f"Duration: {Colors.CYAN}{duration}{Colors.RESET}")
        
        # Print unprocessed shows summary
        if self.unprocessed_shows:
            self.logger.info(f"\n{Colors.BOLD}Unprocessed Shows:{Colors.RESET}")
            for item in self.unprocessed_shows:
                self.logger.info(f"  {Colors.YELLOW}{item['folder_name']}{Colors.RESET}: {item['reason']}")
        else:
            self.logger.info(f"\n{Colors.GREEN}All shows processed successfully!{Colors.RESET}")
        
        if self.dry_run:
            self.logger.info(f"\n{Colors.YELLOW}This was a DRY RUN - no files were actually moved.{Colors.RESET}")
            self.logger.info(f"{Colors.YELLOW}Remove --dry-run flag to perform actual organization.{Colors.RESET}")
        
        # Generate HTML report
        try:
            generate_html_report(
                report_file=self.report_file,
                stats=self.stats,
                processed_shows=self.processed_shows,
                start_time=self.start_time,
                end_time=self.end_time,
                duration=duration,
                dry_run=self.dry_run,
                input_dir=self.input_dir,
                output_dir=self.output_dir,
                log_file=self.log_file
            )
            self.logger.info(f"\n{Colors.CYAN}Report saved to: {self.report_file}{Colors.RESET}")
            
            # Clean up old files after generating new report
            self._cleanup_old_files()
        except Exception as e:
            self.logger.error(f"Failed to generate HTML report: {e}")

def main():
    """Main entry point"""
    parser = argparse.ArgumentParser(
        description="TV Show Media Library Organizer - Reorganize TV shows following Emby naming conventions",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  %(prog)s /path/to/tv/shows /path/to/organized --dry-run
  %(prog)s "/Users/john/TV Shows" "/Users/john/Organized TV" --verbose
  %(prog)s ~/Downloads/TV ~/Media/TV --dry-run --verbose
        """
    )
    
    parser.add_argument('input_dir', help='Input directory containing TV show folders')
    parser.add_argument('output_dir', help='Output directory for organized TV shows')
    parser.add_argument('--dry-run', action='store_true', help='Preview changes without moving files')
    parser.add_argument('--verbose', '-v', action='store_true', help='Enable verbose logging')
    parser.add_argument('--log-dir', help='Directory to save log files (default: project_root/logs)')
    parser.add_argument('--version', action='version', version='%(prog)s 1.0.0')
    
    args = parser.parse_args()
    
    try:
        organizer = TVShowOrganizer(
            input_dir=args.input_dir,
            output_dir=args.output_dir,
            dry_run=args.dry_run,
            verbose=args.verbose,
            log_dir=args.log_dir
        )
        
        success = organizer.scan_and_organize()
        organizer.print_summary()
        
        if success:
            print(f"\n{Colors.GREEN}✓ Organization completed successfully!{Colors.RESET}")
            return 0
        else:
            print(f"\n{Colors.RED}✗ Organization failed or no files processed.{Colors.RESET}")
            return 1
            
    except KeyboardInterrupt:
        print(f"\n{Colors.YELLOW}Operation cancelled by user.{Colors.RESET}")
        return 1
    except Exception as e:
        print(f"\n{Colors.RED}Fatal error: {e}{Colors.RESET}")
        return 1

if __name__ == '__main__':
    exit(main())