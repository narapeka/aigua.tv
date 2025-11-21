"""Preview API endpoints"""

from fastapi import APIRouter, HTTPException

from webui.models.schemas import PreviewResponse, ShowPreviewSchema, SeasonPreviewSchema, EpisodePreviewSchema
from webui.services.job_manager import job_manager, JobStatus

router = APIRouter(prefix="/api/preview", tags=["preview"])


@router.get("/mock", response_model=PreviewResponse)
async def get_mock_preview():
    """Get mock preview data for testing the UI"""
    mock_job_id = "mock-preview-12345"
    
    mock_shows = [
        ShowPreviewSchema(
            folder_name="Breaking Bad",
            detected_name="Breaking Bad",
            cn_name=None,
            en_name="Breaking Bad",
            tmdb_match={
                "id": 1396,
                "name": "Breaking Bad",
                "year": 2008,
                "tmdbid": 1396
            },
            match_confidence="high",
            selected=True,
            seasons=[
                SeasonPreviewSchema(
                    season_number=1,
                    original_folder=None,
                    episodes=[
                        EpisodePreviewSchema(
                            episode_number=1,
                            original_file="Breaking.Bad.S01E01.Pilot.720p.mkv",
                            original_path="/source/Breaking Bad/Breaking.Bad.S01E01.Pilot.720p.mkv",
                            new_file="Breaking Bad - S01E01 - Pilot.mkv",
                            new_path="Breaking Bad (2008) {tmdb-1396}/Season 01/Breaking Bad - S01E01 - Pilot.mkv",
                            status="dry_run"
                        ),
                        EpisodePreviewSchema(
                            episode_number=2,
                            original_file="Breaking.Bad.S01E02.Cat's.in.the.Bag.720p.mkv",
                            original_path="/source/Breaking Bad/Breaking.Bad.S01E02.Cat's.in.the.Bag.720p.mkv",
                            new_file="Breaking Bad - S01E02 - Cat's in the Bag.mkv",
                            new_path="Breaking Bad (2008) {tmdb-1396}/Season 01/Breaking Bad - S01E02 - Cat's in the Bag.mkv",
                            status="dry_run"
                        ),
                        EpisodePreviewSchema(
                            episode_number=3,
                            original_file="Breaking.Bad.S01E03.And.the.Bag's.in.the.River.720p.mkv",
                            original_path="/source/Breaking Bad/Breaking.Bad.S01E03.And.the.Bag's.in.the.River.720p.mkv",
                            new_file="Breaking Bad - S01E03 - And the Bag's in the River.mkv",
                            new_path="Breaking Bad (2008) {tmdb-1396}/Season 01/Breaking Bad - S01E03 - And the Bag's in the River.mkv",
                            status="dry_run"
                        ),
                    ]
                )
            ],
            original_folder="/source/Breaking Bad",
            folder_type="direct_files"
        ),
        ShowPreviewSchema(
            folder_name="The Office",
            detected_name="The Office",
            cn_name=None,
            en_name="The Office",
            tmdb_match={
                "id": 2316,
                "name": "The Office",
                "year": 2005,
                "tmdbid": 2316
            },
            match_confidence="high",
            selected=True,
            seasons=[
                SeasonPreviewSchema(
                    season_number=1,
                    original_folder="/source/The Office/Season 1",
                    episodes=[
                        EpisodePreviewSchema(
                            episode_number=1,
                            original_file="The.Office.S01E01.Pilot.720p.mkv",
                            original_path="/source/The Office/Season 1/The.Office.S01E01.Pilot.720p.mkv",
                            new_file="The Office - S01E01 - Pilot.mkv",
                            new_path="The Office (2005) {tmdb-2316}/Season 01/The Office - S01E01 - Pilot.mkv",
                            status="dry_run"
                        ),
                        EpisodePreviewSchema(
                            episode_number=2,
                            original_file="The.Office.S01E02.Diversity.Day.720p.mkv",
                            original_path="/source/The Office/Season 1/The.Office.S01E02.Diversity.Day.720p.mkv",
                            new_file="The Office - S01E02 - Diversity Day.mkv",
                            new_path="The Office (2005) {tmdb-2316}/Season 01/The Office - S01E02 - Diversity Day.mkv",
                            status="dry_run"
                        ),
                    ]
                ),
                SeasonPreviewSchema(
                    season_number=2,
                    original_folder="/source/The Office/Season 2",
                    episodes=[
                        EpisodePreviewSchema(
                            episode_number=1,
                            original_file="The.Office.S02E01.The.Dundies.720p.mkv",
                            original_path="/source/The Office/Season 2/The.Office.S02E01.The.Dundies.720p.mkv",
                            new_file="The Office - S02E01 - The Dundies.mkv",
                            new_path="The Office (2005) {tmdb-2316}/Season 02/The Office - S02E01 - The Dundies.mkv",
                            status="dry_run"
                        ),
                    ]
                )
            ],
            original_folder="/source/The Office",
            folder_type="season_subfolders"
        ),
        ShowPreviewSchema(
            folder_name="一人之下",
            detected_name="一人之下",
            cn_name="一人之下",
            en_name="The Outcast",
            tmdb_match={
                "id": 123456,
                "name": "一人之下",
                "year": 2016,
                "tmdbid": 123456
            },
            match_confidence="medium",
            selected=False,
            seasons=[
                SeasonPreviewSchema(
                    season_number=1,
                    original_folder=None,
                    episodes=[
                        EpisodePreviewSchema(
                            episode_number=1,
                            original_file="一人之下.S01E01.第1集.mp4",
                            original_path="/source/一人之下/一人之下.S01E01.第1集.mp4",
                            new_file="一人之下 - S01E01 - Episode 01.mp4",
                            new_path="一人之下 (2016) {tmdb-123456}/Season 01/一人之下 - S01E01 - Episode 01.mp4",
                            status="dry_run"
                        ),
                    ]
                )
            ],
            original_folder="/source/一人之下",
            folder_type="direct_files"
        ),
        ShowPreviewSchema(
            folder_name="Unknown Show",
            detected_name="Unknown Show",
            cn_name=None,
            en_name=None,
            tmdb_match=None,
            match_confidence=None,
            selected=False,
            seasons=[],
            original_folder="/source/Unknown Show",
            folder_type="unknown"
        ),
    ]
    
    mock_stats = {
        "shows_processed": 2,
        "seasons_processed": 3,
        "episodes_moved": 7,
        "errors": 0
    }
    
    return PreviewResponse(
        job_id=mock_job_id,
        shows=mock_shows,
        stats=mock_stats
    )


@router.get("/{job_id}", response_model=PreviewResponse)
async def get_preview(job_id: str):
    """Get preview results for a dry-run job"""
    job = job_manager.get_job(job_id)
    if not job:
        raise HTTPException(status_code=404, detail="Job not found")
    
    job_status = job['status']
    if isinstance(job_status, JobStatus):
        job_status = job_status.value
    if job_status != "completed":
        raise HTTPException(status_code=400, detail=f"Job not completed (status: {job_status})")
    
    result = job.get('result')
    if not result:
        raise HTTPException(status_code=404, detail="Preview data not found")
    
    return PreviewResponse(
        job_id=job_id,
        shows=result.get('shows', []),
        stats=result.get('stats', {})
    )

