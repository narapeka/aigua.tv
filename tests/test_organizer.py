#!/usr/bin/env python3
"""
End-to-end test script for tv_show_organizer.py
Tests the complete TV show organization process with LLM and TMDB integration
"""

import sys
import tempfile
import shutil
from pathlib import Path

# Add parent directory to path to import modules
sys.path.insert(0, str(Path(__file__).parent.parent))

from tv_show_organizer import TVShowOrganizer
from config import load_config
from logger import setup_logging


def create_test_structure(base_dir: Path):
    """
    Create a test directory structure with TV show folders
    
    Returns:
        dict with folder paths and expected results
    """
    # Test case 1: Direct files (single season)
    show1_dir = base_dir / "权力的游戏"
    show1_dir.mkdir(parents=True, exist_ok=True)
    
    # Create some test video files
    (show1_dir / "S01E01.mkv").write_bytes(b"fake video content 1")
    (show1_dir / "S01E02.mkv").write_bytes(b"fake video content 2")
    (show1_dir / "S01E03.mkv").write_bytes(b"fake video content 3")
    
    # Test case 2: Season subfolders
    show2_dir = base_dir / "Breaking Bad"
    show2_dir.mkdir(parents=True, exist_ok=True)
    
    season1_dir = show2_dir / "Season 1"
    season1_dir.mkdir(parents=True, exist_ok=True)
    (season1_dir / "Breaking.Bad.S01E01.mkv").write_bytes(b"fake video content 4")
    (season1_dir / "Breaking.Bad.S01E02.mkv").write_bytes(b"fake video content 5")
    
    season2_dir = show2_dir / "Season 2"
    season2_dir.mkdir(parents=True, exist_ok=True)
    (season2_dir / "Breaking.Bad.S02E01.mkv").write_bytes(b"fake video content 6")
    
    # Test case 3: Show with no clear structure (should be skipped if low confidence)
    show3_dir = base_dir / "Unknown Show XYZ"
    show3_dir.mkdir(parents=True, exist_ok=True)
    (show3_dir / "episode1.mkv").write_bytes(b"fake video content 7")
    
    return {
        'show1': show1_dir,
        'show2': show2_dir,
        'show3': show3_dir,
        'base_dir': base_dir
    }


def test_organizer_initialization():
    """Test TVShowOrganizer initialization"""
    print("\n" + "="*60)
    print("Test 1: TVShowOrganizer Initialization")
    print("="*60)
    
    try:
        with tempfile.TemporaryDirectory() as tmpdir:
            input_dir = Path(tmpdir) / "input"
            output_dir = Path(tmpdir) / "output"
            input_dir.mkdir()
            output_dir.mkdir()
            
            # Create temporary log file
            with tempfile.NamedTemporaryFile(mode='w', suffix='.log', delete=False) as tmp_file:
                log_file = Path(tmp_file.name)
            
            logger = setup_logging(log_file, verbose=False)
            
            organizer = TVShowOrganizer(
                input_dir=str(input_dir),
                output_dir=str(output_dir),
                dry_run=True,
                verbose=False,
                log_dir=str(output_dir / "logs")
            )
            
            print(f"✓ Organizer initialized successfully")
            print(f"  Input Directory: {organizer.input_dir}")
            print(f"  Output Directory: {organizer.output_dir}")
            print(f"  Dry Run: {organizer.dry_run}")
            print(f"  File Operation Timeout: {organizer.file_operation_timeout}s")
            print(f"  LLM Agent: {organizer.llm_agent is not None}")
            print(f"  TMDB Client: {organizer.tmdb_client is not None}")
            print(f"  Cache: {organizer.cache is not None}")
            
            # Close all file handlers to allow cleanup on Windows
            for handler in logger.handlers[:]:
                if hasattr(handler, 'close'):
                    handler.close()
                logger.removeHandler(handler)
            
            # Close organizer's logger handlers
            if hasattr(organizer, 'logger'):
                for handler in organizer.logger.handlers[:]:
                    if hasattr(handler, 'close'):
                        handler.close()
                    organizer.logger.removeHandler(handler)
            
            return organizer, logger
    except Exception as e:
        print(f"✗ Failed to initialize organizer: {e}")
        import traceback
        traceback.print_exc()
        return None, None


def test_scan_folders(organizer: TVShowOrganizer):
    """Test folder scanning"""
    print("\n" + "="*60)
    print("Test 2: Scan Folders")
    print("="*60)
    
    try:
        with tempfile.TemporaryDirectory() as tmpdir:
            test_structure = create_test_structure(Path(tmpdir))
            
            # Temporarily set input directory
            original_input = organizer.input_dir
            organizer.input_dir = test_structure['base_dir']
            
            folders = organizer.scan_folders()
            
            print(f"✓ Scanned {len(folders)} folders")
            for folder in folders:
                print(f"  - {folder.name}")
            
            # Restore original input directory
            organizer.input_dir = original_input
            
            assert len(folders) == 3, f"Expected 3 folders, got {len(folders)}"
            print(f"✓ Folder count matches expected (3)")
            
            return True
    except Exception as e:
        print(f"✗ Error: {e}")
        import traceback
        traceback.print_exc()
        return False


def test_determine_folder_type(organizer: TVShowOrganizer):
    """Test folder type determination"""
    print("\n" + "="*60)
    print("Test 3: Determine Folder Type")
    print("="*60)
    
    try:
        with tempfile.TemporaryDirectory() as tmpdir:
            test_structure = create_test_structure(Path(tmpdir))
            
            # Test direct files
            folder_type1 = organizer.determine_folder_type(test_structure['show1'])
            print(f"  Show 1 ({test_structure['show1'].name}): {folder_type1.value}")
            assert folder_type1.value == "direct_files", f"Expected direct_files, got {folder_type1.value}"
            
            # Test season subfolders
            folder_type2 = organizer.determine_folder_type(test_structure['show2'])
            print(f"  Show 2 ({test_structure['show2'].name}): {folder_type2.value}")
            assert folder_type2.value == "season_subfolders", f"Expected season_subfolders, got {folder_type2.value}"
            
            print(f"✓ Folder types determined correctly")
            return True
    except Exception as e:
        print(f"✗ Error: {e}")
        import traceback
        traceback.print_exc()
        return False


def test_end_to_end_dry_run(organizer: TVShowOrganizer):
    """Test end-to-end process in dry-run mode"""
    print("\n" + "="*60)
    print("Test 4: End-to-End Process (Dry Run)")
    print("="*60)
    
    try:
        with tempfile.TemporaryDirectory() as tmpdir:
            input_dir = Path(tmpdir) / "input"
            output_dir = Path(tmpdir) / "output"
            input_dir.mkdir()
            output_dir.mkdir()
            
            # Create test structure
            test_structure = create_test_structure(input_dir)
            
            # Create a new organizer for this test
            with tempfile.NamedTemporaryFile(mode='w', suffix='.log', delete=False) as tmp_file:
                log_file = Path(tmp_file.name)
            
            logger = setup_logging(log_file, verbose=False)
            
            test_organizer = TVShowOrganizer(
                input_dir=str(input_dir),
                output_dir=str(output_dir),
                dry_run=True,
                verbose=True,
                log_dir=str(output_dir / "logs")
            )
            
            print(f"  Input: {input_dir}")
            print(f"  Output: {output_dir}")
            print(f"  Mode: DRY RUN")
            print(f"\n  Running scan_and_organize()...")
            
            success = test_organizer.scan_and_organize()
            
            print(f"\n  Result: {'Success' if success else 'Failed'}")
            print(f"  Shows Processed: {test_organizer.stats['shows_processed']}")
            print(f"  Seasons Processed: {test_organizer.stats['seasons_processed']}")
            print(f"  Episodes Moved: {test_organizer.stats['episodes_moved']}")
            print(f"  Errors: {test_organizer.stats['errors']}")
            print(f"  Unprocessed Shows: {len(test_organizer.unprocessed_shows)}")
            
            if test_organizer.unprocessed_shows:
                print(f"\n  Unprocessed Shows:")
                for item in test_organizer.unprocessed_shows:
                    print(f"    - {item['folder_name']}: {item['reason']}")
            
            # Verify files were not moved (dry run)
            assert (input_dir / "权力的游戏" / "S01E01.mkv").exists(), "File should still exist in input (dry run)"
            assert not (output_dir / "权力的游戏").exists(), "Output directory should not exist (dry run)"
            
            # Close all file handlers to allow cleanup on Windows
            if hasattr(test_organizer, 'logger'):
                for handler in test_organizer.logger.handlers[:]:
                    if hasattr(handler, 'close'):
                        handler.close()
                    test_organizer.logger.removeHandler(handler)
            
            if hasattr(logger, 'handlers'):
                for handler in logger.handlers[:]:
                    if hasattr(handler, 'close'):
                        handler.close()
                    logger.removeHandler(handler)
            
            print(f"✓ Dry run completed - files not moved as expected")
            
            return True
    except Exception as e:
        print(f"✗ Error: {e}")
        import traceback
        traceback.print_exc()
        return False


def test_cache_functionality(organizer: TVShowOrganizer):
    """Test cache functionality"""
    print("\n" + "="*60)
    print("Test 5: Cache Functionality")
    print("="*60)
    
    try:
        from cache import TVShowCache
        from tmdb import TVShowMetadata
        
        cache = TVShowCache()
        
        # Create a mock metadata object
        metadata = TVShowMetadata(
            id=1396,
            name="Breaking Bad",
            year=2008
        )
        
        # Test put and get
        cache.put("test_key", metadata)
        retrieved = cache.get("test_key")
        
        assert retrieved is not None, "Cache should return metadata"
        assert retrieved.id == 1396, "Cache should return correct ID"
        assert retrieved.name == "Breaking Bad", "Cache should return correct name"
        
        print(f"✓ Cache put/get works correctly")
        
        # Test cache miss
        missing = cache.get("nonexistent_key")
        assert missing is None, "Cache should return None for missing key"
        
        print(f"✓ Cache miss handled correctly")
        
        # Test cache size
        size = cache.size()
        assert size == 1, f"Cache should have 1 entry, got {size}"
        
        print(f"✓ Cache size tracking works")
        
        # Test clear
        cache.clear()
        assert cache.size() == 0, "Cache should be empty after clear"
        
        print(f"✓ Cache clear works")
        
        return True
    except Exception as e:
        print(f"✗ Error: {e}")
        import traceback
        traceback.print_exc()
        return False


def test_file_operation_timeout(organizer: TVShowOrganizer):
    """Test file operation timeout handling"""
    print("\n" + "="*60)
    print("Test 6: File Operation Timeout")
    print("="*60)
    
    try:
        from concurrent.futures import TimeoutError as FutureTimeoutError
        
        # Test that timeout mechanism is in place
        assert hasattr(organizer, '_file_operation_with_timeout'), "Organizer should have timeout method"
        assert organizer.file_operation_timeout == 15, "Timeout should be 15 seconds"
        
        print(f"✓ Timeout mechanism configured")
        print(f"  Timeout: {organizer.file_operation_timeout}s")
        print(f"  Method: _file_operation_with_timeout")
        
        # Test that timeout method works (with a fast operation)
        def fast_operation():
            return "success"
        
        result = organizer._file_operation_with_timeout(fast_operation)
        assert result == "success", "Timeout method should execute operations"
        
        print(f"✓ Timeout method executes operations correctly")
        
        return True
    except Exception as e:
        print(f"✗ Error: {e}")
        import traceback
        traceback.print_exc()
        return False


def test_episode_matching(organizer: TVShowOrganizer):
    """Test episode matching with TMDB metadata"""
    print("\n" + "="*60)
    print("Test 7: Episode Matching with TMDB")
    print("="*60)
    
    try:
        from model import Episode, TVShow
        from tmdb import TVShowMetadata, Season, Episode as TMDBEpisode
        
        # Create mock TMDB metadata
        tmdb_episodes = [
            TMDBEpisode(episode_number=1, title="试播集"),
            TMDBEpisode(episode_number=2, title="猫在袋中"),
            TMDBEpisode(episode_number=3, title="不再堕落")
        ]
        
        tmdb_season = Season(season_number=1, episodes=tmdb_episodes)
        tmdb_metadata = TVShowMetadata(
            id=1396,
            name="绝命毒师",
            year=2008,
            seasons=[tmdb_season]
        )
        
        # Create test episode
        from pathlib import Path
        test_path = Path("/fake/path/S01E01.mkv")
        episode = Episode(
            original_path=test_path,
            show_name="Breaking Bad",
            season_number=1,
            episode_number=1,
            extension=".mkv"
        )
        
        # Test matching
        organizer._match_episode_with_tmdb(episode, tmdb_metadata)
        
        assert episode.tmdb_title == "试播集", f"Expected '试播集', got '{episode.tmdb_title}'"
        
        print(f"✓ Episode matched correctly")
        print(f"  Episode: S{episode.season_number:02d}E{episode.episode_number:02d}")
        print(f"  TMDB Title: {episode.tmdb_title}")
        
        # Test episode without match
        episode2 = Episode(
            original_path=test_path,
            show_name="Breaking Bad",
            season_number=1,
            episode_number=99,  # Non-existent episode
            extension=".mkv"
        )
        
        organizer._match_episode_with_tmdb(episode2, tmdb_metadata)
        assert episode2.tmdb_title is None, "Non-existent episode should not have TMDB title"
        
        print(f"✓ Non-existent episode handled correctly")
        
        return True
    except Exception as e:
        print(f"✗ Error: {e}")
        import traceback
        traceback.print_exc()
        return False


def main():
    """Run all tests"""
    print("="*60)
    print("TV Show Organizer End-to-End Tests")
    print("="*60)
    
    results = []
    
    # Test 1: Initialization
    organizer, logger = test_organizer_initialization()
    results.append(("Initialization", organizer is not None))
    
    if organizer is None:
        print("\n✗ Cannot continue tests without organizer initialization")
        return
    
    # Test 2: Scan folders
    results.append(("Scan Folders", test_scan_folders(organizer)))
    
    # Test 3: Determine folder type
    results.append(("Determine Folder Type", test_determine_folder_type(organizer)))
    
    # Test 4: End-to-end dry run
    results.append(("End-to-End Dry Run", test_end_to_end_dry_run(organizer)))
    
    # Test 5: Cache functionality
    results.append(("Cache Functionality", test_cache_functionality(organizer)))
    
    # Test 6: File operation timeout
    results.append(("File Operation Timeout", test_file_operation_timeout(organizer)))
    
    # Test 7: Episode matching
    results.append(("Episode Matching", test_episode_matching(organizer)))
    
    # Print summary
    print("\n" + "="*60)
    print("Test Summary")
    print("="*60)
    
    passed = sum(1 for _, result in results if result)
    total = len(results)
    
    for test_name, result in results:
        status = "✓ PASS" if result else "✗ FAIL"
        print(f"  {status}: {test_name}")
    
    print(f"\nTotal: {passed}/{total} tests passed")
    
    if passed == total:
        print("\n✓ All tests passed!")
        return 0
    else:
        print(f"\n✗ {total - passed} test(s) failed")
        return 1


if __name__ == '__main__':
    exit(main())

