"""
Deserialization utilities
Convert cached show data dicts back to TVShow/Season/Episode dataclass objects
"""

import sys
from pathlib import Path
from typing import Dict, List

# Add parent directory to path to import from root
sys.path.insert(0, str(Path(__file__).parent.parent.parent.parent))

from model import TVShow, Season, Episode, FolderType


def deserialize_to_episode(episode_data: Dict, show_name: str, season_number: int) -> Episode:
    """
    Reconstruct Episode from cached episode dict

    Args:
        episode_data: Episode dict from cached job result
        show_name: Show name
        season_number: Season number

    Returns:
        Episode object
    """
    return Episode(
        original_path=Path(episode_data['original_path']),
        show_name=show_name,
        season_number=season_number,
        episode_number=episode_data['episode_number'],
        extension=Path(episode_data['original_file']).suffix,
        tmdb_title=episode_data.get('tmdb_title'),
        # Note: title will be auto-generated in __post_init__
    )


def deserialize_to_season(season_data: Dict, show_name: str, original_folder: Path) -> Season:
    """
    Reconstruct Season from cached season dict

    Args:
        season_data: Season dict from cached job result
        show_name: Show name
        original_folder: Original folder path

    Returns:
        Season object with filtered episodes
    """
    episodes = []

    for ep_data in season_data['episodes']:
        if not ep_data['selected']:
            continue  # Skip deselected episodes

        episodes.append(deserialize_to_episode(
            ep_data,
            show_name,
            season_data['season_number']
        ))

    return Season(
        show_name=show_name,
        season_number=season_data['season_number'],
        episodes=episodes,
        original_folder=original_folder
    )


def deserialize_to_tvshow(show_data: Dict) -> TVShow:
    """
    Reconstruct TVShow from cached show_data dict

    This reconstructs a TVShow object from the cached JSON data,
    filtering out any deselected seasons/episodes. The reconstructed
    object can be passed to TVShowOrganizer.organize_show() for execution.

    Args:
        show_data: Show dict from cached job result with structure:
            {
                'id': str,
                'name': str,
                'folder_type': str,
                'original_folder': str,
                'category': str,
                'selected': bool,
                'seasons': [
                    {
                        'season_number': int,
                        'selected': bool,
                        'episodes': [...]
                    }
                ]
            }

    Returns:
        TVShow object ready for organize_show()
    """
    seasons = []
    original_folder = Path(show_data['original_folder'])

    for season_data in show_data['seasons']:
        if not season_data['selected']:
            continue  # Skip deselected seasons

        season = deserialize_to_season(
            season_data,
            show_data['name'],
            original_folder
        )

        if season.episodes:  # Only add season if it has episodes
            seasons.append(season)

    # Reconstruct TVShow
    return TVShow(
        name=show_data['name'],
        seasons=seasons,
        original_folder=original_folder,
        folder_type=FolderType(show_data['folder_type']),
        category=show_data.get('category'),
        cn_name=show_data.get('cn_name'),
        en_name=show_data.get('en_name'),
        year=show_data.get('year'),
        tmdb_id=show_data.get('tmdb_id'),
        match_confidence=show_data.get('confidence'),
        # Note: tmdb_metadata not needed for execution since paths are recomputed
        # organize_show() will recompute all paths based on show metadata
    )


def filter_selected_shows(processed_shows: List[Dict]) -> List[Dict]:
    """
    Filter processed_shows to only include selected items

    Args:
        processed_shows: List of show dicts

    Returns:
        Filtered list with only selected shows
    """
    filtered = []

    for show in processed_shows:
        if not show.get('selected', True):
            continue

        # Filter seasons
        selected_seasons = []
        for season in show.get('seasons', []):
            if not season.get('selected', True):
                continue

            # Filter episodes
            selected_episodes = [
                ep for ep in season.get('episodes', [])
                if ep.get('selected', True)
            ]

            if selected_episodes:
                selected_seasons.append({
                    **season,
                    'episodes': selected_episodes
                })

        if selected_seasons:
            filtered.append({
                **show,
                'seasons': selected_seasons
            })

    return filtered
