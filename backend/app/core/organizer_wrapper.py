"""
Organizer Wrapper
Wraps TVShowOrganizer for web usage without modifying the original code
"""

import sys
import uuid
from pathlib import Path
from typing import Dict, List, Any, Callable, Optional

# Add parent directory to path to import from root
sys.path.insert(0, str(Path(__file__).parent.parent.parent.parent))

from tv_show_organizer import TVShowOrganizer
from app.utils.deserializers import deserialize_to_tvshow, filter_selected_shows


class OrganizerWrapper:
    """Wrapper around TVShowOrganizer for WebUI"""

    @staticmethod
    def run_dry_run(
        input_dir: str,
        output_dir: str,
        config_path: Optional[str] = None
    ) -> Dict[str, Any]:
        """
        Run dry-run and return enriched results

        Args:
            input_dir: Input directory with TV show folders
            output_dir: Output directory for organized files
            config_path: Optional path to config.yaml

        Returns:
            Dict with stats, processed_shows, and unprocessed_shows
        """
        # Create organizer with dry_run=True
        organizer = TVShowOrganizer(
            input_dir=input_dir,
            output_dir=output_dir,
            dry_run=True,
            verbose=False,  # Suppress console output
            config_path=config_path
        )

        # Run the full scan and organize (no files moved)
        success = organizer.scan_and_organize()

        if not success:
            raise Exception("Dry-run failed - check input directory and configuration")

        # IMPORTANT: organizer.processed_shows already contains all the data we need!
        # It's a list of show_details dicts with structure:
        # {
        #   'name': str,
        #   'folder_type': str,
        #   'original_folder': str,
        #   'category': str,
        #   'seasons': [
        #     {
        #       'season_number': int,
        #       'episodes': [
        #         {
        #           'episode_number': int,
        #           'original_file': str,
        #           'original_path': str,
        #           'new_file': str,
        #           'new_path': str,
        #           'status': str
        #         }
        #       ]
        #     }
        #   ]
        # }

        # We just need to enrich these dicts with:
        # - UUID for each show (for frontend tracking)
        # - selection flags (initially all true)

        enriched_shows = []
        for show_detail in organizer.processed_shows:
            enriched_shows.append({
                'id': str(uuid.uuid4()),
                'selected': True,
                **show_detail,  # Spread existing data
                'seasons': [
                    {
                        **season,
                        'selected': True,
                        'episodes': [
                            {**ep, 'selected': True}
                            for ep in season['episodes']
                        ]
                    }
                    for season in show_detail['seasons']
                ]
            })

        return {
            "stats": organizer.stats,
            "processed_shows": enriched_shows,
            "unprocessed_shows": organizer.unprocessed_shows
        }

    @staticmethod
    def execute_selected(
        input_dir: str,
        output_dir: str,
        processed_shows: List[Dict],
        progress_callback: Optional[Callable[[Dict], None]] = None,
        config_path: Optional[str] = None
    ) -> Dict[str, Any]:
        """
        Execute organization for selected shows

        Args:
            input_dir: Input directory
            output_dir: Output directory
            processed_shows: List of show dicts from job result
            progress_callback: Optional callback for progress updates
            config_path: Optional path to config.yaml

        Returns:
            Dict with stats
        """
        # Filter to only selected shows/seasons/episodes
        selected_shows = filter_selected_shows(processed_shows)

        if not selected_shows:
            return {
                "stats": {
                    "shows_processed": 0,
                    "episodes_moved": 0,
                    "errors": 0
                }
            }

        # Create new organizer with dry_run=False
        organizer = TVShowOrganizer(
            input_dir=input_dir,
            output_dir=output_dir,
            dry_run=False,
            verbose=False,  # Suppress console output
            config_path=config_path
        )

        # Track overall progress
        total_shows = len(selected_shows)
        completed_shows = 0

        for show_data in selected_shows:
            try:
                # Send progress update
                if progress_callback:
                    progress_callback({
                        "type": "progress",
                        "data": {
                            "show": show_data['name'],
                            "status": "processing",
                            "completed": completed_shows,
                            "total": total_shows,
                            "percent": int((completed_shows / total_shows) * 100)
                        }
                    })

                # Reconstruct TVShow from cached ShowData
                tv_show = deserialize_to_tvshow(show_data)

                # Call existing organize_show() - it will move files
                success = organizer.organize_show(tv_show)

                completed_shows += 1

                # Send completion update
                if progress_callback:
                    progress_callback({
                        "type": "log",
                        "data": {
                            "message": f"{'✓' if success else '✗'} {show_data['name']} - "
                                      f"{len(tv_show.seasons)} seasons, "
                                      f"{sum(len(s.episodes) for s in tv_show.seasons)} episodes",
                            "level": "info" if success else "error"
                        }
                    })

            except Exception as e:
                # Send error update
                if progress_callback:
                    progress_callback({
                        "type": "log",
                        "data": {
                            "message": f"✗ Error processing {show_data['name']}: {str(e)}",
                            "level": "error"
                        }
                    })
                organizer.stats['errors'] = organizer.stats.get('errors', 0) + 1

        # Send final completion message
        if progress_callback:
            progress_callback({
                "type": "completed",
                "data": {
                    "stats": organizer.stats
                }
            })

        return {
            "stats": organizer.stats
        }
