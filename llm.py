#!/usr/bin/env python3
"""
LLM Agent for TV Show Information Extraction
Extracts TV show names (Chinese and English) and year from folder names using LLM models.

Supports multiple LLM providers via OpenAI-compatible API:
- OpenAI GPT models
- Google Gemini (via OpenAI-compatible endpoint)
- Grok (via OpenAI-compatible endpoint)

Author: Kilo Code
"""

import json
import logging
import time
from pathlib import Path
from typing import List, Dict, Optional, Tuple
from dataclasses import dataclass, asdict
from openai import OpenAI


@dataclass
class TVShowInfo:
    """Extracted TV show information from folder name"""
    folder_name: str
    cn_name: Optional[str] = None  # Chinese name
    en_name: Optional[str] = None  # English name
    year: Optional[int] = None  # Release year
    tmdbid: Optional[int] = None  # TMDB ID if present in folder name
    
    def to_dict(self) -> Dict:
        """Convert to dictionary"""
        return asdict(self)


class LLMAgent:
    """LLM agent for extracting TV show information from folder names"""
    
    def __init__(
        self,
        api_key: str,
        base_url: Optional[str] = None,
        model: str = "gpt-4o-mini",
        batch_size: int = 50,
        rate_limit: int = 2,
        logger: Optional[logging.Logger] = None
    ):
        """
        Initialize LLM agent
        
        Args:
            api_key: API key for the LLM service
            base_url: Base URL for the API (None for OpenAI default)
            model: Model name to use (e.g., "gpt-4o-mini", "gpt-4", "gemini-pro", "grok-beta")
            batch_size: Maximum number of folders to process in a single LLM request
            rate_limit: Maximum number of requests allowed per second (default: 2)
            logger: Optional logger instance
        """
        self.api_key = api_key
        self.base_url = base_url
        self.model = model
        self.batch_size = batch_size
        self.rate_limit = rate_limit
        self.min_request_interval = 1.0 / rate_limit  # Minimum seconds between requests
        self.last_request_time = 0.0  # Track last request time for rate limiting
        self.logger = logger or logging.getLogger(__name__)
        
        # Initialize OpenAI client (works with OpenAI-compatible APIs)
        client_kwargs = {"api_key": self.api_key}
        if self.base_url:
            client_kwargs["base_url"] = self.base_url
        
        self.client = OpenAI(**client_kwargs)
        
        # Load prompts from external files
        prompts_dir = Path(__file__).parent / "prompts"
        system_prompt_path = prompts_dir / "system_prompt.txt"
        user_prompt_path = prompts_dir / "user_prompt.txt"
        
        # Load system prompt
        if system_prompt_path.exists():
            with open(system_prompt_path, 'r', encoding='utf-8') as f:
                self.system_prompt = f.read().strip()
        else:
            raise FileNotFoundError(
                f"System prompt file not found: {system_prompt_path}\n"
                f"Please create prompts/system_prompt.txt"
            )
        
        # Load user prompt template
        if user_prompt_path.exists():
            with open(user_prompt_path, 'r', encoding='utf-8') as f:
                self.user_prompt_template = f.read().strip()
        else:
            raise FileNotFoundError(
                f"User prompt file not found: {user_prompt_path}\n"
                f"Please create prompts/user_prompt.txt"
            )
    
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
    
    def _create_extraction_prompt(self, folder_names: List[str]) -> str:
        """Create prompt for extracting TV show information"""
        folder_list = json.dumps(folder_names, ensure_ascii=False, indent=2)
        return self.user_prompt_template.format(folder_list=folder_list)
    
    def _parse_llm_response(self, response_text: str, folder_names: List[str]) -> List[TVShowInfo]:
        """
        Parse LLM response and return list of TVShowInfo
        
        Args:
            response_text: Raw response text from LLM
            folder_names: Original list of folder names for validation
            
        Returns:
            List of TVShowInfo objects
        """
        results = []
        
        try:
            # Try to extract JSON from response (handle cases where LLM adds extra text)
            response_text = response_text.strip()
            
            # Find JSON array in the response
            start_idx = response_text.find('[')
            end_idx = response_text.rfind(']') + 1
            
            if start_idx == -1 or end_idx == 0:
                raise ValueError("No JSON array found in response")
            
            json_text = response_text[start_idx:end_idx]
            parsed_data = json.loads(json_text)
            
            # Validate and convert to TVShowInfo objects
            folder_name_map = {name: None for name in folder_names}
            
            for item in parsed_data:
                if not isinstance(item, dict):
                    continue
                
                folder_name = item.get('folder_name', '')
                if folder_name not in folder_name_map:
                    # Try to match by index if folder_name doesn't match exactly
                    continue
                
                # Extract fields
                cn_name = item.get('cn_name') or item.get('zh_name')  # Support both for backward compatibility
                en_name = item.get('en_name')
                year = item.get('year')
                tmdbid = item.get('tmdbid')
                
                # Convert year to int if it's a string
                if isinstance(year, str):
                    try:
                        year = int(year)
                    except ValueError:
                        year = None
                
                # Convert tmdbid to int if it's a string
                if isinstance(tmdbid, str):
                    try:
                        tmdbid = int(tmdbid)
                    except ValueError:
                        tmdbid = None
                elif tmdbid is not None and not isinstance(tmdbid, int):
                    tmdbid = None
                
                # Convert empty strings to None
                cn_name = cn_name if cn_name and cn_name.strip() else None
                en_name = en_name if en_name and en_name.strip() else None
                
                results.append(TVShowInfo(
                    folder_name=folder_name,
                    cn_name=cn_name,
                    en_name=en_name,
                    year=year,
                    tmdbid=tmdbid
                ))
                folder_name_map[folder_name] = True
            
            # Add missing folders with None values
            for folder_name, processed in folder_name_map.items():
                if processed is None:
                    results.append(TVShowInfo(folder_name=folder_name))
            
        except json.JSONDecodeError as e:
            self.logger.error(f"Failed to parse JSON response: {e}")
            self.logger.debug(f"Response text: {response_text}")
            # Return empty results for all folders
            results = [TVShowInfo(folder_name=name) for name in folder_names]
        
        except Exception as e:
            self.logger.error(f"Error parsing LLM response: {e}")
            results = [TVShowInfo(folder_name=name) for name in folder_names]
        
        return results
    
    def extract_tvshow(self, folder_names: List[str]) -> List[TVShowInfo]:
        """
        Extract TV show information from folder names
        
        Can process a single folder (list with one item) or multiple folders.
        Automatically splits the input into chunks of batch_size
        to balance network cost, token limits, and processing speed.
        
        Args:
            folder_names: List of folder names to extract information from
                          (can be a single-item list for one folder)
            
        Returns:
            List of TVShowInfo objects, one for each input folder name
        """
        if not folder_names:
            return []
        
        self.logger.info(f"Extracting info for {len(folder_names)} folders using model: {self.model}")
        
        all_results = []
        
        # Split into chunks of batch_size
        for i in range(0, len(folder_names), self.batch_size):
            chunk = folder_names[i:i + self.batch_size]
            chunk_num = (i // self.batch_size) + 1
            total_chunks = (len(folder_names) + self.batch_size - 1) // self.batch_size
            
            self.logger.debug(f"Processing chunk {chunk_num}/{total_chunks} ({len(chunk)} folders)")
            
            try:
                # Enforce rate limiting before making the API request
                self._wait_for_rate_limit()
                
                # Create the user prompt
                user_prompt = self._create_extraction_prompt(chunk)
                
                # Log LLM input in verbose mode
                self.logger.debug("=" * 80)
                self.logger.debug(f"LLM Request for chunk {chunk_num}/{total_chunks}:")
                self.logger.debug(f"  Model: {self.model}")
                self.logger.debug(f"  System Prompt ({len(self.system_prompt)} chars):")
                self.logger.debug(f"    {self.system_prompt[:200]}..." if len(self.system_prompt) > 200 else f"    {self.system_prompt}")
                self.logger.debug(f"  User Prompt ({len(user_prompt)} chars):")
                self.logger.debug(f"    {user_prompt}")
                self.logger.debug(f"  Folder names in chunk: {chunk}")
                
                response = self.client.chat.completions.create(
                    model=self.model,
                    messages=[
                        {"role": "system", "content": self.system_prompt},
                        {"role": "user", "content": user_prompt}
                    ],
                    temperature=0.1  # Low temperature for consistent extraction
                )
                
                response_text = response.choices[0].message.content
                
                # Log LLM output in verbose mode
                self.logger.debug(f"  LLM Response ({len(response_text)} chars):")
                self.logger.debug(f"    {response_text}")
                self.logger.debug("=" * 80)
                
                chunk_results = self._parse_llm_response(response_text, chunk)
                all_results.extend(chunk_results)
                
                self.logger.debug(f"Successfully processed chunk {chunk_num}/{total_chunks}")
            
            except Exception as e:
                self.logger.error(f"Error processing chunk {chunk_num}/{total_chunks}: {e}")
                # Add empty results for failed chunk
                all_results.extend([TVShowInfo(folder_name=name) for name in chunk])
        
        # Ensure we have results for all input folders (in case of parsing issues)
        if len(all_results) != len(folder_names):
            self.logger.warning(f"Result count mismatch: expected {len(folder_names)}, got {len(all_results)}")
            # Create a map of existing results
            result_map = {r.folder_name: r for r in all_results}
            # Fill in missing results
            all_results = [
                result_map.get(name, TVShowInfo(folder_name=name))
                for name in folder_names
            ]
        
        self.logger.info(f"Successfully extracted info for {len(all_results)} folders")
        return all_results

