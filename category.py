#!/usr/bin/env python3
"""
Category Helper for TV Show Organizer
Classifies TV shows into categories based on TMDB metadata (genre_ids, origin_country, etc.)

Author: Kilo Code
"""

import logging
from pathlib import Path
from typing import Optional, Dict, Any, List, Union

import yaml


class CategoryHelper:
    """
    Helper class for categorizing TV shows based on TMDB metadata.
    
    Categories are defined in a YAML configuration file with rules for matching
    genre_ids, origin_country, original_language, and release_year.
    """
    
    def __init__(
        self,
        category_path: Optional[Path] = None,
        logger: Optional[logging.Logger] = None
    ):
        """
        Initialize CategoryHelper
        
        Args:
            category_path: Path to category.yaml file. If None, looks for category.yaml
                          in the script directory.
            logger: Optional logger instance
        """
        self.logger = logger or logging.getLogger(__name__)
        self._categories: Dict[str, Any] = {}
        self._tv_categories: Dict[str, Any] = {}
        
        # Determine category config path
        if category_path is None:
            # Default to category.yaml in script directory
            script_dir = Path(__file__).parent
            self._category_path = script_dir / "category.yaml"
        else:
            self._category_path = Path(category_path)
        
        # Load configuration
        self._load_config()
    
    def _load_config(self) -> None:
        """Load category configuration from YAML file"""
        try:
            if not self._category_path.exists():
                self.logger.debug(f"Category config file not found: {self._category_path}")
                return
            
            with open(self._category_path, 'r', encoding='utf-8') as f:
                self._categories = yaml.safe_load(f) or {}
            
            # Extract TV categories
            self._tv_categories = self._categories.get('tv', {})
            
            if self._tv_categories:
                self.logger.info(f"Loaded {len(self._tv_categories)} TV category rules from {self._category_path}")
            else:
                self.logger.debug("No TV categories defined in config")
                
        except yaml.YAMLError as e:
            self.logger.warning(f"Failed to parse category config: {e}")
            self._categories = {}
            self._tv_categories = {}
        except Exception as e:
            self.logger.warning(f"Failed to load category config: {e}")
            self._categories = {}
            self._tv_categories = {}
    
    @property
    def is_enabled(self) -> bool:
        """Check if category classification is enabled (has TV categories)"""
        return bool(self._tv_categories)
    
    @property
    def tv_category_names(self) -> List[str]:
        """Get list of TV category names"""
        return list(self._tv_categories.keys()) if self._tv_categories else []
    
    def get_tv_category(self, tmdb_metadata: Any) -> Optional[str]:
        """
        Determine the category for a TV show based on TMDB metadata
        
        Args:
            tmdb_metadata: TVShowMetadata object with genre_ids, origin_country, 
                          original_language, and year fields
            
        Returns:
            Category name string, or None if no match or categories not configured
        """
        if not self._tv_categories:
            self.logger.debug("  Category matching disabled: no categories configured")
            return None
        
        if not tmdb_metadata:
            self.logger.debug("  Category matching skipped: no TMDB metadata")
            return None
        
        # Build tmdb_info dict from TVShowMetadata attributes
        tmdb_info = self._metadata_to_dict(tmdb_metadata)
        
        # Log what we're matching against
        show_name = getattr(tmdb_metadata, 'name', 'Unknown')
        self.logger.debug(f"  Determining category for: {show_name}")
        
        return self._get_category(self._tv_categories, tmdb_info)
    
    def _metadata_to_dict(self, metadata: Any) -> Dict[str, Any]:
        """
        Convert TVShowMetadata to dict for category matching
        
        Args:
            metadata: TVShowMetadata object
            
        Returns:
            Dictionary with fields needed for category matching
        """
        return {
            'genre_ids': getattr(metadata, 'genre_ids', None),
            'origin_country': getattr(metadata, 'origin_country', None),
            'original_language': getattr(metadata, 'original_language', None),
            'first_air_date': str(getattr(metadata, 'year', '')) if getattr(metadata, 'year', None) else None,
            'year': getattr(metadata, 'year', None)
        }
    
    def _get_category(self, categories: Dict[str, Any], tmdb_info: Dict[str, Any]) -> Optional[str]:
        """
        Match TMDB info against category rules to determine category
        
        Categories are matched in order - first matching category wins.
        A category with no conditions (None/empty) acts as a fallback.
        
        Args:
            categories: Category rules from config
            tmdb_info: TMDB metadata as dictionary
            
        Returns:
            Category name string, or None if no match
        """
        if not tmdb_info:
            return None
        if not categories:
            return None
        
        # Log metadata for debugging
        self.logger.debug(f"  Category matching - genre_ids: {tmdb_info.get('genre_ids')}, "
                         f"origin_country: {tmdb_info.get('origin_country')}, "
                         f"original_language: {tmdb_info.get('original_language')}, "
                         f"year: {tmdb_info.get('year')}")
        
        # Track fallback category separately (category with no conditions)
        fallback_category = None
        
        # First pass: try to match categories with conditions
        for category_name, conditions in categories.items():
            # Skip categories with no conditions - they're fallbacks
            if not conditions:
                if fallback_category is None:
                    fallback_category = category_name
                continue
            
            # Check all conditions for this category
            match_flag = True
            for attr, value in conditions.items():
                if not value:
                    continue
                
                # Get the corresponding value from TMDB info
                if attr == "release_year":
                    # Special handling for release_year - extract from first_air_date
                    info_value = tmdb_info.get('first_air_date') or tmdb_info.get('year')
                    if info_value:
                        info_value = str(info_value)[:4]
                else:
                    info_value = tmdb_info.get(attr)
                
                if not info_value:
                    self.logger.debug(f"  Category '{category_name}': missing {attr} in metadata")
                    match_flag = False
                    break  # No need to check other conditions if this one fails
                
                # Debug: log the actual type and value
                self.logger.debug(f"  Category '{category_name}': checking {attr} - "
                                f"type: {type(info_value).__name__}, value: {info_value}")
                
                # Convert info_value to list of strings for comparison
                # Handle AsObj type from tmdbv3api library - it's iterable but not a list
                if hasattr(info_value, '__iter__') and not isinstance(info_value, (str, bytes)):
                    # Convert iterable (list, AsObj, tuple, etc.) to list
                    try:
                        info_value = list(info_value)
                    except (TypeError, ValueError):
                        # If conversion fails, treat as single value
                        info_value = [info_value]
                
                if attr == "origin_country":
                    # origin_country should be a list from TMDB (e.g., ['JP', 'US'])
                    if isinstance(info_value, list):
                        info_values = [str(val).upper().strip() for val in info_value if val]
                    elif isinstance(info_value, str):
                        # Handle case where it might be a string (shouldn't happen, but be defensive)
                        # If it's a comma-separated string, split it; otherwise use as single value
                        if ',' in info_value:
                            info_values = [v.upper().strip() for v in info_value.split(',') if v.strip()]
                        else:
                            info_values = [info_value.upper().strip()]
                    else:
                        info_values = [str(info_value).upper().strip()]
                elif isinstance(info_value, list):
                    # genre_ids is a list of integers (e.g., [16, 18])
                    info_values = [str(val).upper().strip() for val in info_value if val is not None]
                else:
                    # Single value (e.g., original_language as string)
                    info_values = [str(info_value).upper().strip()]
                
                # Parse condition value - handle comma separation, ranges, and exclusions
                parsed_values, invert_values = self._parse_condition_value(str(value))
                
                # Check if any value matches (OR logic for multiple values)
                if parsed_values and not set(parsed_values).intersection(set(info_values)):
                    self.logger.debug(f"  Category '{category_name}': {attr} mismatch - "
                                    f"expected any of {parsed_values}, got {info_values}")
                    match_flag = False
                    break
                
                # Check if any excluded value matches (should NOT match)
                if invert_values and set(invert_values).intersection(set(info_values)):
                    self.logger.debug(f"  Category '{category_name}': {attr} excluded - "
                                    f"got excluded value {set(invert_values).intersection(set(info_values))}")
                    match_flag = False
                    break
            
            if match_flag:
                self.logger.debug(f"  Matched category: {category_name}")
                return category_name
        
        # If no category matched, use fallback if available
        if fallback_category:
            self.logger.debug(f"  No category matched, using fallback: {fallback_category}")
            return fallback_category
        
        return None
    
    def _parse_condition_value(self, value: str) -> tuple:
        """
        Parse condition value string into include and exclude lists
        
        Supports:
        - Comma-separated values: "CN,TW,HK"
        - Year ranges: "2010-2020"
        - Exclusions with ! prefix: "!CN" or "!2010-2020"
        
        Args:
            value: Condition value string from config
            
        Returns:
            Tuple of (include_values, exclude_values) as uppercase string lists
        """
        values = []
        invert_values = []
        
        # Split by comma
        parts = [v.strip() for v in value.split(',') if v.strip()]
        
        expanded_values = []
        for part in parts:
            if '-' not in part or part.startswith('!') and '-' not in part[1:]:
                # No range, just add the value
                expanded_values.append(part)
                continue
            
            # Handle range (e.g., "2010-2020" or "!2010-2020")
            prefix = ""
            range_part = part
            if part.startswith('!'):
                prefix = '!'
                range_part = part[1:]
            
            if '-' in range_part:
                range_parts = range_part.split('-', 1)
                if len(range_parts) == 2:
                    start, end = range_parts
                    if start.isdigit() and end.isdigit():
                        # Numeric range - expand
                        for num in range(int(start), int(end) + 1):
                            expanded_values.append(f"{prefix}{num}")
                    else:
                        # Not a numeric range, treat as-is
                        expanded_values.append(part)
                else:
                    expanded_values.append(part)
            else:
                expanded_values.append(part)
        
        # Separate into include and exclude lists
        for val in expanded_values:
            val_upper = val.upper()
            if val_upper.startswith('!'):
                invert_values.append(val_upper[1:])
            else:
                values.append(val_upper)
        
        return values, invert_values

