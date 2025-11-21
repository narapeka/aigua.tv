"""Configuration API endpoints"""

from fastapi import APIRouter, HTTPException
from typing import Dict, Any

from config import load_config, save_config, Config, LLMConfig, TMDBConfig, ProxyConfig
from webui.models.schemas import ConfigSchema, LLMConfigSchema, TMDBConfigSchema, ProxyConfigSchema

router = APIRouter(prefix="/api/config", tags=["config"])


@router.get("", response_model=ConfigSchema)
async def get_config():
    """Get current configuration"""
    try:
        config = load_config()
        return ConfigSchema(
            llm=LLMConfigSchema(
                api_key=config.llm.api_key,
                base_url=config.llm.base_url or "",
                model=config.llm.model,
                batch_size=config.llm.batch_size,
                rate_limit=config.llm.rate_limit
            ),
            tmdb=TMDBConfigSchema(
                api_key=config.tmdb.api_key,
                languages=config.tmdb.languages,
                rate_limit=config.tmdb.rate_limit
            ),
            proxy=ProxyConfigSchema(
                host=config.proxy.host,
                port=config.proxy.port
            ) if config.proxy else None
        )
    except ValueError as e:
        # Config validation failed (missing API keys, etc.) - return empty config
        # This allows the UI to still load and let user configure
        import os
        return ConfigSchema(
            llm=LLMConfigSchema(
                api_key=os.getenv('OPENAI_API_KEY', ''),
                base_url="",
                model="",
                batch_size=50,
                rate_limit=2
            ),
            tmdb=TMDBConfigSchema(
                api_key=os.getenv('TMDB_API_KEY', ''),
                languages=["zh-CN", "zh-SG", "zh-TW", "zh-HK"],
                rate_limit=40
            ),
            proxy=None
        )
    except FileNotFoundError as e:
        # Config file doesn't exist - return default config
        import os
        return ConfigSchema(
            llm=LLMConfigSchema(
                api_key=os.getenv('OPENAI_API_KEY', ''),
                base_url="",
                model="",
                batch_size=50,
                rate_limit=2
            ),
            tmdb=TMDBConfigSchema(
                api_key=os.getenv('TMDB_API_KEY', ''),
                languages=["zh-CN", "zh-SG", "zh-TW", "zh-HK"],
                rate_limit=40
            ),
            proxy=None
        )
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to load config: {str(e)}")


@router.put("", response_model=ConfigSchema)
async def update_config(config_data: ConfigSchema):
    """Update configuration"""
    try:
        # Convert schema to Config object
        llm_config = LLMConfig(
            api_key=config_data.llm.api_key,
            base_url=config_data.llm.base_url if config_data.llm.base_url else None,
            model=config_data.llm.model,
            batch_size=config_data.llm.batch_size,
            rate_limit=config_data.llm.rate_limit
        )
        
        tmdb_config = TMDBConfig(
            api_key=config_data.tmdb.api_key,
            languages=config_data.tmdb.languages,
            rate_limit=config_data.tmdb.rate_limit
        )
        
        proxy_config = None
        if config_data.proxy:
            proxy_config = ProxyConfig(
                host=config_data.proxy.host,
                port=config_data.proxy.port
            )
        
        config = Config(
            llm=llm_config,
            tmdb=tmdb_config,
            proxy=proxy_config
        )
        
        # Save configuration
        save_config(config)
        
        # Return updated config
        return ConfigSchema(
            llm=LLMConfigSchema(
                api_key=config.llm.api_key,
                base_url=config.llm.base_url or "",
                model=config.llm.model,
                batch_size=config.llm.batch_size,
                rate_limit=config.llm.rate_limit
            ),
            tmdb=TMDBConfigSchema(
                api_key=config.tmdb.api_key,
                languages=config.tmdb.languages,
                rate_limit=config.tmdb.rate_limit
            ),
            proxy=ProxyConfigSchema(
                host=config.proxy.host,
                port=config.proxy.port
            ) if config.proxy else None
        )
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to save config: {str(e)}")


@router.get("/validate")
async def validate_config():
    """Validate current configuration"""
    try:
        config = load_config()
        errors = []
        
        # Validate LLM config
        if not config.llm.api_key:
            errors.append("LLM API key is required")
        if not config.llm.model:
            errors.append("LLM model is required")
        
        # Validate TMDB config
        if not config.tmdb.api_key:
            errors.append("TMDB API key is required")
        
        return {
            "valid": len(errors) == 0,
            "errors": errors
        }
    except Exception as e:
        return {
            "valid": False,
            "errors": [str(e)]
        }

