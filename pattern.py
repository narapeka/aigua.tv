#!/usr/bin/env python3
"""
Pattern matching and extraction for TV Show Organizer
Provides functions for extracting season/episode numbers and generating filenames.
"""

import re
from typing import Tuple, Optional
from model import Episode
from util import parse_chinese_number


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
    r'[Ee][Pp](\d+)',  # EP01, EP02 format (season-less, must come before [Ee](?:pisode\s*)? pattern)
    r'[Ee](?:pisode\s*)?(\d+)',  # Episode 01, E01, etc. (season-less)
    r'(\d+)-(\d+)',  # 1-09 format (season-episode or episode with dash)
    r'(?:^|\D)(\d{1,3})(?:\D|$)',  # Any 1-3 digit number (fallback, supports episodes > 99)
]

# Metadata patterns to remove from filenames before extracting season/episode numbers
# Format: (pattern, flags, description)
# Flags: 0 = no flags, re.IGNORECASE = case-insensitive
METADATA_PATTERNS = [
    # Episode count patterns (全xx集) - episode count, not season
    (r'全\s*\d+\s*集', 0, 'Episode count pattern'),
    
    # Video resolutions (1080p, 720p, 480p, etc.)
    (r'\b(?:1080|720|576|480|360|240|2160|1440|4320)[pi]?\b', re.IGNORECASE, 'Video resolutions'),
    # 2K/4K/8K resolution - handle cases where K is followed by Chinese characters or other non-alphanumeric
    (r'[248]K(?![a-zA-Z0-9])', re.IGNORECASE, '2K/4K/8K resolution'),
    
    # Video codecs (H264, H265, x264, x265, HEVC, AVC, etc.)
    (r'\b(?:H|X|x)26[45]\b', re.IGNORECASE, 'Video codecs (H264/H265)'),
    (r'\b(?:H\.?26[45]|H\.?266)\b', re.IGNORECASE, 'Video codecs (H.264/H.265/H.266 with dots)'),
    (r'\b(?:HEVC|AVC|VP9|VP8|VC-?1|MPEG-?2|MPEG-?4|AV1|VVC|ProRes|DNxHD|DNxHR|Xvid|DivX)\b', re.IGNORECASE, 'Video codecs (HEVC/AVC/AV1/VVC/ProRes)'),
    
    # Audio track count
    (r'\b\d+Audios?\b', re.IGNORECASE, 'Audio track count (11Audios, 2Audio)'),

    # HDR and Dolby Vision formats
    (r'\b(?:HDR\s*10\+|HDR10\+)\b', re.IGNORECASE, 'HDR formats (HDR10+)'),
    (r'\b(?:HDR\s*10|HDR10)\b', re.IGNORECASE, 'HDR formats (HDR10)'),
    (r'\b(?:Dolby\s*Vision|DV)\b', re.IGNORECASE, 'Dolby Vision (DV)'),
    (r'\bHDR\b', re.IGNORECASE, 'HDR (generic)'),

    # Quality/release type indicators
    (r'\b(?:WEB-DL|WEBRip|UHD|BluRay|BDRip|DVDRip|HDTV|UHDTV|CAM|TS|TC|SCR|DVDScr)\b', re.IGNORECASE, 'Quality indicators'),
    
    # Streaming service abbreviations
    (r'\b(?:NF|DSNP|AMZN|HMAX|HULU|ATVP|DSPY|HBO|MAX)\b', re.IGNORECASE, 'Streaming services'),
    
    # File sizes
    (r'\b\d+\.\d+\s*(?:GB|MB|TB|KB)\b', re.IGNORECASE, 'File sizes'),
    
    # Frame rates
    (r'\b\d+\s*帧\b', 0, 'Frame rates (Chinese)'),
    (r'\b\d+fps\b', re.IGNORECASE, 'Frame rates'),

]


def normalize_metadata(text: str, preserve_years: bool = True) -> str:
    """Remove common metadata patterns from text before extracting season/episode numbers.
    
    This function removes video/audio codecs, resolutions, quality indicators, and other
    metadata that could be mistaken for season/episode numbers.
    
    Args:
        text: Input text (filename or folder name)
        preserve_years: If True, be more careful with years (1900-2099) to avoid removing
                       years that might be part of show names. If False, remove years more aggressively.
    
    Returns:
        Normalized text with metadata removed (replaced with spaces)
    """
    normalized = text
    
    # First, handle audio codecs by removing everything after the codec name
    # Audio codecs typically appear at the end of filenames, followed by channel configs
    # (e.g., AAC2.0, AAC5.1, TrueHD7.1.4, DTS-HDMA5.1, E-AC-3)
    # Remove everything after audio codec until we hit:
    # - Release group markers: -[GROUP], [GROUP], (GROUP)
    # - Quality indicators: Remux, WEB-DL, etc.
    # - File extension: .mkv, .mp4, etc.
    # Pattern matches: codec + optional channel config + everything until delimiter
    # Note: E-AC-3 and E-AC3 are both valid formats for Enhanced AC-3
    audio_codec_with_suffix = r'\b(?:AAC|AC3|DTS(?:-HD(?:MA)?|HD(?:MA)?)?|DDP|E-AC-?3|E-AC3|FLAC|MP3|OGG|VORBIS|OPUS|PCM|TrueHD|DTSX|DTS:X|Atmos)[\s.-]*(?:\d+\.\d+(?:\.\d+)?)?[^\w]*(?=[-\[\(]|(?:Remux|WEB-DL|WEBRip|BluRay|BDRip|DVDRip|HDTV|UHDTV|CAM|TS|TC|SCR|DVDScr|UHD)\b|\.(?:mkv|mp4|avi|mov|wmv|flv|webm|m4v|ts|m2ts|srt|ass|ssa|vtt|sub|idx|sup|pgs)(?:\s|$)|$)'
    normalized = re.sub(audio_codec_with_suffix, ' ', normalized, flags=re.IGNORECASE)
    
    # Apply all metadata patterns from METADATA_PATTERNS
    for pattern, flags, _description in METADATA_PATTERNS:
        normalized = re.sub(pattern, ' ', normalized, flags=flags)
    
    # Handle years (1900-2099) - be careful!
    # Only remove years if they're clearly in metadata context (after codecs, resolutions, etc.)
    # or if preserve_years is False
    if not preserve_years:
        # Remove standalone years that are likely metadata
        normalized = re.sub(r'\b(19|20)\d{2}\b', ' ', normalized)
    else:
        # Only remove years that are clearly metadata (preceded by common separators and metadata)
        # This is more conservative - preserves years that might be part of show names
        metadata_year_pattern = r'(?:WEB-DL|BluRay|1080p|720p|4K|8K|H264|H265|x264|x265|AAC|AC3|DTS)\s+(19|20)\d{2}\b'
        normalized = re.sub(metadata_year_pattern, ' ', normalized, flags=re.IGNORECASE)
    
    # Clean up multiple spaces and trim
    normalized = re.sub(r'\s+', ' ', normalized)
    normalized = normalized.strip()
    
    return normalized


def extract_season_number(text: str, fallback: int = 1, mode: str = 'file') -> int:
    """Extract season number from text using regex patterns including Chinese
    
    Args:
        text: Input text (filename or folder name)
        fallback: Default season number if none found (default: 1)
        mode: 'folder' for folder names, 'file' for episode files (default: 'file')
              When mode='folder', excludes episode count patterns like "xx集" from being detected as season numbers
    """
    # Normalize text first: remove common metadata patterns
    # This prevents metadata like "4K", "H264", "1080p" from being mistaken as season numbers
    text = normalize_metadata(text, preserve_years=True)
    
    # For folder mode, remove episode count patterns (xx集) before extracting season
    # This prevents "78集" (78 episodes) from being detected as season 78
    if mode == 'folder':
        # Remove patterns like "78集", "全78集", "共78集" (episode count, not season)
        text = re.sub(r'(?:全|共|总)?\d+集', ' ', text)
        text = re.sub(r'\s+', ' ', text).strip()
    
    for pattern_idx, pattern in enumerate(SEASON_PATTERNS):
        match = re.search(pattern, text, re.IGNORECASE)
        if match:
            try:
                matched_text = match.group(1)
                # Try Chinese number parsing first
                if re.search(r'[一二三四五六七八九十壹贰叁肆伍陆柒捌玖拾]', matched_text):
                    season_num = parse_chinese_number(matched_text)
                else:
                    season_num = int(matched_text)
                
                # Get match position once
                match_start = match.start()
                match_end = match.end()
                
                # Additional safety checks (most metadata should be removed by normalize_metadata,
                # but keep these as fallback filters for edge cases):
                # - Years (1900-2099) - check if this number is part of a year
                if 1900 <= season_num <= 2099:
                    # Look for 4-digit year pattern around the match
                    year_context = text[max(0, match_start-4):min(len(text), match_end+4)]
                    if re.search(r'\b(19|20)\d{2}\b', year_context):
                        continue
                
                # - For the fallback pattern (last pattern), be extra strict
                # Check if the number appears to be part of a larger number or year
                if pattern_idx == len(SEASON_PATTERNS) - 1:  # Last pattern (fallback)
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


def extract_episode_info(filename: str, position: int = 1) -> Tuple[int, int, Optional[int]]:
    """Extract season and episode numbers from filename including Chinese numerals
    Returns: (season_num, episode_num, end_episode_num) where end_episode_num is None for single episodes
    """
    season_num = 1
    episode_num = position
    end_episode_num = None
    
    # Normalize metadata FIRST to prevent metadata from being mistaken as episode numbers.
    # This must be done BEFORE space normalization to avoid cases like "S02E01 1080p"
    # becoming "S02E011080p" which would be parsed incorrectly.
    # Note: preserve_years=False here because we have special year protection logic below
    normalized_filename = normalize_metadata(filename, preserve_years=False)
    
    # Normalize filename: remove spaces between digits (e.g., "1 8" -> "18")
    # This helps with filenames like "1 8.mp4" which should be episode 18
    # But be careful: don't remove spaces that are between episode patterns and other text
    # Also don't remove spaces before 4-digit years (1900-2099) as they're likely release years
    # Strategy: Protect patterns that should keep spaces, then remove spaces between other digits
    
    protected = []
    counter = 0
    
    # First protect 4-digit years (1900-2099) - these are likely release years
    year_pattern = r'(\d+)\s+((?:19|20)\d{2})\b'
    def replace_year(match):
        nonlocal counter
        marker = f"__PROTECTED_{counter}__"
        protected.append((match.group(0), marker))
        counter += 1
        return marker
    
    normalized_filename = re.sub(year_pattern, replace_year, normalized_filename)
    
    # Then protect episode patterns (E## or S##E##) followed by digits - these are metadata, not part of episode number
    episode_pattern = r'([ES]\d+[ES]?\d+)\s+(\d+)'
    def replace_episode(match):
        nonlocal counter
        marker = f"__PROTECTED_{counter}__"
        protected.append((match.group(0), marker))
        counter += 1
        return marker
    
    normalized_filename = re.sub(episode_pattern, replace_episode, normalized_filename, flags=re.IGNORECASE)
    
    # Now remove spaces between digits in unprotected parts
    normalized_filename = re.sub(r'(\d)\s+(\d)', r'\1\2', normalized_filename)
    
    # Restore protected patterns
    for original, marker in protected:
        normalized_filename = normalized_filename.replace(marker, original)
    
    # First, check for multi-episode patterns like S01E01-S01E02, S01E01E02, etc.
    multi_episode_patterns = [
        # Dash-separated patterns
        (r'[Ss](\d+)[Ee][Pp]?(\d+)\s*-\s*[Ss](\d+)[Ee][Pp]?(\d+)', 's_dash_s'),  # S01E01-S01E02, S01EP01-S01EP02
        (r'[Ss](\d+)[Ee](\d+)\s*-\s*[Ee](\d+)', 's_dash_e'),  # S01E01-E02 (same season)
        (r'(\d+)[xX](\d+)\s*-\s*(\d+)[xX](\d+)', 'x_dash_x'),  # 01x02-01x03 (season x episode format)
        # Concatenated patterns (no dash)
        (r'[Ss](\d+)[Ee][Pp]?(\d+)[Ee][Pp]?(\d+)', 's_concat'),  # S01E01E02, S01EP01EP02
        (r'[Ee][Pp]?(\d+)[Ee][Pp]?(\d+)', 'e_concat'),  # E01E02, EP01EP02 (no season)
    ]
    
    for pattern, pattern_type in multi_episode_patterns:
        match = re.search(pattern, normalized_filename, re.IGNORECASE)
        if match:
            try:
                groups = match.groups()
                if len(groups) == 4:
                    # S01E01-S01E02 or 01x02-01x03 format
                    if pattern_type == 'x_dash_x':
                        # 01x02-01x03 format
                        season1 = int(match.group(1))
                        episode1 = int(match.group(2))
                        season2 = int(match.group(3))
                        episode2 = int(match.group(4))
                        # Only treat as multi-episode if same season
                        if season1 == season2 and episode2 > episode1:
                            season_num = season1
                            episode_num = episode1
                            end_episode_num = episode2
                            return season_num, episode_num, end_episode_num
                    elif pattern_type == 's_dash_s':
                        # S01E01-S01E02 format
                        season1 = int(match.group(1))
                        episode1 = int(match.group(2))
                        season2 = int(match.group(3))
                        episode2 = int(match.group(4))
                        # Only treat as multi-episode if same season
                        if season1 == season2 and episode2 > episode1:
                            season_num = season1
                            episode_num = episode1
                            end_episode_num = episode2
                            return season_num, episode_num, end_episode_num
                elif len(groups) == 3:
                    if pattern_type == 's_dash_e':
                        # S01E01-E02 format
                        season1 = int(match.group(1))
                        episode1 = int(match.group(2))
                        episode2 = int(match.group(3))
                        if episode2 > episode1:
                            season_num = season1
                            episode_num = episode1
                            end_episode_num = episode2
                            return season_num, episode_num, end_episode_num
                    elif pattern_type == 's_concat':
                        # S01E01E02 format: group1=season, group2=ep1, group3=ep2
                        season1 = int(match.group(1))
                        episode1 = int(match.group(2))
                        episode2 = int(match.group(3))
                        if episode2 > episode1:
                            season_num = season1
                            episode_num = episode1
                            end_episode_num = episode2
                            return season_num, episode_num, end_episode_num
                    elif pattern_type == 'e_concat':
                        # E01E02 format (no season, use default season 1)
                        episode1 = int(match.group(1))
                        episode2 = int(match.group(2))
                        if episode2 > episode1:
                            season_num = 1  # Default season
                            episode_num = episode1
                            end_episode_num = episode2
                            return season_num, episode_num, end_episode_num
            except (ValueError, IndexError):
                continue
    
    # Try S##E## format first (season-episode patterns)
    for pattern in EPISODE_PATTERNS[:4]:  # S##EP##, S##E##, S##.E##, ##x##
        match = re.search(pattern, normalized_filename, re.IGNORECASE)
        if match:
            try:
                if len(match.groups()) == 2:
                    season_num = int(match.group(1))
                    episode_num = int(match.group(2))
                    return season_num, episode_num, None
            except (ValueError, IndexError):
                continue
    
    # Try Chinese episode patterns
    for pattern in EPISODE_PATTERNS[4:6]:  # 第六十集, 六十集
        match = re.search(pattern, normalized_filename, re.IGNORECASE)
        if match:
            try:
                matched_text = match.group(1)
                if re.search(r'[一二三四五六七八九十壹贰叁肆伍陆柒捌玖拾]', matched_text):
                    episode_num = parse_chinese_number(matched_text)
                    return season_num, episode_num, None
                elif matched_text.isdigit():
                    episode_num = int(matched_text)
                    return season_num, episode_num, None
            except (ValueError, IndexError):
                continue
    
    # Try explicit episode patterns (English) - EP01 format first
    episode_pattern_ep = EPISODE_PATTERNS[6]  # r'[Ee][Pp](\d+)'
    match = re.search(episode_pattern_ep, normalized_filename, re.IGNORECASE)
    if match:
        try:
            episode_num = int(match.group(1))
            return season_num, episode_num, None
        except (ValueError, IndexError):
            pass
    
    # Try Episode/E01 format
    episode_pattern = EPISODE_PATTERNS[7]  # r'[Ee](?:pisode\s*)?(\d+)'
    match = re.search(episode_pattern, normalized_filename, re.IGNORECASE)
    if match:
        try:
            episode_num = int(match.group(1))
            return season_num, episode_num, None
        except (ValueError, IndexError):
            pass
    
    # Try dash-separated pattern (e.g., 1-09, 10-20)
    # This is typically just episode number with dash separator
    # For cases like "红蜘蛛1-09.mp4", extract episode 9
    dash_pattern = EPISODE_PATTERNS[8]  # r'(\d+)-(\d+)'
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
            return season_num, episode_num, None
        except (ValueError, IndexError):
            pass
    
    # Try numeric fallback pattern, but avoid file extensions
    # Remove file extension before trying numeric patterns
    name_without_ext = normalized_filename.rsplit('.', 1)[0] if '.' in normalized_filename else normalized_filename
    
    # If season number is still default (1), try to extract it from filename first
    # This helps us exclude it from episode number candidates
    # BUT: Only do this if the filename has explicit season patterns (S01, Season 1, etc.)
    # For simple numeric filenames like "01.ts", "10.ts", these are episode-only, not season numbers
    if season_num == 1:
        # Check if filename has explicit season patterns before trying generic extraction
        has_explicit_season = bool(re.search(
            r'[Ss](?:eason\s*)?\d+|第[一二三四五六七八九十壹贰叁肆伍陆柒捌玖拾\d]+季|'
            r'[一二三四五六七八九十壹贰叁肆伍陆柒捌玖拾]+季|\d+\s*单元',
            normalized_filename, re.IGNORECASE
        ))
        if has_explicit_season:
            detected_season = extract_season_number(normalized_filename, fallback=1)
            if 1 <= detected_season <= 100:  # Valid season range
                season_num = detected_season
    
    number_pattern = EPISODE_PATTERNS[9]  # r'(?:^|\D)(\d{1,3})(?:\D|$)' 
    
    # Find all potential matches and filter out false positives
    all_matches = list(re.finditer(number_pattern, name_without_ext, re.IGNORECASE))
    valid_matches = []
    
    for match in all_matches:
        try:
            found_num = int(match.group(1))
            match_start = match.start()
            match_end = match.end()
            
            # Filter out false positives:
            # - Codec numbers (H264, H265, x264, x265, etc.) - check context
            context_after = name_without_ext[match_end:min(len(name_without_ext), match_end+6)].lower()
            context_before = name_without_ext[max(0, match_start-3):match_start].lower()
            # Check wider context for codec patterns
            wider_context = name_without_ext[max(0, match_start-5):min(len(name_without_ext), match_end+10)].lower()
            
            # Check if preceded by H, x, X, or common codec patterns (e.g., H265, x264, [H264])
            is_codec_before = (
                # Direct codec patterns before number: H264, x264, [H264], (H264), .x264, _x264
                context_before in ['h', 'x', '[h', '(h', '.h', '_h', ' h', ' x', '.xh', '.x', '[xh', '(xh'] or
                context_before.endswith('h') or context_before.endswith('x') or context_before.endswith('[h') or
                context_before.endswith('.x') or context_before.endswith(' x') or
                # Check if number is part of codec pattern like .x264, .h265 (where number is 264/265)
                (found_num in [264, 265] and (
                    context_before.endswith('.x') or context_before.endswith('.h') or
                    context_before.endswith(' x') or context_before.endswith(' h') or
                    context_before.endswith('[x') or context_before.endswith('[h') or
                    context_before.endswith('(x') or context_before.endswith('(h')
                ))
            )
            
            # Check if followed by codec patterns (e.g., 01.x264, 01 h265, 01 [h264])
            is_codec_after = (
                # Codec patterns after number: .x264, .h264, .x265, .h265
                re.search(r'^\.(x|h)26[45]', context_after, re.IGNORECASE) or
                # Codec patterns with space:  h264,  h265,  x264,  x265
                re.search(r'^\s+(x|h)26[45]', context_after, re.IGNORECASE) or
                # Codec patterns in brackets: [h264], [x264], [h265], [x265]
                re.search(r'^\s*\[(x|h)26[45]', context_after, re.IGNORECASE) or
                # Codec patterns in parentheses: (h264), (x264), (h265), (x265)
                re.search(r'^\s*\((x|h)26[45]', context_after, re.IGNORECASE) or
                # Short patterns: 264], 265), .x, ]4, ]5
                context_after[:3] in ['4]', '5]', '.x', ']4', ']5'] or
                context_after.startswith(']') or context_after.startswith('.x')
            )
            
            # Check for H264/H265/x264/x265 patterns in wider context
            is_codec_in_context = (
                re.search(r'[hx]26[45]', wider_context, re.IGNORECASE) or
                # Also filter out common codec numbers (264, 265) when they appear in codec-like context
                (found_num in [264, 265] and (
                    'h26' in wider_context or 'x26' in wider_context or 
                    '[h26' in wider_context or '.x26' in wider_context or
                    'h]' in wider_context or 'x]' in wider_context
                ))
            )
            
            is_codec = is_codec_before or is_codec_after or is_codec_in_context
            
            if is_codec:
                continue  # Skip this match (codec number)
            
            # - Video resolutions (1080, 720, 480, etc.) - check if followed by 'p', 'i', or preceded by resolution context
            if (context_after in ['p', 'i'] or 
                '1080' in name_without_ext[max(0, match_start-5):match_start].lower() or 
                '720' in name_without_ext[max(0, match_start-5):match_start].lower() or 
                '480' in name_without_ext[max(0, match_start-5):match_start].lower() or
                found_num in [1080, 720, 480, 360, 240, 2160, 1440]):  # Common video resolutions
                continue  # Skip this match
            
            # - Years (1900-2099) - unlikely in filenames but filter to be safe
            elif 1900 <= found_num <= 2099:
                # Check if it's actually part of a year pattern
                year_context = name_without_ext[max(0, match_start-2):min(len(name_without_ext), match_end+2)]
                if re.search(r'\b(19|20)\d{2}\b', year_context):
                    continue  # Skip this match
                else:
                    # Not a clear year pattern, but still in year range - skip to be safe
                    continue
            
            # - Only use if it seems reasonable (not 0, and reasonable episode range)
            elif 1 <= found_num <= 300:  # Support up to 300 episodes per season
                # Exclude the season number if we already detected it
                # This prevents season numbers from being selected as episode numbers
                if found_num == season_num and season_num != 1:
                    continue  # Skip season number
                valid_matches.append((found_num, match, match_start))
        except (ValueError, IndexError):
            continue
    
    # Prefer numbers that appear later in the filename (more likely to be episode numbers)
    # Also prefer smaller numbers when position is similar
    if valid_matches:
        # Calculate position as percentage of filename length (later = higher percentage)
        filename_len = len(name_without_ext)
        # Sort by: 1) later position in filename (higher percentage), 2) smaller number
        # This ensures numbers at the end (like "07" in "红蜘蛛6欲海沉沦07") are preferred
        valid_matches.sort(key=lambda x: (-x[2] / max(filename_len, 1), x[0]))
        episode_num = valid_matches[0][0]
        return season_num, episode_num, None
    
    # If no patterns worked, use position-based numbering
    return season_num, position, None


def generate_filename(episode: Episode, tmdb_show_name: Optional[str] = None) -> str:
    """
    Generate Emby-compatible filename using TMDB show name and episode titles when available
    
    Args:
        episode: Episode object
        tmdb_show_name: Optional TMDB show name (if None, uses episode.show_name)
    
    Returns:
        Formatted filename: {tmdb_show_name} - S{season:02d}E{episode:02d} - {tmdb_episode_title}.{ext}
        or {tmdb_show_name} - S{season:02d}E{episode:02d}.{ext} if TMDB title not available
    """
    season_str = f"S{episode.season_number:02d}"
    if episode.end_episode_number:
        # Multi-episode file: show range like S01E01-E02
        episode_str = f"E{episode.episode_number:02d}-E{episode.end_episode_number:02d}"
    else:
        episode_str = f"E{episode.episode_number:02d}"
    
    # Use TMDB show name if provided, otherwise fallback to episode.show_name
    show_name = tmdb_show_name if tmdb_show_name else episode.show_name
    
    # Clean show name for filename
    # Convert colon to full-width colon (：), remove other illegal characters
    clean_show_name = show_name.replace(':', '：')
    clean_show_name = re.sub(r'[<>"/\\|?*]', '', clean_show_name)
    
    # Use TMDB episode title if available, otherwise use format without title
    if episode.tmdb_title:
        # Convert colon to full-width colon (：), remove other illegal characters
        clean_episode_title = episode.tmdb_title.replace(':', '：')
        clean_episode_title = re.sub(r'[<>"/\\|?*]', '', clean_episode_title)
        # Format: {tmdb_show_name} - S{season:02d}E{episode:02d} - {tmdb_episode_title}.{ext}
        return f"{clean_show_name} - {season_str}{episode_str} - {clean_episode_title}{episode.extension}"
    else:
        # Format: {tmdb_show_name} - S{season:02d}E{episode:02d}.{ext}
        return f"{clean_show_name} - {season_str}{episode_str}{episode.extension}"

