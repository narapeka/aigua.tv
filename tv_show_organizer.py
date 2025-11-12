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
    
    # Supported video file extensions
    VIDEO_EXTENSIONS = {'.mp4', '.mkv', '.avi', '.mov', '.wmv', '.flv', '.webm', '.m4v', '.ts', '.m2ts'}
    
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
        r'(\d+)',  # Fallback: any number
    ]
    
    EPISODE_PATTERNS = [
        r'[Ss](\d+)[Ee](\d+)',  # S01E01 format
        r'[Ss](\d+)\.?[Ee](\d+)',  # S01.E01 format
        r'(\d+)[xX](\d+)',  # 1x01 format
        r'第([一二三四五六七八九十壹贰叁肆伍陆柒捌玖拾\d]+)集',  # 第六十集, 第1集
        r'([一二三四五六七八九十壹贰叁肆伍陆柒捌玖拾]+)集',  # 六十集
        r'[Ee](?:pisode\s*)?(\d+)',  # Episode 01, E01, etc. (season-less)
        r'(?:^|\D)(\d{1,2})(?:\D|$)',  # Any 1-2 digit number (fallback)
    ]
    
    def __init__(self, input_dir: str, output_dir: str, dry_run: bool = False, verbose: bool = False):
        self.input_dir = Path(input_dir).resolve()
        self.output_dir = Path(output_dir).resolve()
        self.dry_run = dry_run
        self.verbose = verbose
        
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
        
    def _setup_logging(self):
        """Setup colored logging"""
        self.logger = logging.getLogger('TVOrganizer')
        self.logger.setLevel(logging.DEBUG if self.verbose else logging.INFO)
        
        # Clear existing handlers
        self.logger.handlers.clear()
        
        # Console handler
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
        
        formatter = ColoredFormatter('%(levelname)s: %(message)s')
        console_handler.setFormatter(formatter)
        self.logger.addHandler(console_handler)
    
    def is_video_file(self, file_path: Path) -> bool:
        """Check if file is a supported video file"""
        return file_path.suffix.lower() in self.VIDEO_EXTENSIONS
    
    def get_video_files(self, directory: Path) -> List[Path]:
        """Get all video files in a directory"""
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
        for pattern in self.SEASON_PATTERNS:
            match = re.search(pattern, text, re.IGNORECASE)
            if match:
                try:
                    matched_text = match.group(1)
                    # Try Chinese number parsing first
                    if re.search(r'[一二三四五六七八九十壹贰叁肆伍陆柒捌玖拾]', matched_text):
                        return self.parse_chinese_number(matched_text)
                    else:
                        return int(matched_text)
                except (ValueError, IndexError):
                    continue
        return fallback
    
    def extract_episode_info(self, filename: str, position: int = 1) -> Tuple[int, int]:
        """Extract season and episode numbers from filename including Chinese numerals"""
        season_num = 1
        episode_num = position
        
        # Try S##E## format first
        for pattern in self.EPISODE_PATTERNS[:3]:  # S##E##, S##.E##, ##x##
            match = re.search(pattern, filename, re.IGNORECASE)
            if match:
                try:
                    if len(match.groups()) == 2:
                        season_num = int(match.group(1))
                        episode_num = int(match.group(2))
                        return season_num, episode_num
                except (ValueError, IndexError):
                    continue
        
        # Try Chinese episode patterns
        for pattern in self.EPISODE_PATTERNS[3:5]:  # 第六十集, 六十集
            match = re.search(pattern, filename, re.IGNORECASE)
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
        episode_pattern = self.EPISODE_PATTERNS[5]  # r'[Ee](?:pisode\s*)?(\d+)'
        match = re.search(episode_pattern, filename, re.IGNORECASE)
        if match:
            try:
                episode_num = int(match.group(1))
                return season_num, episode_num
            except (ValueError, IndexError):
                pass
        
        # Try numeric fallback pattern, but avoid file extensions
        # Remove file extension before trying numeric patterns
        name_without_ext = filename.rsplit('.', 1)[0] if '.' in filename else filename
        number_pattern = self.EPISODE_PATTERNS[6]  # r'(?:^|\D)(\d{1,2})(?:\D|$)'
        match = re.search(number_pattern, name_without_ext, re.IGNORECASE)
        if match:
            try:
                found_num = int(match.group(1))
                # Only use if it seems reasonable (not 0, and not too high)
                if 1 <= found_num <= 99:
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
        
        # Try to extract season number from first file, fallback to 1
        first_file = video_files[0]
        season_num, _ = self.extract_episode_info(first_file.name)
        
        episodes = []
        for i, video_file in enumerate(video_files, 1):
            # Try to extract episode info, use position as fallback
            detected_season, detected_episode = self.extract_episode_info(video_file.name, i)
            
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
            
            # Check if files have more reliable season information
            file_seasons = []
            for video_file in video_files:
                file_season, _ = self.extract_episode_info(video_file.name)
                if file_season > 1:  # Only consider if we got a meaningful season number
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
            
            for season in tv_show.seasons:
                season_dir = show_output_dir / f"Season {season.season_number}"

                self.logger.info(f"  Organizing Season {season.season_number} -> {Colors.GREEN}{season_dir.relative_to(self.output_dir)}{Colors.RESET}")
                
                # Create season directory
                if not self.dry_run:
                    season_dir.mkdir(parents=True, exist_ok=True)
                
                for episode in season.episodes:
                    new_filename = self.generate_emby_filename(episode)
                    new_path = season_dir / new_filename
                    
                    # Log the operation
                    self.logger.info(f"    {Colors.YELLOW}Moving:{Colors.RESET} {episode.original_path.name}")
                    self.logger.info(f"    {Colors.GREEN}To:{Colors.RESET} {new_path.relative_to(self.output_dir)}")
                    
                    # Move the file
                    if not self.dry_run:
                        try:
                            # Ensure target directory exists
                            new_path.parent.mkdir(parents=True, exist_ok=True)
                            
                            # Move (rename) the file
                            shutil.move(str(episode.original_path), str(new_path))
                            self.stats['episodes_moved'] += 1
                            
                        except Exception as e:
                            self.logger.error(f"Failed to move {episode.original_path}: {e}")
                            self.stats['errors'] += 1
                            return False
                    else:
                        self.stats['episodes_moved'] += 1
                
                self.stats['seasons_processed'] += 1
            
            self.stats['shows_processed'] += 1
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
        
        if self.dry_run:
            self.logger.info(f"\n{Colors.YELLOW}This was a DRY RUN - no files were actually moved.{Colors.RESET}")
            self.logger.info(f"{Colors.YELLOW}Remove --dry-run flag to perform actual organization.{Colors.RESET}")

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
    parser.add_argument('--version', action='version', version='%(prog)s 1.0.0')
    
    args = parser.parse_args()
    
    try:
        organizer = MediaLibraryOrganizer(
            input_dir=args.input_dir,
            output_dir=args.output_dir,
            dry_run=args.dry_run,
            verbose=args.verbose
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