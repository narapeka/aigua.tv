#!/usr/bin/env python3
"""
Configuration loader for TV Show Organizer
Loads configuration from config.yaml file.

Author: Kilo Code
"""

import os
import yaml
from pathlib import Path
from typing import Optional, Dict, Any, List
from dataclasses import dataclass


@dataclass
class LLMConfig:
    """LLM agent configuration"""
    api_key: str
    base_url: Optional[str]
    model: str
    batch_size: int
    rate_limit: int = 2
    
    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> 'LLMConfig':
        """Create LLMConfig from dictionary"""
        # Get API key from config or environment
        api_key = data.get('api_key', '')
        if not api_key:
            # Try to get from environment variable
            api_key = os.getenv('OPENAI_API_KEY', '')
        
        # Get base_url, convert empty string to None
        base_url = data.get('base_url')
        if base_url == '' or base_url == 'null':
            base_url = None
        
        # Get rate_limit, convert to int and handle both old and new key names for backward compatibility
        rate_limit = data.get('rate_limit')
        if rate_limit is None:
            # Try old key name for backward compatibility
            rate_limit = data.get('max_requests_per_second', 2)
        if isinstance(rate_limit, float):
            rate_limit = int(rate_limit)
        elif not isinstance(rate_limit, int):
            rate_limit = 2  # Default fallback
        
        return cls(
            api_key=api_key,
            base_url=base_url,
            model=data.get('model', 'gpt-4o-mini'),
            batch_size=data.get('batch_size', 50),
            rate_limit=rate_limit
        )


@dataclass
class ProxyConfig:
    """Proxy configuration"""
    host: str
    port: int
    
    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> Optional['ProxyConfig']:
        """Create ProxyConfig from dictionary"""
        if not data:
            return None
        host = data.get('host')
        port = data.get('port')
        if not host or not port:
            return None
        return cls(host=host, port=port)


@dataclass
class TMDBConfig:
    """TMDB API configuration"""
    api_key: str
    languages: List[str] = None
    rate_limit: int = 40
    
    def __post_init__(self):
        """Set default languages if not provided"""
        if self.languages is None:
            self.languages = ["zh-CN", "zh-SG", "zh-TW", "zh-HK"]
    
    @property
    def language(self) -> str:
        """Get default language from first item in languages array"""
        return self.languages[0] if self.languages else "en-US"
    
    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> 'TMDBConfig':
        """Create TMDBConfig from dictionary"""
        # Get API key from config or environment
        api_key = data.get('api_key', '')
        if not api_key:
            # Try to get from environment variable
            api_key = os.getenv('TMDB_API_KEY', '')
        
        # Get languages array, default to Chinese variants if not provided
        languages = data.get('languages', ["zh-CN", "zh-SG", "zh-TW", "zh-HK"])
        if not isinstance(languages, list):
            languages = ["zh-CN", "zh-SG", "zh-TW", "zh-HK"]
        
        # Get rate_limit, convert to int
        rate_limit = data.get('rate_limit', 40)
        if isinstance(rate_limit, float):
            rate_limit = int(rate_limit)
        elif not isinstance(rate_limit, int):
            rate_limit = 40  # Default fallback
        
        return cls(
            api_key=api_key,
            languages=languages,
            rate_limit=rate_limit
        )


@dataclass
class Config:
    """Complete application configuration"""
    llm: LLMConfig
    tmdb: TMDBConfig
    proxy: Optional[ProxyConfig] = None
    
    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> 'Config':
        """Create Config from dictionary"""
        # Load LLM config
        llm_section = data.get('llm', {})
        if not llm_section:
            raise ValueError(
                "LLM configuration section not found in config.yaml.\n"
                "Please add an 'llm' section with your API settings."
            )
        llm_config = LLMConfig.from_dict(llm_section)
        
        # Validate LLM API key
        if not llm_config.api_key:
            raise ValueError(
                "API key not found in config.yaml or OPENAI_API_KEY environment variable.\n"
                "Please set llm.api_key in config.yaml or set OPENAI_API_KEY environment variable."
            )
        
        # Load TMDB config
        tmdb_section = data.get('tmdb', {})
        if not tmdb_section:
            raise ValueError(
                "TMDB configuration section not found in config.yaml.\n"
                "Please add a 'tmdb' section with your API settings."
            )
        
        tmdb_config = TMDBConfig.from_dict(tmdb_section)
        
        # Validate TMDB API key
        if not tmdb_config.api_key:
            raise ValueError(
                "TMDB API key not found in config.yaml or TMDB_API_KEY environment variable.\n"
                "Please set tmdb.api_key in config.yaml or set TMDB_API_KEY environment variable."
            )
        
        # Load proxy configuration from root level
        proxy_data = data.get('proxy')
        proxy = ProxyConfig.from_dict(proxy_data) if proxy_data else None
        
        return cls(
            llm=llm_config,
            tmdb=tmdb_config,
            proxy=proxy
        )


def load_config(config_path: Optional[str] = None) -> Config:
    """
    Load complete configuration from YAML file
    
    Args:
        config_path: Path to config.yaml file. If None, looks for config.yaml
                     in the current directory or script directory.
    
    Returns:
        Config object with all loaded configurations (LLM, TMDB, etc.)
    
    Raises:
        FileNotFoundError: If config file doesn't exist
        yaml.YAMLError: If config file is invalid YAML
        ValueError: If required configuration is missing
    """
    # Find config file
    if config_path is None:
        # Try current directory first
        current_dir = Path.cwd()
        config_file = current_dir / 'config.yaml'
        
        # If not found, try script directory
        if not config_file.exists():
            script_dir = Path(__file__).parent
            config_file = script_dir / 'config.yaml'
    else:
        config_file = Path(config_path)
    
    if not config_file.exists():
        raise FileNotFoundError(
            f"Configuration file not found: {config_file}\n"
            f"Please create config.yaml with your API settings."
        )
    
    # Load and parse YAML file
    with open(config_file, 'r', encoding='utf-8') as f:
        config_data = yaml.safe_load(f)
    
    if not config_data:
        raise ValueError("Configuration file is empty")
    
    # Convert to Config object
    return Config.from_dict(config_data)

