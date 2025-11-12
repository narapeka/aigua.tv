#!/usr/bin/env python3
"""
TV Show Media Library Organizer
Reorganizes TV show media files following Emby naming conventions.

Supports two folder structure cases:
1. Direct files in show folder (represents single season)
2. Season subfolders containing episode files

Author: Kilo Code
"""

import os
import re
import shutil
import argparse
import logging
from pathlib import Path
from typing import List, Dict, Tuple, Optional, NamedTuple
from dataclasses import dataclass
from enum import Enum
import json
from datetime import datetime

# ANSI color codes for terminal output
class Colors:
    RESET = '\033[0m'
    BOLD = '\033[1m'
    RED = '\033[91m'
    GREEN = '\033[92m'
    YELLOW = '\033[93m'
    BLUE = '\033[94m'
    MAGENTA = '\033[95m'
    CYAN = '\033[96m'
    WHITE = '\033[97m'

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
    
    def __post_init__(self):
        if not self.extension:
            self.extension = self.original_path.suffix
        if not self.title:
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

class MediaLibraryOrganizer:
    """Main class for organizing TV show media library"""
    
    # Supported media file extensions (video + subtitles)
    # Subtitle files are included so they go through the same episode/season detection logic
    MEDIA_EXTENSIONS = {
        # Video formats
        '.mp4', '.mkv', '.avi', '.mov', '.wmv', '.flv', '.webm', '.m4v', '.ts', '.m2ts',
        # Subtitle formats
        '.srt', '.ass', '.ssa', '.vtt', '.sub', '.idx', '.sup', '.pgs'
    }
    
    # Chinese numeral mappings
    CHINESE_NUMERALS = {
        '零': 0, '一': 1, '二': 2, '三': 3, '四': 4, '五': 5,
        '六': 6, '七': 7, '八': 8, '九': 9, '十': 10,
        '壹': 1, '贰': 2, '叁': 3, '肆': 4, '伍': 5,  # Traditional
        '陆': 6, '柒': 7, '捌': 8, '玖': 9, '拾': 10
    }
    
    # Regex patterns for extracting information
    SEASON_PATTERNS = [
        r'[Ss](?:eason\s*)?(\d+)',  # Season 1, season 1, S1, etc.
        r'第([一二三四五六七八九十壹贰叁肆伍陆柒捌玖拾\d]+)季',  # 第三季, 第1季
        r'([一二三四五六七八九十壹贰叁肆伍陆柒捌玖拾]+)季',  # 三季
        r'(\d+)\s*单元',  # 01单元, 1单元 (unit number - indicates season)
        # Strict fallback: match standalone numbers (1-100) that aren't years or codec numbers
        # Matches numbers at word boundaries, not part of larger numbers
        r'(?:^|[^\d])([1-9]\d?)(?![0-9])(?:[^\d]|$)',  # Standalone 1-99 (not part of 100+)
    ]
    
    EPISODE_PATTERNS = [
        r'[Ss](\d+)[Ee][Pp](\d+)',  # S01EP02, S01Ep02 format
        r'[Ss](\d+)[Ee](\d+)',  # S01E01 format
        r'[Ss](\d+)\.?[Ee](\d+)',  # S01.E01 format
        r'(\d+)[xX](\d+)',  # 1x01 format
        r'第([一二三四五六七八九十壹贰叁肆伍陆柒捌玖拾\d]+)集',  # 第六十集, 第1集
        r'([一二三四五六七八九十壹贰叁肆伍陆柒捌玖拾]+)集',  # 六十集
        r'[Ee](?:pisode\s*)?(\d+)',  # Episode 01, E01, etc. (season-less)
        r'(\d+)-(\d+)',  # 1-09 format (season-episode or episode with dash)
        r'(?:^|\D)(\d{1,3})(?:\D|$)',  # Any 1-3 digit number (fallback, supports episodes > 99)
    ]
    
    def __init__(self, input_dir: str, output_dir: str, dry_run: bool = False, verbose: bool = False, log_dir: Optional[str] = None):
        self.input_dir = Path(input_dir).resolve()
        self.output_dir = Path(output_dir).resolve()
        self.dry_run = dry_run
        self.verbose = verbose
        
        # Setup log directory
        if log_dir:
            self.log_dir = Path(log_dir).resolve()
        else:
            self.log_dir = self.output_dir / "logs"
        self.log_dir.mkdir(parents=True, exist_ok=True)
        
        # Generate log file names with timestamp
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        self.log_file = self.log_dir / f"tv_organizer_{timestamp}.log"
        self.report_file = self.log_dir / f"tv_organizer_report_{timestamp}.html"
        
        # Execution tracking
        self.start_time = datetime.now()
        self.processed_shows = []  # Store details of processed shows
        
        # Setup logging
        self._setup_logging()
        
        # Statistics
        self.stats = {
            'shows_processed': 0,
            'seasons_processed': 0,
            'episodes_moved': 0,
            'errors': 0
        }
        
        self.logger.info(f"{Colors.CYAN}TV Show Media Library Organizer{Colors.RESET}")
        self.logger.info(f"Input Directory: {Colors.YELLOW}{self.input_dir}{Colors.RESET}")
        self.logger.info(f"Output Directory: {Colors.YELLOW}{self.output_dir}{Colors.RESET}")
        self.logger.info(f"Mode: {Colors.MAGENTA}{'DRY RUN' if dry_run else 'LIVE'}{Colors.RESET}")
        self.logger.info(f"Log File: {Colors.CYAN}{self.log_file}{Colors.RESET}")
        
    def _setup_logging(self):
        """Setup colored logging with file handler"""
        self.logger = logging.getLogger('TVOrganizer')
        self.logger.setLevel(logging.DEBUG if self.verbose else logging.INFO)
        
        # Clear existing handlers
        self.logger.handlers.clear()
        
        # Console handler with colored output
        console_handler = logging.StreamHandler()
        console_handler.setLevel(logging.DEBUG if self.verbose else logging.INFO)
        
        # Custom formatter for colored output
        class ColoredFormatter(logging.Formatter):
            COLORS = {
                'DEBUG': Colors.BLUE,
                'INFO': Colors.GREEN,
                'WARNING': Colors.YELLOW,
                'ERROR': Colors.RED,
                'CRITICAL': Colors.RED + Colors.BOLD
            }
            
            def format(self, record):
                color = self.COLORS.get(record.levelname, Colors.RESET)
                record.levelname = f"{color}{record.levelname}{Colors.RESET}"
                return super().format(record)
        
        console_formatter = ColoredFormatter('%(levelname)s: %(message)s')
        console_handler.setFormatter(console_formatter)
        self.logger.addHandler(console_handler)
        
        # File handler with detailed formatting (no ANSI colors)
        file_handler = logging.FileHandler(self.log_file, encoding='utf-8')
        file_handler.setLevel(logging.DEBUG)
        
        file_formatter = logging.Formatter(
            '%(asctime)s | %(levelname)-8s | %(message)s',
            datefmt='%Y-%m-%d %H:%M:%S'
        )
        file_handler.setFormatter(file_formatter)
        self.logger.addHandler(file_handler)
    
    def is_video_file(self, file_path: Path) -> bool:
        """Check if file is a supported media file (video or subtitle)"""
        return file_path.suffix.lower() in self.MEDIA_EXTENSIONS
    
    def get_video_files(self, directory: Path) -> List[Path]:
        """Get all media files (video + subtitles) in a directory"""
        if not directory.exists() or not directory.is_dir():
            return []
        
        video_files = []
        for file_path in directory.iterdir():
            if file_path.is_file() and self.is_video_file(file_path):
                video_files.append(file_path)
        
        return sorted(video_files, key=lambda x: x.name.lower())
    
    def normalize_show_name(self, name: str) -> str:
        """Normalize TV show name for consistent formatting"""
        # Remove special characters and normalize spacing
        name = re.sub(r'[^\w\s\-\.\(\)\u4e00-\u9fff]', '', name)  # Include Chinese characters
        name = re.sub(r'\s+', ' ', name)
        return name.strip()
    
    def parse_chinese_number(self, chinese_text: str) -> int:
        """Convert Chinese numerals to Arabic numbers"""
        if not chinese_text:
            return 0
        
        # Handle pure Arabic numbers
        if chinese_text.isdigit():
            return int(chinese_text)
        
        # Handle mixed Chinese-Arabic (like "第1集")
        arabic_match = re.search(r'\d+', chinese_text)
        if arabic_match:
            return int(arabic_match.group())
        
        result = 0
        temp = 0
        
        for char in chinese_text:
            if char in self.CHINESE_NUMERALS:
                num = self.CHINESE_NUMERALS[char]
                if num == 10:  # 十
                    if temp == 0:
                        temp = 10  # 十 = 10
                    else:
                        temp *= 10  # 二十 = 2 * 10
                elif num == 0:  # 零
                    continue
                else:
                    if temp == 10 or temp == 0:
                        temp += num  # 十五 = 10 + 5, or just 五 = 5
                    else:
                        result += temp
                        temp = num
        
        result += temp
        return result if result > 0 else temp
    
    def extract_season_number(self, text: str, fallback: int = 1) -> int:
        """Extract season number from text using regex patterns including Chinese"""
        for pattern_idx, pattern in enumerate(self.SEASON_PATTERNS):
            match = re.search(pattern, text, re.IGNORECASE)
            if match:
                try:
                    matched_text = match.group(1)
                    # Try Chinese number parsing first
                    if re.search(r'[一二三四五六七八九十壹贰叁肆伍陆柒捌玖拾]', matched_text):
                        season_num = self.parse_chinese_number(matched_text)
                    else:
                        season_num = int(matched_text)
                    
                    # Get match position once
                    match_start = match.start()
                    match_end = match.end()
                    
                    # Filter out false positives:
                    # - "全xx集" pattern (全21集, 全12集, etc.) - this indicates episode count, not season
                    # Check if the number is within "全...集" context
                    # Look for "全" before the match and "集" after the match within reasonable distance
                    text_before_match = text[:match_start]
                    text_after_match = text[match_end:]
                    # Check if "全" appears before (within 10 chars) and "集" appears after (within 10 chars)
                    if '全' in text_before_match[-10:] and '集' in text_after_match[:10]:
                        # Verify this is actually a "全xx集" pattern by checking the context
                        pattern_context = text[max(0, match_start-15):min(len(text), match_end+15)]
                        # Match pattern like "全21集", "全 12 集", "全12集" etc.
                        if re.search(r'全\s*' + re.escape(matched_text) + r'\s*集', pattern_context):
                            continue
                    
                    # - Years (1900-2099) - check if this number is part of a year
                    if 1900 <= season_num <= 2099:
                        # Look for 4-digit year pattern around the match
                        year_context = text[max(0, match_start-4):min(len(text), match_end+4)]
                        if re.search(r'\b(19|20)\d{2}\b', year_context):
                            continue
                    
                    # - Codec numbers (H264, H265, x264, x265, etc.) - check context
                    # If the number is preceded by H, x, X, or followed by codec-related text, skip it
                    context_before_upper = text[max(0, match_start-2):match_start].upper()
                    context_after_upper = text[match_end:min(len(text), match_end+2)].upper()
                    if (context_before_upper in ['H', 'X', '[H', '(H', '.H', '_H'] or 
                        context_after_upper in ['4', '5', '6', '8'] or
                        re.search(r'[HXx]26[45]', text, re.IGNORECASE)):
                        continue
                    
                    # - For the fallback pattern (last pattern), be extra strict
                    # Check if the number appears to be part of a larger number or year
                    if pattern_idx == len(self.SEASON_PATTERNS) - 1:  # Last pattern (fallback)
                        # Check if surrounded by digits (part of larger number)
                        if match_start > 0 and text[match_start-1].isdigit():
                            continue
                        if match_end < len(text) and text[match_end].isdigit():
                            continue
                        # Check if it's the last digit of a 4-digit year (e.g., "7" in "2007")
                        if match_start >= 3:
                            year_candidate = text[match_start-3:match_end]
                            if year_candidate.isdigit() and 1900 <= int(year_candidate) <= 2099:
                                continue
                    
                    # - Unreasonably high season numbers (> 100)
                    if season_num > 100:
                        continue
                    
                    return season_num
                except (ValueError, IndexError):
                    continue
        return fallback
    
    def extract_episode_info(self, filename: str, position: int = 1) -> Tuple[int, int]:
        """Extract season and episode numbers from filename including Chinese numerals"""
        season_num = 1
        episode_num = position
        
        # Normalize filename: remove spaces between digits (e.g., "1 8" -> "18")
        # This helps with filenames like "1 8.mp4" which should be episode 18
        normalized_filename = re.sub(r'(\d)\s+(\d)', r'\1\2', filename)
        
        # Try S##E## format first (season-episode patterns)
        for pattern in self.EPISODE_PATTERNS[:4]:  # S##EP##, S##E##, S##.E##, ##x##
            match = re.search(pattern, normalized_filename, re.IGNORECASE)
            if match:
                try:
                    if len(match.groups()) == 2:
                        season_num = int(match.group(1))
                        episode_num = int(match.group(2))
                        return season_num, episode_num
                except (ValueError, IndexError):
                    continue
        
        # Try Chinese episode patterns
        for pattern in self.EPISODE_PATTERNS[4:6]:  # 第六十集, 六十集
            match = re.search(pattern, normalized_filename, re.IGNORECASE)
            if match:
                try:
                    matched_text = match.group(1)
                    if re.search(r'[一二三四五六七八九十壹贰叁肆伍陆柒捌玖拾]', matched_text):
                        episode_num = self.parse_chinese_number(matched_text)
                        return season_num, episode_num
                    elif matched_text.isdigit():
                        episode_num = int(matched_text)
                        return season_num, episode_num
                except (ValueError, IndexError):
                    continue
        
        # Try explicit episode patterns (English)
        episode_pattern = self.EPISODE_PATTERNS[6]  # r'[Ee](?:pisode\s*)?(\d+)'
        match = re.search(episode_pattern, normalized_filename, re.IGNORECASE)
        if match:
            try:
                episode_num = int(match.group(1))
                return season_num, episode_num
            except (ValueError, IndexError):
                pass
        
        # Try dash-separated pattern (e.g., 1-09, 10-20)
        # This is typically just episode number with dash separator
        # For cases like "红蜘蛛1-09.mp4", extract episode 9
        dash_pattern = self.EPISODE_PATTERNS[7]  # r'(\d+)-(\d+)'
        match = re.search(dash_pattern, normalized_filename, re.IGNORECASE)
        if match:
            try:
                first_num = int(match.group(1))
                second_num = int(match.group(2))
                # Check if there's a season indicator before the dash (e.g., "S1-09")
                match_start = match.start()
                context_before = normalized_filename[max(0, match_start-2):match_start].upper()
                # If preceded by 'S' or 'SEASON', treat as season-episode
                if 'S' in context_before or 'SEASON' in normalized_filename[max(0, match_start-10):match_start].upper():
                    if 1 <= first_num <= 100:  # Reasonable season number
                        season_num = first_num
                        episode_num = second_num
                    else:
                        episode_num = second_num
                else:
                    # No season indicator, treat as episode only (e.g., "1-09" = episode 9)
                    episode_num = second_num
                return season_num, episode_num
            except (ValueError, IndexError):
                pass
        
        # Try numeric fallback pattern, but avoid file extensions
        # Remove file extension before trying numeric patterns
        name_without_ext = normalized_filename.rsplit('.', 1)[0] if '.' in normalized_filename else normalized_filename
        number_pattern = self.EPISODE_PATTERNS[8]  # r'(?:^|\D)(\d{1,3})(?:\D|$)' 
        match = re.search(number_pattern, name_without_ext, re.IGNORECASE)
        if match:
            try:
                found_num = int(match.group(1))
                match_start = match.start()
                match_end = match.end()
                
                # Filter out false positives:
                # - Video resolutions (1080, 720, 480, etc.) - check if followed by 'p', 'i', or preceded by resolution context
                context_after = name_without_ext[match_end:min(len(name_without_ext), match_end+2)].lower()
                context_before = name_without_ext[max(0, match_start-5):match_start].lower()
                if (context_after in ['p', 'i'] or 
                    '1080' in context_before or '720' in context_before or '480' in context_before or
                    found_num in [1080, 720, 480, 360, 240, 2160, 1440]):  # Common video resolutions
                    pass  # Skip this match
                # - Years (1900-2099) - unlikely in filenames but filter to be safe
                elif 1900 <= found_num <= 2099:
                    # Check if it's actually part of a year pattern
                    year_context = name_without_ext[max(0, match_start-2):min(len(name_without_ext), match_end+2)]
                    if re.search(r'\b(19|20)\d{2}\b', year_context):
                        pass  # Skip this match
                    else:
                        # Not a clear year pattern, but still in year range - skip to be safe
                        pass
                # - Only use if it seems reasonable (not 0, and reasonable episode range)
                elif 1 <= found_num <= 300:  # Support up to 300 episodes per season
                    episode_num = found_num
                    return season_num, episode_num
            except (ValueError, IndexError):
                pass
        
        # If no patterns worked, use position-based numbering
        return season_num, position
    
    def determine_folder_type(self, folder_path: Path) -> FolderType:
        """Determine if folder contains direct files or season subfolders"""
        if not folder_path.exists() or not folder_path.is_dir():
            return FolderType.DIRECT_FILES
        
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
        detected_season, _ = self.extract_episode_info(first_file.name)
        
        # Only use detected season if it's reasonable (1-100), otherwise default to 1
        # This prevents false matches from codec names (H265), years (2001), etc.
        if 1 <= detected_season <= 100:
            season_num = detected_season
        else:
            season_num = 1
            self.logger.debug(f"  Detected season {detected_season} seems invalid, defaulting to Season 1")
        
        episodes = []
        for i, video_file in enumerate(video_files, 1):
            # Try to extract episode info, use position as fallback
            detected_season, detected_episode = self.extract_episode_info(video_file.name, i)
            
            # Validate detected season - only use if reasonable
            if not (1 <= detected_season <= 100):
                detected_season = season_num
            
            # Use detected season if consistent, otherwise use first file's season
            final_season = detected_season if detected_season == season_num else season_num
            final_episode = detected_episode if detected_episode != i else i
            
            episode = Episode(
                original_path=video_file,
                show_name=show_name,
                season_number=final_season,
                episode_number=final_episode,
                extension=video_file.suffix
            )
            episodes.append(episode)
            
            self.logger.debug(f"  Episode: {video_file.name} -> S{final_season:02d}E{final_episode:02d}")
        
        season = Season(
            show_name=show_name,
            season_number=season_num,
            episodes=episodes,
            original_folder=folder_path
        )
        
        return TVShow(
            name=show_name,
            seasons=[season],
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
            folder_season = self.extract_season_number(subdir.name, None)
            
            # Validate folder_season - filter out unreasonable values
            if folder_season and not (1 <= folder_season <= 100):
                self.logger.debug(f"    Ignoring invalid season {folder_season} from folder name")
                folder_season = None
            
            # Check if files have more reliable season information
            file_seasons = []
            for video_file in video_files:
                file_season, _ = self.extract_episode_info(video_file.name)
                # Only consider reasonable season numbers (1-100)
                if 1 < file_season <= 100:  # > 1 to avoid default season 1
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
                file_season, episode_num = self.extract_episode_info(video_file.name, i)
                
                # Use the determined season number, not the one from individual files
                final_season = season_num
                
                episode = Episode(
                    original_path=video_file,
                    show_name=show_name,
                    season_number=final_season,
                    episode_number=episode_num,
                    extension=video_file.suffix
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
    
    def generate_emby_filename(self, episode: Episode) -> str:
        """Generate Emby-compatible filename"""
        season_str = f"S{episode.season_number:02d}"
        episode_str = f"E{episode.episode_number:02d}"
        
        # Clean show name for filename
        clean_show_name = re.sub(r'[<>:"/\\|?*]', '', episode.show_name)
        
        return f"{clean_show_name} - {season_str}{episode_str} - {episode.title}{episode.extension}"
    
    def organize_show(self, tv_show: TVShow) -> bool:
        """Organize a TV show into Emby format"""
        try:
            show_output_dir = self.output_dir / tv_show.name
            show_details = {
                'name': tv_show.name,
                'folder_type': tv_show.folder_type.value,
                'original_folder': str(tv_show.original_folder),
                'seasons': []
            }
            
            for season in tv_show.seasons:
                season_dir = show_output_dir / f"Season {season.season_number}"

                self.logger.info(f"  Organizing Season {season.season_number} -> {Colors.GREEN}{season_dir.relative_to(self.output_dir)}{Colors.RESET}")
                
                season_details = {
                    'season_number': season.season_number,
                    'episodes': []
                }
                
                # Create season directory
                if not self.dry_run:
                    season_dir.mkdir(parents=True, exist_ok=True)
                
                for episode in season.episodes:
                    new_filename = self.generate_emby_filename(episode)
                    new_path = season_dir / new_filename
                    
                    # Log the operation
                    self.logger.info(f"    {Colors.YELLOW}Moving:{Colors.RESET} {episode.original_path.name}")
                    self.logger.info(f"    {Colors.GREEN}To:{Colors.RESET} {new_path.relative_to(self.output_dir)}")
                    
                    episode_details = {
                        'episode_number': episode.episode_number,
                        'original_file': episode.original_path.name,
                        'original_path': str(episode.original_path),
                        'new_file': new_filename,
                        'new_path': str(new_path.relative_to(self.output_dir)),
                        'status': 'pending'
                    }
                    
                    # Move the file
                    if not self.dry_run:
                        try:
                            # Ensure target directory exists
                            new_path.parent.mkdir(parents=True, exist_ok=True)
                            
                            # Move (rename) the file
                            shutil.move(str(episode.original_path), str(new_path))
                            self.stats['episodes_moved'] += 1
                            episode_details['status'] = 'moved'
                            
                        except Exception as e:
                            self.logger.error(f"Failed to move {episode.original_path}: {e}")
                            self.stats['errors'] += 1
                            episode_details['status'] = 'error'
                            episode_details['error'] = str(e)
                            return False
                    else:
                        self.stats['episodes_moved'] += 1
                        episode_details['status'] = 'dry_run'
                    
                    season_details['episodes'].append(episode_details)
                
                show_details['seasons'].append(season_details)
                self.stats['seasons_processed'] += 1
            
            self.stats['shows_processed'] += 1
            self.processed_shows.append(show_details)
            return True
            
        except Exception as e:
            self.logger.error(f"Failed to organize show {tv_show.name}: {e}")
            self.stats['errors'] += 1
            return False
    
    def scan_and_organize(self) -> bool:
        """Main method to scan input directory and organize all shows"""
        if not self.input_dir.exists():
            self.logger.error(f"Input directory does not exist: {self.input_dir}")
            return False
        
        if not self.input_dir.is_dir():
            self.logger.error(f"Input path is not a directory: {self.input_dir}")
            return False
        
        # Create output directory if it doesn't exist
        if not self.dry_run:
            self.output_dir.mkdir(parents=True, exist_ok=True)
        
        self.logger.info(f"\n{Colors.BOLD}Scanning input directory...{Colors.RESET}")
        
        # Get all subdirectories (potential TV shows)
        show_folders = [d for d in self.input_dir.iterdir() if d.is_dir()]
        
        if not show_folders:
            self.logger.warning("No subdirectories found in input directory")
            return False
        
        self.logger.info(f"Found {len(show_folders)} potential TV show folders")
        
        success_count = 0
        for show_folder in sorted(show_folders, key=lambda x: x.name.lower()):
            self.logger.info(f"\n{Colors.BOLD}Processing: {show_folder.name}{Colors.RESET}")
            
            # Determine folder structure type
            folder_type = self.determine_folder_type(show_folder)
            
            # Process based on folder type
            if folder_type == FolderType.DIRECT_FILES:
                tv_show = self.process_direct_files_folder(show_folder)
            else:
                tv_show = self.process_season_subfolders(show_folder)
            
            if tv_show:
                if self.organize_show(tv_show):
                    success_count += 1
                    self.logger.info(f"{Colors.GREEN}✓ Successfully processed: {tv_show.name}{Colors.RESET}")
                else:
                    self.logger.error(f"{Colors.RED}✗ Failed to process: {show_folder.name}{Colors.RESET}")
            else:
                self.logger.warning(f"{Colors.YELLOW}⚠ Skipped: {show_folder.name} (no valid media files found){Colors.RESET}")
        
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
        
        if self.dry_run:
            self.logger.info(f"\n{Colors.YELLOW}This was a DRY RUN - no files were actually moved.{Colors.RESET}")
            self.logger.info(f"{Colors.YELLOW}Remove --dry-run flag to perform actual organization.{Colors.RESET}")
        
        # Generate HTML report
        self.generate_html_report(duration)
        self.logger.info(f"\n{Colors.CYAN}Report saved to: {self.report_file}{Colors.RESET}")
    
    def generate_html_report(self, duration):
        """Generate a pretty HTML report of the execution"""
        html_content = f"""<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>TV Show Organizer Report</title>
    <style>
        * {{
            margin: 0;
            padding: 0;
            box-sizing: border-box;
        }}
        body {{
            font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, 'Helvetica Neue', Arial, sans-serif;
            line-height: 1.6;
            color: #e0e0e0;
            background: #121212;
            padding: 20px;
        }}
        .container {{
            max-width: 1200px;
            margin: 0 auto;
            background: #1e1e1e;
            border-radius: 8px;
            box-shadow: 0 2px 20px rgba(0,0,0,0.5);
            padding: 30px;
        }}
        h1 {{
            color: #ffffff;
            border-bottom: 3px solid #5dade2;
            padding-bottom: 10px;
            margin-bottom: 30px;
        }}
        h2 {{
            color: #b0b0b0;
            margin-top: 30px;
            margin-bottom: 15px;
            border-left: 4px solid #5dade2;
            padding-left: 15px;
        }}
        .summary-grid {{
            display: grid;
            grid-template-columns: repeat(auto-fit, minmax(200px, 1fr));
            gap: 20px;
            margin: 20px 0;
        }}
        .summary-card {{
            background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
            color: white;
            padding: 20px;
            border-radius: 8px;
            text-align: center;
            box-shadow: 0 4px 15px rgba(102, 126, 234, 0.3);
        }}
        .summary-card.error {{
            background: linear-gradient(135deg, #e74c3c 0%, #c0392b 100%);
            box-shadow: 0 4px 15px rgba(231, 76, 60, 0.3);
        }}
        .summary-card.success {{
            background: linear-gradient(135deg, #3498db 0%, #2980b9 100%);
            box-shadow: 0 4px 15px rgba(52, 152, 219, 0.3);
        }}
        .summary-card h3 {{
            font-size: 14px;
            opacity: 0.9;
            margin-bottom: 10px;
            text-transform: uppercase;
            letter-spacing: 1px;
        }}
        .summary-card .value {{
            font-size: 36px;
            font-weight: bold;
        }}
        .info-section {{
            background: #2a2a2a;
            padding: 15px;
            border-radius: 5px;
            margin: 15px 0;
            border: 1px solid #3a3a3a;
        }}
        .info-section p {{
            margin: 5px 0;
            color: #d0d0d0;
        }}
        .info-section strong {{
            color: #ffffff;
        }}
        .info-section code {{
            background: #1a1a1a;
            color: #5dade2;
            padding: 2px 6px;
            border-radius: 3px;
            font-size: 0.9em;
        }}
        .show-card {{
            border: 1px solid #3a3a3a;
            border-radius: 5px;
            margin: 20px 0;
            overflow: hidden;
            background: #252525;
        }}
        .show-header {{
            background: linear-gradient(135deg, #3498db 0%, #2980b9 100%);
            color: white;
            padding: 15px;
            font-weight: bold;
            font-size: 18px;
        }}
        .show-body {{
            padding: 15px;
            background: #252525;
            color: #e0e0e0;
        }}
        .show-body code {{
            background: #1a1a1a;
            color: #5dade2;
            padding: 2px 6px;
            border-radius: 3px;
            font-size: 0.9em;
        }}
        .season-section {{
            margin: 15px 0;
            padding: 10px;
            background: #2a2a2a;
            border-radius: 5px;
            border: 1px solid #3a3a3a;
        }}
        .season-title {{
            font-weight: bold;
            color: #ffffff;
            margin-bottom: 10px;
        }}
        .episode-list {{
            list-style: none;
            margin-left: 20px;
        }}
        .episode-item {{
            padding: 8px;
            margin: 5px 0;
            background: #1e1e1e;
            border-left: 3px solid #5dade2;
            border-radius: 3px;
            color: #e0e0e0;
        }}
        .episode-item.error {{
            border-left-color: #e74c3c;
            background: #2a1a1a;
        }}
        .episode-item.dry-run {{
            border-left-color: #f39c12;
            background: #2a241a;
        }}
        .file-path {{
            font-family: 'Courier New', monospace;
            font-size: 12px;
            color: #888;
            margin-top: 5px;
        }}
        .status-badge {{
            display: inline-block;
            padding: 3px 8px;
            border-radius: 3px;
            font-size: 11px;
            font-weight: bold;
            margin-left: 10px;
        }}
        .status-moved {{
            background: #27ae60;
            color: #ffffff;
        }}
        .status-error {{
            background: #e74c3c;
            color: #ffffff;
        }}
        .status-dry-run {{
            background: #f39c12;
            color: #ffffff;
        }}
        .footer {{
            margin-top: 40px;
            padding-top: 20px;
            border-top: 2px solid #3a3a3a;
            text-align: center;
            color: #888;
            font-size: 14px;
        }}
        .footer code {{
            background: #1a1a1a;
            color: #5dade2;
            padding: 2px 6px;
            border-radius: 3px;
            font-size: 0.9em;
        }}
    </style>
</head>
<body>
    <div class="container">
        <h1>📺 TV Show Organizer Execution Report</h1>
        
        <div class="summary-grid">
            <div class="summary-card success">
                <h3>Shows Processed</h3>
                <div class="value">{self.stats['shows_processed']}</div>
            </div>
            <div class="summary-card success">
                <h3>Seasons Processed</h3>
                <div class="value">{self.stats['seasons_processed']}</div>
            </div>
            <div class="summary-card success">
                <h3>Episodes Moved</h3>
                <div class="value">{self.stats['episodes_moved']}</div>
            </div>
            <div class="summary-card {'error' if self.stats['errors'] > 0 else 'success'}">
                <h3>Errors</h3>
                <div class="value">{self.stats['errors']}</div>
            </div>
        </div>
        
        <h2>Execution Information</h2>
        <div class="info-section">
            <p><strong>Start Time:</strong> {self.start_time.strftime('%Y-%m-%d %H:%M:%S')}</p>
            <p><strong>End Time:</strong> {self.end_time.strftime('%Y-%m-%d %H:%M:%S')}</p>
            <p><strong>Duration:</strong> {str(duration).split('.')[0]}</p>
            <p><strong>Mode:</strong> {'<span style="color: #f39c12; font-weight: bold;">DRY RUN</span>' if self.dry_run else '<span style="color: #27ae60; font-weight: bold;">LIVE</span>'}</p>
            <p><strong>Input Directory:</strong> <code>{self.input_dir}</code></p>
            <p><strong>Output Directory:</strong> <code>{self.output_dir}</code></p>
            <p><strong>Log File:</strong> <code>{self.log_file}</code></p>
        </div>
        
        <h2>Processed Shows</h2>
"""
        
        if self.processed_shows:
            for show in self.processed_shows:
                html_content += f"""
        <div class="show-card">
            <div class="show-header">
                {show['name']} <span style="font-size: 12px; opacity: 0.9;">({show['folder_type']})</span>
            </div>
            <div class="show-body">
                <p><strong>Original Folder:</strong> <code>{show['original_folder']}</code></p>
"""
                for season in show['seasons']:
                    html_content += f"""
                <div class="season-section">
                    <div class="season-title">Season {season['season_number']:02d} ({len(season['episodes'])} episodes)</div>
                    <ul class="episode-list">
"""
                    for episode in season['episodes']:
                        status_class = episode['status']
                        status_text = episode['status'].replace('_', ' ').title()
                        html_content += f"""
                        <li class="episode-item {status_class}">
                            <strong>{episode['new_file']}</strong>
                            <span class="status-badge status-{episode['status']}">{status_text}</span>
                            <div class="file-path">From: {episode['original_file']}</div>
                            <div class="file-path">To: {episode['new_path']}</div>
"""
                        if episode.get('error'):
                            html_content += f"""
                            <div class="file-path" style="color: #ff6b6b;">Error: {episode['error']}</div>
"""
                        html_content += """
                        </li>
"""
                    html_content += """
                    </ul>
                </div>
"""
                html_content += """
            </div>
        </div>
"""
        else:
            html_content += """
        <p style="color: #888; font-style: italic;">No shows were processed.</p>
"""
        
        html_content += f"""
        <div class="footer">
            <p>Generated by TV Show Organizer on {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}</p>
            <p>Report saved to: <code>{self.report_file}</code></p>
        </div>
    </div>
</body>
</html>
"""
        
        try:
            with open(self.report_file, 'w', encoding='utf-8') as f:
                f.write(html_content)
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
    parser.add_argument('--log-dir', help='Directory to save log files (default: output_dir/logs)')
    parser.add_argument('--version', action='version', version='%(prog)s 1.0.0')
    
    args = parser.parse_args()
    
    try:
        organizer = MediaLibraryOrganizer(
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