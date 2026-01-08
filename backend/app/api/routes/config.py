"""
Configuration API Routes
Endpoints for managing configuration
"""

import sys
import yaml
from pathlib import Path
from fastapi import APIRouter, HTTPException

# Add parent directory to path
sys.path.insert(0, str(Path(__file__).parent.parent.parent.parent.parent))

from app.models.api_models import ConfigResponse, ConfigUpdateRequest

router = APIRouter()


def get_config_path() -> Path:
    """Get path to config.yaml"""
    # Look for config.yaml in project root
    root_dir = Path(__file__).parent.parent.parent.parent.parent
    config_path = root_dir / "config.yaml"

    if not config_path.exists():
        raise FileNotFoundError("config.yaml not found")

    return config_path


@router.get("/config", response_model=ConfigResponse)
async def get_config():
    """
    Get current configuration

    Returns the contents of config.yaml including LLM, TMDB,
    proxy, and category settings.
    """
    try:
        config_path = get_config_path()

        with open(config_path, 'r', encoding='utf-8') as f:
            config_data = yaml.safe_load(f)

        return ConfigResponse(
            llm=config_data.get('llm', {}),
            tmdb=config_data.get('tmdb', {}),
            proxy=config_data.get('proxy'),
            category=config_data.get('category')
        )

    except FileNotFoundError as e:
        raise HTTPException(status_code=404, detail=str(e))
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to load config: {str(e)}")


@router.put("/config")
async def update_config(request: ConfigUpdateRequest):
    """
    Update configuration

    Updates config.yaml with new settings. Only provided fields
    will be updated, others remain unchanged.
    """
    try:
        config_path = get_config_path()

        # Load current config
        with open(config_path, 'r', encoding='utf-8') as f:
            config_data = yaml.safe_load(f)

        # Update fields
        if request.llm is not None:
            config_data['llm'] = {**config_data.get('llm', {}), **request.llm}

        if request.tmdb is not None:
            config_data['tmdb'] = {**config_data.get('tmdb', {}), **request.tmdb}

        if request.proxy is not None:
            config_data['proxy'] = request.proxy

        if request.category is not None:
            config_data['category'] = request.category

        # Save config
        with open(config_path, 'w', encoding='utf-8') as f:
            yaml.safe_dump(config_data, f, default_flow_style=False, allow_unicode=True)

        return {"status": "updated"}

    except FileNotFoundError as e:
        raise HTTPException(status_code=404, detail=str(e))
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to update config: {str(e)}")


@router.get("/config/categories")
async def get_categories():
    """
    Get category configuration

    Returns the contents of category.yaml with category rules.
    """
    try:
        root_dir = Path(__file__).parent.parent.parent.parent.parent
        category_path = root_dir / "category.yaml"

        if not category_path.exists():
            raise FileNotFoundError("category.yaml not found")

        with open(category_path, 'r', encoding='utf-8') as f:
            category_data = yaml.safe_load(f)

        return category_data

    except FileNotFoundError as e:
        raise HTTPException(status_code=404, detail=str(e))
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to load categories: {str(e)}")
