#!/usr/bin/env python3
"""
TMDB API Client for TV Show Information
Provides access to The Movie Database API for fetching TV show metadata.

Author: Kilo Code
"""

import logging
import re
import time
from typing import Optional, List, Dict, Any, Tuple, Union
from dataclasses import dataclass
from tmdbv3api import TMDb, TV, Season as TMDBSeason, Episode as TMDBEpisode
import requests


@dataclass
class AlternativeTitle:
    """Alternative title with country code"""
    title: str
    iso_3166_1: str  # Country code (e.g., "CN", "US", "GB")


@dataclass
class Translation:
    """Translation with country code"""
    name: str
    iso_3166_1: str  # Country code (e.g., "CN", "US", "GB")


@dataclass
class Episode:
    """Episode information"""
    episode_number: int
    title: str


@dataclass
class Season:
    """Season information with episodes"""
    season_number: int
    episodes: List['Episode']


@dataclass
class TVShowMetadata:
    """TV show metadata from TMDB"""
    id: int
    name: str
    original_name: Optional[str] = None
    folder_name: Optional[str] = None
    cn_name: Optional[str] = None
    en_name: Optional[str] = None
    year: Optional[int] = None
    tmdbid: Optional[int] = None
    alternative_titles: Optional[List[AlternativeTitle]] = None
    translations: Optional[List[Translation]] = None
    seasons: Optional[List[Season]] = None
    match_confidence: Optional[str] = None
    search_language: Optional[str] = None
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary"""
        # Convert alternative_titles and translations to dicts
        alt_titles_dict = None
        if self.alternative_titles:
            alt_titles_dict = [{'title': alt.title, 'iso_3166_1': alt.iso_3166_1} for alt in self.alternative_titles]
        
        translations_dict = None
        if self.translations:
            translations_dict = [{'name': trans.name, 'iso_3166_1': trans.iso_3166_1} for trans in self.translations]
        
        # Convert seasons to dicts
        seasons_dict = None
        if self.seasons:
            seasons_dict = []
            for season in self.seasons:
                episodes_dict = [{'episode_number': ep.episode_number, 'title': ep.title} for ep in season.episodes]
                seasons_dict.append({
                    'season_number': season.season_number,
                    'episodes': episodes_dict
                })
        
        return {
            'id': self.id,
            'name': self.name,
            'original_name': self.original_name,
            'folder_name': self.folder_name,
            'cn_name': self.cn_name,
            'en_name': self.en_name,
            'year': self.year,
            'tmdbid': self.tmdbid,
            'alternative_titles': alt_titles_dict,
            'translations': translations_dict,
            'seasons': seasons_dict,
            'match_confidence': self.match_confidence,
            'search_language': self.search_language
        }


class TMDBClient:
    """Client for interacting with TMDB API"""
    
    def __init__(
        self,
        api_key: str,
        languages: Optional[List[str]] = None,
        proxy_host: Optional[str] = None,
        proxy_port: Optional[int] = None,
        rate_limit: int = 40,
        logger: Optional[logging.Logger] = None
    ):
        """
        Initialize TMDB client
        
        Args:
            api_key: TMDB API key
            languages: List of languages to try when searching (default: ["zh-CN", "zh-SG", "zh-TW", "zh-HK"])
            proxy_host: Proxy host with protocol (e.g., "http://proxy.example.com")
            proxy_port: Proxy port
            rate_limit: Maximum number of requests allowed per second (default: 40)
            logger: Optional logger instance
        """
        self.api_key = api_key
        self.languages = languages or ["zh-CN", "zh-SG", "zh-TW", "zh-HK"]
        # Derive language from first item in languages
        self.language = self.languages[0] if self.languages else "en-US"
        self.rate_limit = rate_limit
        self.min_request_interval = 1.0 / rate_limit  # Minimum seconds between requests
        self.last_request_time = 0.0  # Track last request time for rate limiting
        self.logger = logger or logging.getLogger(__name__)
        
        # Initialize TMDB client
        self.tmdb = TMDb()
        self.tmdb.api_key = self.api_key
        self.tmdb.language = self.language
        
        # Configure proxy if provided
        if proxy_host and proxy_port:
            try:
                # Construct proxy URL
                proxy_url = f"{proxy_host.rstrip('/')}:{proxy_port}"
                
                # Create requests session with proxy
                session = requests.Session()
                proxies = {
                    'http': proxy_url,
                    'https': proxy_url,
                }
                session.proxies.update(proxies)
                
                # Set X-Forwarded-Host header to avoid 403 errors
                session.headers.update({'X-Forwarded-Host': 'api.themoviedb.org'})
                
                # Assign session to tmdb
                self.tmdb.session = session
                
                self.logger.debug(f"Proxy configured: {proxy_url}")
            except Exception as e:
                self.logger.warning(f"Failed to configure proxy: {e}")
        
        # Initialize API objects
        self.tv = TV()
        self.season = TMDBSeason()
        self.episode = TMDBEpisode()
    
    def _wait_for_rate_limit(self):
        """
        Enforce rate limiting by waiting if necessary before making a request.
        Ensures we don't exceed rate_limit requests per second.
        """
        current_time = time.time()
        time_since_last_request = current_time - self.last_request_time
        
        if time_since_last_request < self.min_request_interval:
            wait_time = self.min_request_interval - time_since_last_request
            self.logger.debug(f"Rate limiting: waiting {wait_time:.3f} seconds before next request")
            time.sleep(wait_time)
        
        self.last_request_time = time.time()
    
    def search_tv_show(self, query: str, year: Optional[int] = None) -> List[TVShowMetadata]:
        """
        Search for TV shows by name
        
        Args:
            query: TV show name to search for
            year: Optional year to filter results
            
        Returns:
            List of TVShowMetadata objects
        """
        try:
            self.logger.debug(f"Searching TMDB for TV show: {query}" + (f" (year: {year})" if year else ""))
            
            # Enforce rate limiting before making the API request
            self._wait_for_rate_limit()
            
            results = self.tv.search(query)
            
            if not results:
                self.logger.debug(f"No results found for: {query}")
                return []
            
            # Filter by year if provided
            if year:
                results = [
                    r for r in results
                    if r.get('first_air_date') and 
                    r['first_air_date'].startswith(str(year))
                ]
            
            # Convert to TVShowMetadata objects
            metadata_list = []
            for result in results:
                try:
                    metadata = self._parse_tv_show_result(result)
                    metadata_list.append(metadata)
                except Exception as e:
                    self.logger.warning(f"Failed to parse TV show result: {e}")
                    continue
            
            self.logger.debug(f"Found {len(metadata_list)} results for: {query}")
            return metadata_list
            
        except Exception as e:
            self.logger.error(f"Error searching TMDB for '{query}': {e}")
            return []
    
    def get_tv_show_details(self, tv_id: int) -> Optional[TVShowMetadata]:
        """
        Get detailed information about a TV show by ID
        
        Args:
            tv_id: TMDB TV show ID
            
        Returns:
            TVShowMetadata object or None if not found
        """
        try:
            self.logger.debug(f"Fetching TMDB details for TV show ID: {tv_id}")
            
            # Enforce rate limiting before making the API request
            self._wait_for_rate_limit()
            
            details = self.tv.details(tv_id)
            
            if not details:
                self.logger.debug(f"No details found for TV show ID: {tv_id}")
                return None
            
            metadata = self._parse_tv_show_result(details)
            self.logger.debug(f"Successfully fetched details for TV show ID: {tv_id}")
            return metadata
            
        except Exception as e:
            self.logger.error(f"Error fetching TMDB details for TV show ID {tv_id}: {e}")
            return None
    
    def find_tv_show(self, name: str, year: Optional[int] = None) -> Optional[TVShowMetadata]:
        """
        Find a TV show by name (returns the best match)
        
        Args:
            name: TV show name
            year: Optional year to help narrow down results
            
        Returns:
            TVShowMetadata object for the best match, or None if not found
        """
        results = self.search_tv_show(name, year)
        
        if not results:
            return None
        
        # Return the first result (TMDB typically returns best matches first)
        return results[0]
    
    def _extract_year_from_date(self, date_string: Optional[str]) -> Optional[int]:
        """
        Extract year from date string (YYYY-MM-DD format)
        
        Args:
            date_string: Date string in YYYY-MM-DD format
            
        Returns:
            Year as integer or None
        """
        if not date_string:
            return None
        try:
            return int(date_string[:4])
        except (ValueError, IndexError):
            return None
    
    def is_chinese(self, word: Union[str, list]) -> bool:
        """
        Check if text contains Chinese characters
        
        Args:
            word: String or list of strings to check
            
        Returns:
            True if contains Chinese characters, False otherwise
        """
        if not word:
            return False
        if isinstance(word, list):
            word = " ".join(word)
        chn = re.compile(r'[\u4e00-\u9fff]')
        if chn.search(word):
            return True
        else:
            return False
    
    def _get_chinese_name_from_alternative_titles(self, tmdb_info: Dict[str, Any]) -> Optional[str]:
        """
        Get Chinese name from alternative_titles with iso_3166_1 = 'CN'
        
        Args:
            tmdb_info: Full TMDB API response dictionary
            
        Returns:
            Chinese name if found, None otherwise
        """
        alternative_titles = tmdb_info.get("alternative_titles", {}).get("results", [])
        for alt_title in alternative_titles:
            iso_3166_1 = alt_title.get("iso_3166_1")
            title = alt_title.get("title")
            if iso_3166_1 == "CN" and title:
                self.logger.debug(f"  Found Chinese name from alternative_titles: '{title}' (iso_3166_1=CN)")
                return title
        return None
    
    def _get_chinese_name_from_translations(self, tmdb_info: Dict[str, Any]) -> Optional[str]:
        """
        Get Chinese name from translations with iso_3166_1 = 'CN'
        
        Args:
            tmdb_info: Full TMDB API response dictionary
            
        Returns:
            Chinese name if found, None otherwise
        """
        translations = tmdb_info.get("translations", {}).get("translations", [])
        for translation in translations:
            iso_3166_1 = translation.get("iso_3166_1")
            name = translation.get("data", {}).get("name")
            if iso_3166_1 == "CN" and name:
                self.logger.debug(f"  Found Chinese name from translations: '{name}' (iso_3166_1=CN)")
                return name
        return None
    
    def _ensure_chinese_name(self, result: TVShowMetadata, tmdb_info: Dict[str, Any]) -> None:
        """
        Ensure the result has a Chinese name. If current name is not Chinese,
        try to get Chinese name from alternative_titles or translations.
        
        Args:
            result: TVShowMetadata result to update
            tmdb_info: Full TMDB API response dictionary
        """
        # Check if current name is Chinese
        if self.is_chinese(result.name):
            self.logger.debug(f"  Name '{result.name}' is already Chinese, no need to replace")
            return
        
        self.logger.info(f"  Name '{result.name}' is not Chinese, searching for Chinese name...")
        
        # Try to get Chinese name from alternative_titles first
        chinese_name = self._get_chinese_name_from_alternative_titles(tmdb_info)
        
        # If not found, try translations
        if not chinese_name:
            chinese_name = self._get_chinese_name_from_translations(tmdb_info)
        
        if chinese_name:
            self.logger.info(f"  → Replacing name '{result.name}' with Chinese name '{chinese_name}'")
            result.name = chinese_name
        else:
            self.logger.warning(f"  → No Chinese name found in alternative_titles or translations, keeping original name")
    
    def _extract_alternative_titles(self, tmdb_info: Dict[str, Any]) -> List[AlternativeTitle]:
        """
        Extract all alternative titles with country codes
        
        Args:
            tmdb_info: Full TMDB API response dictionary
            
        Returns:
            List of AlternativeTitle objects
        """
        alt_titles = []
        
        # Extract from alternative_titles
        alternative_titles = tmdb_info.get("alternative_titles", {}).get("results", [])
        self.logger.debug(f"  Extracting from alternative_titles: {len(alternative_titles)} entries found")
        for alt_title in alternative_titles:
            title = alt_title.get("title")
            iso_3166_1 = alt_title.get("iso_3166_1")
            if title and iso_3166_1:
                alt_titles.append(AlternativeTitle(title=title, iso_3166_1=iso_3166_1))
                self.logger.debug(f"    Added alternative title: '{title}' (iso_3166_1={iso_3166_1})")
        
        self.logger.debug(f"  Total alternative titles extracted: {len(alt_titles)}")
        return alt_titles
    
    def _extract_translations(self, tmdb_info: Dict[str, Any]) -> List[Translation]:
        """
        Extract all translations with country codes
        
        Args:
            tmdb_info: Full TMDB API response dictionary
            
        Returns:
            List of Translation objects
        """
        translations = []
        
        # Extract from translations
        translations_data = tmdb_info.get("translations", {}).get("translations", [])
        self.logger.debug(f"  Extracting from translations: {len(translations_data)} entries found")
        for translation in translations_data:
            name = translation.get("data", {}).get("name")
            iso_3166_1 = translation.get("iso_3166_1")
            if name and iso_3166_1:
                translations.append(Translation(name=name, iso_3166_1=iso_3166_1))
                self.logger.debug(f"    Added translation: '{name}' (iso_3166_1={iso_3166_1})")
        
        self.logger.debug(f"  Total translations extracted: {len(translations)}")
        return translations
    
    def _extract_alternative_names(self, tmdb_info: Dict[str, Any]) -> List[str]:
        """
        Extract all alternative names as strings (for backward compatibility in confidence checking)
        
        Args:
            tmdb_info: Full TMDB API response dictionary
            
        Returns:
            List of unique alternative names (strings only, for matching)
        """
        ret_names = []
        
        # Extract from alternative_titles
        alternative_titles = tmdb_info.get("alternative_titles", {}).get("results", [])
        for alternative_title in alternative_titles:
            name = alternative_title.get("title")
            if name and name not in ret_names:
                ret_names.append(name)
        
        # Extract from translations
        translations = tmdb_info.get("translations", {}).get("translations", [])
        for translation in translations:
            name = translation.get("data", {}).get("name")
            if name and name not in ret_names:
                ret_names.append(name)
        
        return ret_names
    
    def _search_with_languages(
        self, 
        query: str, 
        year: Optional[int] = None, 
        languages: Optional[List[str]] = None
    ) -> Optional[Tuple[TVShowMetadata, str]]:
        """
        Search for TV show using multiple languages, stopping at first result
        
        Args:
            query: TV show name to search for
            year: Optional year to filter results
            languages: List of languages to try (defaults to self.languages)
            
        Returns:
            Tuple of (TVShowMetadata, language_used) or None if not found
        """
        if languages is None:
            languages = self.languages
        
        original_language = self.tmdb.language
        
        for lang in languages:
            try:
                self.tmdb.language = lang
                self.logger.debug(f"Searching TMDB for '{query}' with language {lang}" + (f" (year: {year})" if year else ""))
                
                # Enforce rate limiting before making the API request
                self._wait_for_rate_limit()
                
                results = self.tv.search(query)
                
                if not results:
                    continue
                
                # Filter by year if provided
                filtered_results = results
                if year:
                    filtered_results = [
                        r for r in results
                        if r.get('first_air_date') and 
                        r['first_air_date'].startswith(str(year))
                    ]
                
                if not filtered_results:
                    continue
                
                # Convert first result to TVShowMetadata
                try:
                    metadata = self._parse_tv_show_result(filtered_results[0])
                    self.tmdb.language = original_language
                    self.logger.debug(f"Found result for '{query}' using language {lang}")
                    return (metadata, lang)
                except Exception as e:
                    self.logger.warning(f"Failed to parse TV show result: {e}")
                    continue
                    
            except Exception as e:
                self.logger.warning(f"Error searching with language {lang}: {e}")
                continue
        
        # Restore original language
        self.tmdb.language = original_language
        return None
    
    def _get_full_tv_details(self, tv_id: int) -> Optional[Dict[str, Any]]:
        """
        Get full TV show details including alternative_titles and translations
        
        Args:
            tv_id: TMDB TV show ID
            
        Returns:
            Full details dictionary or None if not found
        """
        try:
            # Get basic details
            # Enforce rate limiting before making the API request
            self._wait_for_rate_limit()
            details = self.tv.details(tv_id)
            if not details:
                return None
            
            # Get alternative titles
            try:
                # Enforce rate limiting before making the API request
                self._wait_for_rate_limit()
                alt_titles = self.tv.alternative_titles(tv_id)
                details['alternative_titles'] = alt_titles
            except Exception as e:
                self.logger.debug(f"Could not fetch alternative_titles for {tv_id}: {e}")
                details['alternative_titles'] = {}
            
            # Get translations
            try:
                # Enforce rate limiting before making the API request
                self._wait_for_rate_limit()
                translations = self.tv.translations(tv_id)
                details['translations'] = translations
            except Exception as e:
                self.logger.debug(f"Could not fetch translations for {tv_id}: {e}")
                details['translations'] = {}
            
            return details
            
        except Exception as e:
            self.logger.error(f"Error fetching full details for TV show ID {tv_id}: {e}")
            return None
    
    def _check_match_confidence(
        self,
        result: TVShowMetadata,
        folder_name: str,
        input_name: Optional[str],
        input_year: Optional[int],
        all_results_count: int,
        tmdb_info: Dict[str, Any]
    ) -> str:
        """
        Check match confidence based on various criteria
        
        Args:
            result: TVShowMetadata result
            folder_name: Original folder name
            input_name: Input name used for search
            input_year: Input year used for search (from LLM extraction)
            all_results_count: Total number of results from search
            tmdb_info: Full TMDB info including alternative_titles and translations
            
        Returns:
            Confidence level: "high", "medium", "low", or None
        """
        self.logger.info(f"Checking match confidence for: {result.name} (ID: {result.id})")
        self.logger.debug(f"  Folder name: {folder_name}")
        self.logger.debug(f"  Input name: {input_name}")
        self.logger.debug(f"  Input year (from LLM): {input_year}")
        self.logger.debug(f"  TMDB year: {result.year}")
        self.logger.debug(f"  Total search results: {all_results_count}")
        
        # Check year mismatch first - if years don't match, downgrade to low confidence
        if input_year and result.year:
            if input_year != result.year:
                self.logger.warning(f"  → Confidence: LOW (year mismatch: LLM year={input_year}, TMDB year={result.year})")
                return "low"
            self.logger.debug(f"  Year match confirmed: {input_year} == {result.year}")
        
        # If single result and year matches (or no year provided), it's high confidence
        if all_results_count == 1:
            self.logger.info(f"  → Confidence: HIGH (single result returned, year matches)")
            return "high"
        
        self.logger.debug(f"  Multiple results ({all_results_count}), checking for exact matches...")
        
        # Check exact name and year match
        if input_year and result.year:
            self.logger.debug(f"  Comparing years: input={input_year}, result={result.year}")
            if result.name == input_name and result.year == input_year:
                self.logger.info(f"  → Confidence: HIGH (exact name and year match: '{result.name}' == '{input_name}', {result.year} == {input_year})")
                return "high"
            if result.original_name == input_name and result.year == input_year:
                self.logger.info(f"  → Confidence: HIGH (exact original name and year match: '{result.original_name}' == '{input_name}', {result.year} == {input_year})")
                return "high"
            self.logger.debug(f"  No exact name+year match found")
        else:
            self.logger.debug(f"  Year comparison skipped (input_year={input_year}, result.year={result.year})")
        
        # Extract alternative names and check if any match folder_name
        self.logger.debug(f"  Extracting alternative names from TMDB data...")
        ret_names = self._extract_alternative_names(tmdb_info)
        self.logger.debug(f"  Found {len(ret_names)} alternative names from alternative_titles/translations")
        
        # Also add the main names
        if result.name:
            ret_names.append(result.name)
            self.logger.debug(f"  Added main name: {result.name}")
        if result.original_name:
            ret_names.append(result.original_name)
            self.logger.debug(f"  Added original name: {result.original_name}")
        
        self.logger.debug(f"  Total names to check: {len(ret_names)}")
        
        # Check if any name appears in folder_name (case-insensitive, partial match)
        folder_name_lower = folder_name.lower()
        self.logger.debug(f"  Checking if any name matches folder_name (case-insensitive): '{folder_name_lower}'")
        
        matching_names = []
        for name in ret_names:
            if name:
                name_lower = name.lower()
                if name_lower in folder_name_lower:
                    matching_names.append(name)
                    # Year already checked above, so if we reach here and year matches, it's high confidence
                    self.logger.info(f"  → Confidence: HIGH (name '{name}' found in folder_name '{folder_name}', year matches)")
                    return "high"
        
        if matching_names:
            # Year already checked above, so if we reach here and year matches, it's high confidence
            self.logger.info(f"  → Confidence: HIGH (found {len(matching_names)} matching names in folder_name, year matches)")
            return "high"
        
        # If we have multiple results but no strong match, return low
        self.logger.warning(f"  → Confidence: LOW (multiple results but no strong match found)")
        self.logger.debug(f"    Checked {len(ret_names)} names against folder_name '{folder_name}'")
        self.logger.debug(f"    Result name: '{result.name}', Original: '{result.original_name}'")
        if input_name:
            self.logger.debug(f"    Input name: '{input_name}'")
        return "low"
    
    def _fetch_seasons_and_episodes(self, tv_id: int, language: str) -> List[Season]:
        """
        Fetch all seasons and episodes for a TV show
        
        Args:
            tv_id: TMDB TV show ID
            language: Language to use for fetching season details
            
        Returns:
            List of Season objects with episodes
        """
        seasons_data = []
        original_language = self.tmdb.language
        
        try:
            # Set language for season details
            self.tmdb.language = language
            
            # Get TV show details to know number of seasons
            # Enforce rate limiting before making the API request
            self._wait_for_rate_limit()
            details = self.tv.details(tv_id)
            if not details:
                return []
            
            num_seasons = details.get('number_of_seasons', 0)
            
            for season_num in range(1, num_seasons + 1):
                try:
                    # Enforce rate limiting before making the API request
                    self._wait_for_rate_limit()
                    season_details = self.season.details(tv_id, season_num)
                    if not season_details:
                        continue
                    
                    episodes = []
                    for episode in season_details.get('episodes', []):
                        episodes.append(Episode(
                            episode_number=episode.get('episode_number', 0),
                            title=episode.get('name', '')
                        ))
                    
                    seasons_data.append(Season(
                        season_number=season_num,
                        episodes=episodes
                    ))
                    
                except Exception as e:
                    self.logger.warning(f"Error fetching season {season_num} for TV show {tv_id}: {e}")
                    continue
            
        except Exception as e:
            self.logger.error(f"Error fetching seasons/episodes for TV show {tv_id}: {e}")
        finally:
            # Restore original language
            self.tmdb.language = original_language
        
        return seasons_data
    
    def get_tv_show(
        self,
        folder_name: str,
        cn_name: Optional[str] = None,
        en_name: Optional[str] = None,
        year: Optional[int] = None,
        tmdbid: Optional[int] = None
    ) -> Optional[TVShowMetadata]:
        """
        Get TV show information with comprehensive search strategy and confidence checking
        
        Args:
            folder_name: Original folder name
            cn_name: Chinese name (optional)
            en_name: English name (optional)
            year: Release year (optional)
            tmdbid: TMDB ID (optional, if provided, used directly)
            
        Returns:
            TVShowMetadata with full data if trustable, None otherwise
        """
        result: Optional[TVShowMetadata] = None
        search_language: Optional[str] = None
        all_results_count: int = 0
        
        try:
            # Strategy 1: If tmdbid is provided, use it directly
            if tmdbid:
                self.logger.debug(f"Using provided TMDB ID: {tmdbid}")
                result = self.get_tv_show_details(tmdbid)
                if result:
                    search_language = self.language
                    all_results_count = 1
                    
                    # Get full details to ensure Chinese name
                    full_details = self._get_full_tv_details(result.id)
                    if full_details:
                        # Extract alternative titles and translations with country codes
                        alternative_titles = self._extract_alternative_titles(full_details)
                        result.alternative_titles = alternative_titles
                        
                        translations = self._extract_translations(full_details)
                        result.translations = translations
                        
                        # Ensure Chinese name if needed
                        self._ensure_chinese_name(result, full_details)
                    
                    # TMDB ID is always trustable, set confidence to high
                    result.match_confidence = "high"
                    
                    # Fetch seasons and episodes
                    if search_language:
                        seasons_data = self._fetch_seasons_and_episodes(result.id, search_language)
                        result.seasons = seasons_data
                    
                    # Set all extended fields
                    result.folder_name = folder_name
                    # Don't override cn_name and en_name - they're already handled correctly
                    # Always use year from TMDB result (already extracted from first_air_date)
                    result.year = result.year
                    # Always use TMDB ID from TMDB result
                    result.tmdbid = result.id
                    result.search_language = search_language
                    
                    self.logger.info(f"Successfully retrieved TV show data for: {result.name} (confidence: high, from TMDB ID)")
                    return result
            
            # Strategy 2: If cn_name is provided, search with year, then try multiple languages
            if not result and cn_name:
                self.logger.debug(f"Searching with cn_name: {cn_name}, year: {year}")
                # First try with year
                search_result = self._search_with_languages(cn_name, year, self.languages)
                if search_result:
                    result, search_language = search_result
                    # Count total results for confidence checking
                    original_lang = self.tmdb.language
                    try:
                        self.tmdb.language = search_language
                        # Enforce rate limiting before making the API request
                        self._wait_for_rate_limit()
                        all_results = self.tv.search(cn_name)
                        if year:
                            all_results = [r for r in all_results if r.get('first_air_date') and r['first_air_date'].startswith(str(year))]
                        all_results_count = len(all_results) if all_results else 1
                    except:
                        all_results_count = 1
                    finally:
                        self.tmdb.language = original_lang
                
                # If no result with year, try without year
                if not result:
                    self.logger.debug(f"No result with year, trying without year")
                    search_result = self._search_with_languages(cn_name, None, self.languages)
                    if search_result:
                        result, search_language = search_result
                        # Count total results
                        original_lang = self.tmdb.language
                        try:
                            self.tmdb.language = search_language
                            # Enforce rate limiting before making the API request
                            self._wait_for_rate_limit()
                            all_results = self.tv.search(cn_name)
                            all_results_count = len(all_results) if all_results else 1
                        except:
                            all_results_count = 1
                        finally:
                            self.tmdb.language = original_lang
            
            # Strategy 3: If cn_name is None but en_name is provided, search with year
            if not result and en_name:
                self.logger.debug(f"Searching with en_name: {en_name}, year: {year}")
                results = self.search_tv_show(en_name, year)
                if results:
                    result = results[0]
                    search_language = self.language
                    all_results_count = len(results)
            
            # Strategy 4: If no result, search without year, try multiple languages if name is Chinese
            if not result:
                search_name = cn_name if cn_name else en_name
                if search_name:
                    self.logger.debug(f"Searching without year: {search_name}")
                    if cn_name:
                        # Try multiple languages for Chinese name
                        search_result = self._search_with_languages(search_name, None, self.languages)
                        if search_result:
                            result, search_language = search_result
                            # Count total results
                            original_lang = self.tmdb.language
                            try:
                                self.tmdb.language = search_language
                                # Enforce rate limiting before making the API request
                                self._wait_for_rate_limit()
                                all_results = self.tv.search(search_name)
                                all_results_count = len(all_results) if all_results else 1
                            except:
                                all_results_count = 1
                            finally:
                                self.tmdb.language = original_lang
                    else:
                        # Use default language for English name
                        results = self.search_tv_show(search_name, None)
                        if results:
                            result = results[0]
                            search_language = self.language
                            all_results_count = len(results)
            
            # If no result found, return None
            if not result:
                self.logger.debug(f"No TV show found for folder: {folder_name}")
                return None
            
            # Get full details including alternative_titles and translations
            full_details = self._get_full_tv_details(result.id)
            if not full_details:
                self.logger.warning(f"Could not fetch full details for TV show ID {result.id}")
                return None
            
            # Extract alternative titles and translations with country codes
            alternative_titles = self._extract_alternative_titles(full_details)
            result.alternative_titles = alternative_titles
            
            translations = self._extract_translations(full_details)
            result.translations = translations
            
            # Ensure Chinese name if needed
            self._ensure_chinese_name(result, full_details)
            
            # Check match confidence
            input_name = cn_name if cn_name else en_name
            self.logger.info(f"Evaluating match confidence for result: {result.name} (ID: {result.id})")
            confidence = self._check_match_confidence(
                result, folder_name, input_name, year, all_results_count, full_details
            )
            result.match_confidence = confidence
            self.logger.info(f"Final confidence level: {confidence}")
            
            # Only proceed if confidence is high
            if confidence != "high":
                self.logger.debug(f"Match confidence is {confidence}, not proceeding with season/episode fetch")
                # Still return the result but without seasons/episodes
                result.folder_name = folder_name
                # Don't override cn_name and en_name - they're already handled correctly
                # Always use year from TMDB result (already extracted from first_air_date)
                result.year = result.year
                # Always use TMDB ID from TMDB result
                result.tmdbid = result.id
                result.search_language = search_language
                return result
            
            # Fetch seasons and episodes
            if search_language:
                seasons_data = self._fetch_seasons_and_episodes(result.id, search_language)
                result.seasons = seasons_data
            
            # Set all extended fields
            result.folder_name = folder_name
            # Don't override cn_name and en_name - they're already handled correctly
            # Always use year from TMDB result (already extracted from first_air_date)
            result.year = result.year
            # Always use TMDB ID from TMDB result
            result.tmdbid = result.id
            result.search_language = search_language
            
            self.logger.info(f"Successfully retrieved TV show data for: {result.name} (confidence: {confidence})")
            return result
            
        except Exception as e:
            self.logger.error(f"Error in get_tv_show for folder '{folder_name}': {e}")
            return None
    
    def _parse_tv_show_result(self, result: Dict[str, Any]) -> TVShowMetadata:
        """
        Parse TMDB API result into TVShowMetadata object
        
        Args:
            result: Raw result dictionary from TMDB API
            
        Returns:
            TVShowMetadata object
        """
        # Extract year from first_air_date
        year = self._extract_year_from_date(result.get('first_air_date'))
        
        return TVShowMetadata(
            id=result.get('id', 0),
            name=result.get('name', ''),
            original_name=result.get('original_name'),
            year=year
        )


def create_tmdb_client_from_config(config: Any, logger: Optional[logging.Logger] = None) -> TMDBClient:
    """
    Create TMDBClient instance from Config
    
    Args:
        config: Config instance (with tmdb and proxy at root level)
        logger: Optional logger instance
        
    Returns:
        TMDBClient instance configured with proxy if specified
    """
    tmdb_config = config.tmdb
    proxy_host = None
    proxy_port = None
    if config.proxy:
        proxy_host = config.proxy.host
        proxy_port = config.proxy.port
    
    return TMDBClient(
        api_key=tmdb_config.api_key,
        languages=tmdb_config.languages,
        proxy_host=proxy_host,
        proxy_port=proxy_port,
        rate_limit=tmdb_config.rate_limit,
        logger=logger
    )

