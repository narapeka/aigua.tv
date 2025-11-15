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
    
    def search_tv_show(self, query: str, year: Optional[int] = None, max_pages: int = 3, initial_pages_only: int = 1) -> List[TVShowMetadata]:
        """
        Search for TV shows by name with pagination support
        
        Args:
            query: TV show name to search for
            year: Optional year to filter results
            max_pages: Maximum number of pages to fetch (default: 3, i.e., up to 60 results)
            initial_pages_only: Only fetch this many pages initially (default: 1). Use max_pages to fetch more.
            
        Returns:
            List of TVShowMetadata objects
        """
        try:
            pages_to_fetch = min(initial_pages_only, max_pages)
            self.logger.debug(f"Searching TMDB for TV show: {query}" + (f" (year: {year})" if year else "") + f" (pages: {pages_to_fetch}/{max_pages})")
            
            all_results = []
            original_first_page_size = 0  # Track original page size before filtering
            
            # Fetch pages of results (only initial_pages_only initially)
            for page in range(1, pages_to_fetch + 1):
                # Enforce rate limiting before making the API request
                self._wait_for_rate_limit()
                
                try:
                    # Try to get paginated results
                    # The tmdbv3api library may support page parameter via kwargs
                    raw_page_results = self.tv.search(query, page=page)
                    
                    if not raw_page_results:
                        # No more results, stop pagination
                        if page == 1:
                            self.logger.debug(f"No results found for: {query}")
                            return []
                        break
                    
                    # Track original page size for first page (before filtering)
                    if page == 1:
                        original_first_page_size = len(raw_page_results)
                    
                    # Filter by year if provided
                    if year:
                        page_results = [
                            r for r in raw_page_results
                            if r.get('first_air_date') and 
                            r['first_air_date'].startswith(str(year))
                        ]
                    else:
                        page_results = raw_page_results
                    
                    if not page_results:
                        # No results after year filtering, but might have more pages
                        # Continue to next page if this is first page, otherwise stop
                        if page == 1:
                            continue
                        else:
                            break
                    
                    all_results.extend(page_results)
                    
                    # If we got fewer than 20 results in the original (unfiltered) page, we've reached the last page
                    if len(raw_page_results) < 20:
                        break
                        
                except TypeError:
                    # Library doesn't support page parameter, fall back to single page
                    if page == 1:
                        # Enforce rate limiting before making the API request
                        self._wait_for_rate_limit()
                        raw_results = self.tv.search(query)
                        
                        if not raw_results:
                            self.logger.debug(f"No results found for: {query}")
                            return []
                        
                        # Track original page size for first page (before filtering)
                        original_first_page_size = len(raw_results)
                        
                        # Filter by year if provided
                        if year:
                            results = [
                                r for r in raw_results
                                if r.get('first_air_date') and 
                                r['first_air_date'].startswith(str(year))
                            ]
                        else:
                            results = raw_results
                        
                        all_results = results
                    break
                except Exception as e:
                    self.logger.warning(f"Error fetching page {page} for '{query}': {e}")
                    if page == 1:
                        return []
                    break
            
            # Convert to TVShowMetadata objects
            metadata_list = []
            for result in all_results:
                try:
                    metadata = self._parse_tv_show_result(result)
                    metadata_list.append(metadata)
                except Exception as e:
                    self.logger.warning(f"Failed to parse TV show result: {e}")
                    continue
            
            self.logger.debug(f"Found {len(metadata_list)} results for: {query} (from {len(all_results)} raw results)")
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
        languages: Optional[List[str]] = None,
        max_pages: int = 3,
        initial_pages_only: int = 1
    ) -> Optional[Tuple[List[TVShowMetadata], str]]:
        """
        Search for TV show using multiple languages, returning all results with pagination
        
        Args:
            query: TV show name to search for
            year: Optional year to filter results
            languages: List of languages to try (defaults to self.languages)
            max_pages: Maximum number of pages to fetch per language (default: 3, i.e., up to 60 results)
            initial_pages_only: Only fetch this many pages initially (default: 1). Use max_pages to fetch more.
            
        Returns:
            Tuple of (List[TVShowMetadata], language_used) or None if not found
        """
        if languages is None:
            languages = self.languages
        
        original_language = self.tmdb.language
        
        for lang in languages:
            try:
                self.tmdb.language = lang
                pages_to_fetch = min(initial_pages_only, max_pages)
                self.logger.debug(f"Searching TMDB for '{query}' with language {lang}" + (f" (year: {year})" if year else "") + f" (pages: {pages_to_fetch}/{max_pages})")
                
                all_results = []
                original_first_page_size = 0  # Track original page size before filtering
                
                # Fetch pages of results (only initial_pages_only initially)
                for page in range(1, pages_to_fetch + 1):
                    # Enforce rate limiting before making the API request
                    self._wait_for_rate_limit()
                    
                    try:
                        # Try to get paginated results
                        raw_page_results = self.tv.search(query, page=page)
                        
                        if not raw_page_results:
                            # No more results, stop pagination
                            if page == 1:
                                break
                            break
                        
                        # Track original page size for first page (before filtering)
                        if page == 1:
                            original_first_page_size = len(raw_page_results)
                        
                        # Filter by year if provided
                        if year:
                            page_results = [
                                r for r in raw_page_results
                                if r.get('first_air_date') and 
                                r['first_air_date'].startswith(str(year))
                            ]
                        else:
                            page_results = raw_page_results
                        
                        if not page_results:
                            # No results after year filtering, but might have more pages
                            # Continue to next page if this is first page, otherwise stop
                            if page == 1:
                                continue
                            else:
                                break
                        
                        all_results.extend(page_results)
                        
                        # If we got fewer than 20 results in the original (unfiltered) page, we've reached the last page
                        if len(raw_page_results) < 20:
                            break
                            
                    except TypeError:
                        # Library doesn't support page parameter, fall back to single page
                        if page == 1:
                            # Enforce rate limiting before making the API request
                            self._wait_for_rate_limit()
                            raw_results = self.tv.search(query)
                            
                            if not raw_results:
                                break
                            
                            # Track original page size for first page (before filtering)
                            original_first_page_size = len(raw_results)
                            
                            # Filter by year if provided
                            if year:
                                results = [
                                    r for r in raw_results
                                    if r.get('first_air_date') and 
                                    r['first_air_date'].startswith(str(year))
                                ]
                            else:
                                results = raw_results
                            
                            all_results = results
                        break
                    except Exception as e:
                        self.logger.warning(f"Error fetching page {page} for '{query}' with language {lang}: {e}")
                        if page == 1:
                            break
                        break
                
                if not all_results:
                    continue
                
                # Convert all results to TVShowMetadata
                metadata_list = []
                try:
                    for result in all_results:
                        metadata = self._parse_tv_show_result(result)
                        metadata_list.append(metadata)
                    self.tmdb.language = original_language
                    # Enhanced logging: show original page size vs filtered results
                    if year and original_first_page_size > 0:
                        filtered_count = len(metadata_list)
                        self.logger.debug(
                            f"Found {filtered_count} results for '{query}' using language {lang} "
                            f"(original page 1: {original_first_page_size} results, "
                            f"after year {year} filtering: {filtered_count} results)"
                        )
                    else:
                        self.logger.debug(f"Found {len(metadata_list)} results for '{query}' using language {lang} (from {len(all_results)} raw results)")
                    # Return metadata list, language, and original first page size
                    return (metadata_list, lang, original_first_page_size)
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
        tmdb_info: Dict[str, Any],
        folder_type: Optional[str] = None,
        detected_season: Optional[int] = None
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
            folder_type: Folder type - "direct_files" or "season_subfolders" (optional)
            detected_season: Detected season number (optional)
            
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
        # EXCEPTION: For season > 1 in direct_files, skip year check here (will validate season year later)
        skip_year_check = (folder_type == "direct_files" and detected_season and detected_season > 1)
        
        if skip_year_check:
            self.logger.debug(f"  Skipping year mismatch check (season {detected_season} > 1, will validate season year later)")
        elif input_year and result.year:
            year_diff = abs(input_year - result.year)
            if year_diff == 0:
                self.logger.debug(f"  Year match confirmed: {input_year} == {result.year}")
            elif year_diff == 1:
                # Allow ±1 year tolerance (shows often air across year boundaries)
                self.logger.debug(f"  Year difference of 1 year allowed (LLM year={input_year}, TMDB year={result.year})")
            else:
                # Year difference > 1, downgrade to low confidence
                self.logger.warning(f"  → Confidence: LOW (year mismatch: LLM year={input_year}, TMDB year={result.year}, diff={year_diff})")
                return "low"
        
        # Extract alternative names and check if any match folder_name
        # IMPORTANT: Always validate against folder_name, even for single results
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
                # Remove common punctuation and normalize for better matching
                name_normalized = name_lower.replace('.', ' ').replace('_', ' ').replace('-', ' ')
                folder_normalized = folder_name_lower.replace('.', ' ').replace('_', ' ').replace('-', ' ')
                
                # Check if name appears in folder_name (as whole word or significant substring)
                if name_lower in folder_name_lower or name_normalized in folder_normalized:
                    matching_names.append(name)
                    self.logger.debug(f"  Found matching name: '{name}' in folder_name")
        
        # If no name matches folder_name, it's low confidence (even if year matches)
        if not matching_names:
            self.logger.warning(f"  → Confidence: LOW (no matching names found in folder_name '{folder_name}')")
            self.logger.debug(f"    Checked {len(ret_names)} names against folder_name")
            self.logger.debug(f"    Result name: '{result.name}', Original: '{result.original_name}'")
            if input_name:
                self.logger.debug(f"    Input name: '{input_name}'")
            return "low"
        
        # If single result, name matches folder_name, and year matches (or no year provided), it's high confidence
        if all_results_count == 1:
            self.logger.info(f"  → Confidence: HIGH (single result, name '{matching_names[0]}' found in folder_name, year matches)")
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
        
        # If we have matching names in folder_name and year matches, it's high confidence
        if matching_names:
            self.logger.info(f"  → Confidence: HIGH (found {len(matching_names)} matching names in folder_name, year matches)")
            return "high"
        
        # If we have multiple results but no strong match, return low
        self.logger.warning(f"  → Confidence: LOW (multiple results but no strong match found)")
        self.logger.debug(f"    Checked {len(ret_names)} names against folder_name '{folder_name}'")
        self.logger.debug(f"    Result name: '{result.name}', Original: '{result.original_name}'")
        if input_name:
            self.logger.debug(f"    Input name: '{input_name}'")
        return "low"
    
    def _evaluate_candidate_confidence(
        self,
        candidate: TVShowMetadata,
        folder_name: str,
        input_name: Optional[str],
        input_year: Optional[int],
        all_results_count: int,
        folder_type: Optional[str] = None,
        detected_season: Optional[int] = None
    ) -> Tuple[TVShowMetadata, str]:
        """
        Evaluate confidence for a single candidate by fetching full details and checking confidence
        
        Args:
            candidate: TVShowMetadata candidate to evaluate
            folder_name: Original folder name
            input_name: Input name used for search
            input_year: Input year used for search (from LLM extraction)
            all_results_count: Total number of results from search
            folder_type: Folder type - "direct_files" or "season_subfolders" (optional)
            detected_season: Detected season number (optional)
            
        Returns:
            Tuple of (candidate with full details, confidence_level)
        """
        # Get full details including alternative_titles and translations
        full_details = self._get_full_tv_details(candidate.id)
        if not full_details:
            self.logger.warning(f"Could not fetch full details for candidate ID {candidate.id}")
            return (candidate, "low")
        
        # Extract alternative titles and translations with country codes
        alternative_titles = self._extract_alternative_titles(full_details)
        candidate.alternative_titles = alternative_titles
        
        translations = self._extract_translations(full_details)
        candidate.translations = translations
        
        # Ensure Chinese name if needed
        self._ensure_chinese_name(candidate, full_details)
        
        # Check match confidence
        confidence = self._check_match_confidence(
            candidate, folder_name, input_name, input_year, all_results_count, full_details,
            folder_type=folder_type, detected_season=detected_season
        )
        candidate.match_confidence = confidence
        
        return (candidate, confidence)
    
    def _process_candidates_with_fallback(
        self,
        candidates: List[TVShowMetadata],
        folder_name: str,
        input_name: Optional[str],
        input_year: Optional[int],
        search_language: str,
        folder_type: Optional[str] = None,
        detected_season: Optional[int] = None
    ) -> Optional[Tuple[TVShowMetadata, str]]:
        """
        Process candidates with fallback: check first candidate, if not high confidence, check others
        
        Args:
            candidates: List of candidate TVShowMetadata objects
            folder_name: Original folder name
            input_name: Input name used for search
            input_year: Input year used for search
            search_language: Language used for search
            folder_type: Folder type - "direct_files" or "season_subfolders" (optional)
            detected_season: Detected season number (optional)
            
        Returns:
            Tuple of (best TVShowMetadata, confidence_level) or None if no candidates
        """
        if not candidates:
            return None
        
        all_results_count = len(candidates)
        input_name_for_check = input_name
        
        # Evaluate first candidate
        first_candidate = candidates[0]
        self.logger.info(f"Evaluating first candidate: {first_candidate.name} (ID: {first_candidate.id})")
        evaluated_candidate, confidence = self._evaluate_candidate_confidence(
            first_candidate, folder_name, input_name_for_check, input_year, all_results_count,
            folder_type=folder_type, detected_season=detected_season
        )
        
        # If first candidate has high confidence, return it immediately (fast path)
        if confidence == "high":
            self.logger.info(f"First candidate has high confidence, using it: {evaluated_candidate.name}")
            return (evaluated_candidate, confidence)
        
        # First candidate doesn't have high confidence, check other candidates
        self.logger.info(f"First candidate has {confidence} confidence, checking {len(candidates) - 1} other candidates...")
        best_candidate = evaluated_candidate
        best_confidence = confidence
        
        # Evaluate remaining candidates
        for i, candidate in enumerate(candidates[1:], start=2):
            self.logger.info(f"Evaluating candidate {i}/{len(candidates)}: {candidate.name} (ID: {candidate.id})")
            evaluated_candidate, candidate_confidence = self._evaluate_candidate_confidence(
                candidate, folder_name, input_name_for_check, input_year, all_results_count,
                folder_type=folder_type, detected_season=detected_season
            )
            
            # If we find a high confidence match, use it immediately
            if candidate_confidence == "high":
                self.logger.info(f"Found high confidence match in candidate {i}: {evaluated_candidate.name}")
                return (evaluated_candidate, candidate_confidence)
            
            # Track the best candidate so far (high > medium > low)
            confidence_order = {"high": 3, "medium": 2, "low": 1}
            if confidence_order.get(candidate_confidence, 0) > confidence_order.get(best_confidence, 0):
                best_candidate = evaluated_candidate
                best_confidence = candidate_confidence
                self.logger.debug(f"  Candidate {i} has better confidence ({candidate_confidence}) than previous best ({best_confidence})")
        
        # Return the best candidate found (or first if all have same confidence)
        self.logger.info(f"Using best candidate with {best_confidence} confidence: {best_candidate.name}")
        return (best_candidate, best_confidence)
    
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
    
    def _fetch_season_details(self, tv_id: int, season_number: int, language: str) -> Optional[Dict[str, Any]]:
        """
        Fetch details for a specific season
        
        Args:
            tv_id: TMDB TV show ID
            season_number: Season number to fetch
            language: Language to use
            
        Returns:
            Season details dictionary or None
        """
        original_language = self.tmdb.language
        try:
            self.tmdb.language = language
            self._wait_for_rate_limit()
            season_details = self.season.details(tv_id, season_number)
            return season_details
        except Exception as e:
            self.logger.warning(f"Error fetching season {season_number} details for TV show {tv_id}: {e}")
            return None
        finally:
            self.tmdb.language = original_language
    
    def get_tv_show(
        self,
        folder_name: str,
        cn_name: Optional[str] = None,
        en_name: Optional[str] = None,
        year: Optional[int] = None,
        tmdbid: Optional[int] = None,
        folder_type: Optional[str] = None,
        detected_season: Optional[int] = None
    ) -> Optional[TVShowMetadata]:
        """
        Get TV show information with comprehensive search strategy and confidence checking
        
        Args:
            folder_name: Original folder name
            cn_name: Chinese name (optional)
            en_name: English name (optional)
            year: Release year (optional)
            tmdbid: TMDB ID (optional, if provided, used directly)
            folder_type: Folder type - "direct_files" or "season_subfolders" (optional)
            detected_season: Detected season number from folder/files (optional)
            
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
            # SPECIAL CASE: If folder_type is DIRECT_FILES and detected_season > 1,
            # skip year filter in initial search (year might be season release year, not show first air date)
            use_year_in_search = year
            if folder_type == "direct_files" and detected_season and detected_season > 1:
                self.logger.info(f"  Detected direct files with season {detected_season} > 1, searching without year filter (year {year} may be season release year)")
                use_year_in_search = None
            
            if not result and cn_name:
                self.logger.debug(f"Searching with cn_name: {cn_name}, year: {use_year_in_search}")
                # First try with year (or without if season > 1)
                # Fetch only page 1 initially (efficient - only fetch more if needed)
                search_result = self._search_with_languages(cn_name, use_year_in_search, self.languages, max_pages=3, initial_pages_only=1)
                if search_result:
                    candidates, search_language, original_page_size = search_result
                    # Enhanced logging: show pagination context
                    if use_year_in_search:
                        self.logger.debug(
                            f"Page 1 search results: {len(candidates)} candidates after year filtering "
                            f"(original page 1 had {original_page_size} results)"
                        )
                    else:
                        self.logger.debug(
                            f"Page 1 search results: {len(candidates)} candidates "
                            f"(original page 1 had {original_page_size} results)"
                        )
                    
                    # Process candidates with fallback
                    candidate_result = self._process_candidates_with_fallback(
                        candidates, folder_name, cn_name, year, search_language,
                        folder_type=folder_type, detected_season=detected_season
                    )
                    if candidate_result:
                        result, confidence = candidate_result
                        result.match_confidence = confidence
                        
                        # If no candidate from page 1 had high confidence, fetch more pages and re-evaluate
                        # But only if the original page had 20 results (indicating there might be more pages)
                        if confidence != "high" and original_page_size >= 20:
                            self.logger.info(
                                f"No high confidence match found in page 1 (best was {confidence}). "
                                f"Original page 1 had {original_page_size} results (>=20), so more pages may exist. "
                                f"Fetching additional pages for more candidates..."
                            )
                            # Fetch all pages now (using the same language that worked)
                            full_search_result = self._search_with_languages(cn_name, use_year_in_search, [search_language], max_pages=3, initial_pages_only=3)
                            if full_search_result:
                                all_candidates, _, _ = full_search_result
                                self.logger.debug(
                                    f"Fetched all pages: found {len(all_candidates)} total candidates "
                                    f"(was {len(candidates)} on page 1)"
                                )
                                # Re-process with all candidates
                                candidate_result = self._process_candidates_with_fallback(
                                    all_candidates, folder_name, cn_name, year, search_language,
                                    folder_type=folder_type, detected_season=detected_season
                                )
                                if candidate_result:
                                    result, confidence = candidate_result
                                    result.match_confidence = confidence
                                    all_results_count = len(all_candidates)
                                else:
                                    all_results_count = len(candidates)
                            else:
                                all_results_count = len(candidates)
                        else:
                            all_results_count = len(candidates)
                
                # If no result with year, try without year
                if not result:
                    self.logger.debug(f"No result with year, trying without year")
                    search_result = self._search_with_languages(cn_name, None, self.languages, max_pages=3, initial_pages_only=1)
                    if search_result:
                        candidates, search_language, original_page_size = search_result
                        self.logger.debug(
                            f"Page 1 search results (no year filter): {len(candidates)} candidates "
                            f"(original page 1 had {original_page_size} results)"
                        )
                        # Process candidates with fallback
                        candidate_result = self._process_candidates_with_fallback(
                            candidates, folder_name, cn_name, year, search_language,
                            folder_type=folder_type, detected_season=detected_season
                        )
                        if candidate_result:
                            result, confidence = candidate_result
                            result.match_confidence = confidence
                            
                            # If no candidate from page 1 had high confidence, fetch more pages and re-evaluate
                            # But only if the original page had 20 results (indicating there might be more pages)
                            if confidence != "high" and original_page_size >= 20:
                                self.logger.info(
                                    f"No high confidence match found in page 1 (best was {confidence}). "
                                    f"Original page 1 had {original_page_size} results (>=20), so more pages may exist. "
                                    f"Fetching additional pages for more candidates..."
                                )
                                full_search_result = self._search_with_languages(cn_name, None, [search_language], max_pages=3, initial_pages_only=3)
                                if full_search_result:
                                    all_candidates, _, _ = full_search_result
                                    self.logger.debug(
                                        f"Fetched all pages: found {len(all_candidates)} total candidates "
                                        f"(was {len(candidates)} on page 1)"
                                    )
                                    candidate_result = self._process_candidates_with_fallback(
                                        all_candidates, folder_name, cn_name, year, search_language,
                                        folder_type=folder_type, detected_season=detected_season
                                    )
                                    if candidate_result:
                                        result, confidence = candidate_result
                                        result.match_confidence = confidence
                                        all_results_count = len(all_candidates)
                                    else:
                                        all_results_count = len(candidates)
                                else:
                                    all_results_count = len(candidates)
                            else:
                                all_results_count = len(candidates)
            
            # Strategy 3: If cn_name is None but en_name is provided, search with year
            if not result and en_name:
                self.logger.debug(f"Searching with en_name: {en_name}, year: {use_year_in_search}")
                results = self.search_tv_show(en_name, use_year_in_search, max_pages=3, initial_pages_only=1)
                if results:
                    # Process candidates with fallback
                    candidate_result = self._process_candidates_with_fallback(
                        results, folder_name, en_name, year, self.language,
                        folder_type=folder_type, detected_season=detected_season
                    )
                    if candidate_result:
                        result, confidence = candidate_result
                        result.match_confidence = confidence
                        
                        # If no candidate from page 1 had high confidence, fetch more pages and re-evaluate
                        # But only if we got 20 results (indicating there might be more pages)
                        if confidence != "high" and len(results) >= 20:
                            self.logger.info(
                                f"No high confidence match found in page 1 (best was {confidence}). "
                                f"Page 1 had {len(results)} results (>=20), so more pages may exist. "
                                f"Fetching additional pages for more candidates..."
                            )
                            all_results = self.search_tv_show(en_name, use_year_in_search, max_pages=3, initial_pages_only=3)
                            if all_results:
                                self.logger.debug(
                                    f"Fetched all pages: found {len(all_results)} total candidates "
                                    f"(was {len(results)} on page 1)"
                                )
                                candidate_result = self._process_candidates_with_fallback(
                                    all_results, folder_name, en_name, year, self.language,
                                    folder_type=folder_type, detected_season=detected_season
                                )
                                if candidate_result:
                                    result, confidence = candidate_result
                                    result.match_confidence = confidence
                                    all_results_count = len(all_results)
                                else:
                                    all_results_count = len(results)
                            else:
                                all_results_count = len(results)
                        else:
                            all_results_count = len(results)
                        search_language = self.language
            
            # Strategy 4: If no result, search without year, try multiple languages if name is Chinese
            if not result:
                search_name = cn_name if cn_name else en_name
                if search_name:
                    self.logger.debug(f"Searching without year: {search_name}")
                    if cn_name:
                        # Try multiple languages for Chinese name
                        search_result = self._search_with_languages(search_name, None, self.languages, max_pages=3, initial_pages_only=1)
                        if search_result:
                            candidates, search_language, original_page_size = search_result
                            self.logger.debug(
                                f"Page 1 search results (no year filter): {len(candidates)} candidates "
                                f"(original page 1 had {original_page_size} results)"
                            )
                            # Process candidates with fallback
                            candidate_result = self._process_candidates_with_fallback(
                                candidates, folder_name, cn_name, year, search_language,
                                folder_type=folder_type, detected_season=detected_season
                            )
                            if candidate_result:
                                result, confidence = candidate_result
                                result.match_confidence = confidence
                                
                                # If no candidate from page 1 had high confidence, fetch more pages and re-evaluate
                                # But only if the original page had 20 results (indicating there might be more pages)
                                if confidence != "high" and original_page_size >= 20:
                                    self.logger.info(
                                        f"No high confidence match found in page 1 (best was {confidence}). "
                                        f"Original page 1 had {original_page_size} results (>=20), so more pages may exist. "
                                        f"Fetching additional pages for more candidates..."
                                    )
                                    full_search_result = self._search_with_languages(search_name, None, [search_language], max_pages=3, initial_pages_only=3)
                                    if full_search_result:
                                        all_candidates, _, _ = full_search_result
                                        self.logger.debug(
                                            f"Fetched all pages: found {len(all_candidates)} total candidates "
                                            f"(was {len(candidates)} on page 1)"
                                        )
                                        candidate_result = self._process_candidates_with_fallback(
                                            all_candidates, folder_name, cn_name, year, search_language,
                                            folder_type=folder_type, detected_season=detected_season
                                        )
                                        if candidate_result:
                                            result, confidence = candidate_result
                                            result.match_confidence = confidence
                                            all_results_count = len(all_candidates)
                                        else:
                                            all_results_count = len(candidates)
                                    else:
                                        all_results_count = len(candidates)
                                else:
                                    all_results_count = len(candidates)
                    else:
                        # Use default language for English name
                        results = self.search_tv_show(search_name, None, max_pages=3, initial_pages_only=1)
                        if results:
                            # Process candidates with fallback
                            candidate_result = self._process_candidates_with_fallback(
                                results, folder_name, en_name, year, self.language,
                                folder_type=folder_type, detected_season=detected_season
                            )
                            if candidate_result:
                                result, confidence = candidate_result
                                result.match_confidence = confidence
                                
                                # If no candidate from page 1 had high confidence, fetch more pages and re-evaluate
                                # But only if we got 20 results (indicating there might be more pages)
                                if confidence != "high" and len(results) >= 20:
                                    self.logger.info(
                                        f"No high confidence match found in page 1 (best was {confidence}). "
                                        f"Page 1 had {len(results)} results (>=20), so more pages may exist. "
                                        f"Fetching additional pages for more candidates..."
                                    )
                                    all_results = self.search_tv_show(search_name, None, max_pages=3, initial_pages_only=3)
                                    if all_results:
                                        self.logger.debug(
                                            f"Fetched all pages: found {len(all_results)} total candidates "
                                            f"(was {len(results)} on page 1)"
                                        )
                                    if all_results:
                                        candidate_result = self._process_candidates_with_fallback(
                                            all_results, folder_name, en_name, year, self.language,
                                            folder_type=folder_type, detected_season=detected_season
                                        )
                                        if candidate_result:
                                            result, confidence = candidate_result
                                            result.match_confidence = confidence
                                            all_results_count = len(all_results)
                                        else:
                                            all_results_count = len(results)
                                    else:
                                        all_results_count = len(results)
                                else:
                                    all_results_count = len(results)
                                search_language = self.language
            
            # If no result found, return None
            if not result:
                self.logger.debug(f"No TV show found for folder: {folder_name}")
                return None
            
            # Result already has full details and confidence set from _process_candidates_with_fallback()
            # Get confidence from result
            confidence = result.match_confidence
            self.logger.info(f"Final confidence level: {confidence}")
            
            # SPECIAL VALIDATION: If folder_type is DIRECT_FILES and detected_season > 1,
            # validate that the season's air date year OR show's first air date year matches the LLM-extracted year
            # (folder year could be either season release year or show first air date)
            # Allow ±1 year tolerance for both show year and season year
            if confidence == "high" and folder_type == "direct_files" and detected_season and detected_season > 1 and year:
                self.logger.info(f"  Validating year for season {detected_season} (LLM year: {year})")
                self.logger.debug(f"  Show first air date year: {result.year}")
                
                # Check if show year matches (with ±1 tolerance)
                show_year_diff = abs(result.year - year) if result.year else None
                show_year_matches = (show_year_diff is not None and show_year_diff <= 1)
                if show_year_matches:
                    if show_year_diff == 0:
                        self.logger.info(f"  ✓ Show first air date year ({result.year}) matches LLM year ({year})")
                    else:
                        self.logger.info(f"  ✓ Show first air date year ({result.year}) within ±1 year tolerance of LLM year ({year})")
                else:
                    # If show year doesn't match, check season year (folder year = season release year)
                    self.logger.debug(f"  Show year ({result.year}) doesn't match (diff={show_year_diff}), checking season {detected_season} air date year")
                    season_details = self._fetch_season_details(result.id, detected_season, search_language or self.language)
                    if season_details:
                        season_air_date = season_details.get('air_date')
                        season_year = self._extract_year_from_date(season_air_date)
                        if season_year:
                            self.logger.debug(f"  Season {detected_season} air date: {season_air_date}, year: {season_year}")
                            season_year_diff = abs(season_year - year)
                            if season_year_diff <= 1:
                                if season_year_diff == 0:
                                    self.logger.info(f"  ✓ Season {detected_season} year ({season_year}) matches LLM year ({year})")
                                else:
                                    self.logger.info(f"  ✓ Season {detected_season} year ({season_year}) within ±1 year tolerance of LLM year ({year})")
                            else:
                                # Neither show year nor season year matches (even with tolerance)
                                self.logger.warning(f"  → Confidence downgraded: Neither show year ({result.year}, diff={show_year_diff}) nor season {detected_season} year ({season_year}, diff={season_year_diff}) matches LLM year ({year}) within ±1 tolerance")
                                confidence = "low"
                                result.match_confidence = "low"
                        else:
                            self.logger.warning(f"  Could not extract year from season {detected_season} air date: {season_air_date}")
                            # If we can't get season year, and show year doesn't match, downgrade
                            self.logger.warning(f"  → Confidence downgraded: Show year ({result.year}, diff={show_year_diff}) doesn't match and season year unavailable")
                            confidence = "low"
                            result.match_confidence = "low"
                    else:
                        self.logger.warning(f"  Could not fetch season {detected_season} details for validation")
                        # If we can't get season details, and show year doesn't match, downgrade
                        self.logger.warning(f"  → Confidence downgraded: Show year ({result.year}, diff={show_year_diff}) doesn't match and season details unavailable")
                        confidence = "low"
                        result.match_confidence = "low"
            
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

