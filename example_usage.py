#!/usr/bin/env python3
"""
Example usage and test script for TV Show Media Library Organizer

This script demonstrates how to use the organizer and creates sample folder structures for testing.
"""

import os
import sys
from pathlib import Path
import tempfile
import shutil

def create_test_structure():
    """Create sample TV show folder structures for testing"""
    
    # Create temporary directory for testing
    test_dir = Path(tempfile.mkdtemp(prefix="tv_test_"))
    print(f"Creating test structure in: {test_dir}")
    
    # Case 1: Direct files (single season shows)
    
    # Breaking Bad - well formatted filenames
    breaking_bad_dir = test_dir / "Breaking Bad"
    breaking_bad_dir.mkdir()
    
    breaking_bad_files = [
        "Breaking.Bad.S01E01.Pilot.mp4",
        "Breaking.Bad.S01E02.Cat's.in.the.Bag.mp4",
        "Breaking.Bad.S01E03.And.the.Bag's.in.the.River.mkv"
    ]
    
    for filename in breaking_bad_files:
        (breaking_bad_dir / filename).touch()
    
    # Friends - episode numbers only
    friends_dir = test_dir / "Friends"
    friends_dir.mkdir()
    
    friends_files = [
        "Episode 1 - The One Where Monica Gets a Roommate.mp4",
        "Episode 2 - The One with the Sonogram at the End.mp4",
        "Episode 3 - The One with the Thumb.avi"
    ]
    
    for filename in friends_files:
        (friends_dir / filename).touch()
    
    # The Office - poorly named files (will use position)
    office_dir = test_dir / "The Office"
    office_dir.mkdir()
    
    office_files = [
        "001.mp4",
        "002.mkv",
        "003.avi",
        "004.mp4"
    ]
    
    for filename in office_files:
        (office_dir / filename).touch()
    
    # Case 2: Season subfolders
    
    # Game of Thrones - multiple seasons with good structure
    got_dir = test_dir / "Game of Thrones"
    got_dir.mkdir()
    
    # Season 1
    got_s1 = got_dir / "Season 1"
    got_s1.mkdir()
    got_s1_files = [
        "Game.of.Thrones.S01E01.Winter.Is.Coming.mp4",
        "Game.of.Thrones.S01E02.The.Kingsroad.mp4",
        "Game.of.Thrones.S01E03.Lord.Snow.mkv"
    ]
    for filename in got_s1_files:
        (got_s1 / filename).touch()
    
    # Season 2
    got_s2 = got_dir / "Season 2"
    got_s2.mkdir()
    got_s2_files = [
        "Game.of.Thrones.S02E01.The.North.Remembers.mp4",
        "Game.of.Thrones.S02E02.The.Night.Lands.mkv"
    ]
    for filename in got_s2_files:
        (got_s2 / filename).touch()
    
    # Stranger Things - mixed naming in seasons
    st_dir = test_dir / "Stranger Things"
    st_dir.mkdir()
    
    # Season 1 - good naming
    st_s1 = st_dir / "S01"
    st_s1.mkdir()
    st_s1_files = [
        "Stranger.Things.S01E01.Chapter.One.The.Vanishing.of.Will.Byers.mp4",
        "Stranger.Things.S01E02.Chapter.Two.The.Weirdo.on.Maple.Street.mp4"
    ]
    for filename in st_s1_files:
        (st_s1 / filename).touch()
    
    # Season 2 - episode format only
    st_s2 = st_dir / "Season 02"
    st_s2.mkdir()
    st_s2_files = [
        "E01 - MADMAX.mkv",
        "E02 - Trick or Treat, Freak.mkv",
        "E03 - The Pollywog.mp4"
    ]
    for filename in st_s2_files:
        (st_s2 / filename).touch()
    
    # The Mandalorian - test case for unclear folder names but clear file season info
    mando_dir = test_dir / "The Mandalorian"
    mando_dir.mkdir()
    
    # Unclear folder name but files have season 2 info
    mando_s2 = mando_dir / "Random Folder"  # No season info in folder name
    mando_s2.mkdir()
    mando_s2_files = [
        "The.Mandalorian.S02E01.Chapter.9.The.Marshal.mp4",
        "The.Mandalorian.S02E02.Chapter.10.The.Passenger.mp4",
        "The.Mandalorian.S02E03.Chapter.11.The.Heiress.mkv"
    ]
    for filename in mando_s2_files:
        (mando_s2 / filename).touch()
    
    # Worst case scenario - no useful info in folder or filenames
    worst_case_dir = test_dir / "Mystery Show"
    worst_case_dir.mkdir()
    
    worst_case_folder = worst_case_dir / "random_folder_name"
    worst_case_folder.mkdir()
    worst_case_files = [
        "random_filename.mkv",
        "another_file.mp4",
        "video123.avi"
    ]
    for filename in worst_case_files:
        (worst_case_folder / filename).touch()
    
    print("\nTest structure created:")
    print_directory_tree(test_dir)
    
    return test_dir

def print_directory_tree(directory, prefix="", max_depth=3, current_depth=0):
    """Print directory structure in tree format"""
    if current_depth > max_depth:
        return
    
    directory = Path(directory)
    items = sorted(directory.iterdir(), key=lambda x: (x.is_file(), x.name.lower()))
    
    for i, item in enumerate(items):
        is_last = i == len(items) - 1
        current_prefix = "└── " if is_last else "├── "
        print(f"{prefix}{current_prefix}{item.name}")
        
        if item.is_dir() and current_depth < max_depth:
            next_prefix = prefix + ("    " if is_last else "│   ")
            print_directory_tree(item, next_prefix, max_depth, current_depth + 1)

def demonstrate_usage():
    """Demonstrate the TV show organizer with examples"""
    
    print("=" * 60)
    print("TV Show Media Library Organizer - Demo")
    print("=" * 60)
    
    # Create test structure
    test_input = create_test_structure()
    test_output = test_input.parent / "organized_tv"
    
    print(f"\nInput directory: {test_input}")
    print(f"Output directory: {test_output}")
    
    # Import the organizer
    try:
        from tv_show_organizer import MediaLibraryOrganizer
    except ImportError:
        print("Error: Cannot import tv_show_organizer.py")
        print("Make sure tv_show_organizer.py is in the current directory")
        return
    
    print("\n" + "=" * 60)
    print("DRY RUN - Preview what will happen")
    print("=" * 60)
    
    # Create organizer and run dry-run
    organizer = MediaLibraryOrganizer(
        input_dir=str(test_input),
        output_dir=str(test_output),
        dry_run=True,
        verbose=True
    )
    
    success = organizer.scan_and_organize()
    organizer.print_summary()
    
    if success:
        print(f"\n{'='*60}")
        print("ACTUAL ORGANIZATION")
        print("=" * 60)
        
        # Now do the actual organization
        organizer_real = MediaLibraryOrganizer(
            input_dir=str(test_input),
            output_dir=str(test_output),
            dry_run=False,
            verbose=False
        )
        
        organizer_real.scan_and_organize()
        organizer_real.print_summary()
        
        print(f"\nFinal organized structure:")
        if test_output.exists():
            print_directory_tree(test_output)
        
        # Cleanup option
        print(f"\nTest files created in: {test_input.parent}")
        cleanup = input("\nCleanup test files? (y/N): ").lower().strip()
        if cleanup == 'y':
            shutil.rmtree(test_input.parent)
            print("Test files cleaned up.")
        else:
            print(f"Test files preserved in: {test_input.parent}")
    
    else:
        print("Demo failed - check error messages above")

def show_usage_examples():
    """Show practical usage examples"""
    
    print("\n" + "=" * 60)
    print("PRACTICAL USAGE EXAMPLES")
    print("=" * 60)
    
    examples = [
        {
            "title": "Preview organization (recommended first step)",
            "command": 'python tv_show_organizer.py "~/Downloads/TV Shows" "~/Media/TV" --dry-run --verbose'
        },
        {
            "title": "Organize TV shows with progress tracking",
            "command": 'python tv_show_organizer.py "/Users/john/Unsorted TV" "/Users/john/Organized TV" --verbose'
        },
        {
            "title": "Quick preview of changes",
            "command": 'python tv_show_organizer.py "/media/downloads" "/media/tv" --dry-run'
        },
        {
            "title": "Windows paths example",
            "command": 'python tv_show_organizer.py "C:\\Downloads\\TV" "D:\\Media\\TV Shows" --dry-run'
        }
    ]
    
    for i, example in enumerate(examples, 1):
        print(f"\n{i}. {example['title']}:")
        print(f"   {example['command']}")
    
    print(f"\n{'='*60}")
    print("SUPPORTED FILE PATTERNS")
    print("=" * 60)
    
    patterns = [
        ("Season Detection", ["Season 1", "S01", "S1", "season 01", "1"]),
        ("Episode Detection", ["S01E01", "S1E1", "1x01", "Episode 1", "E01", "001"]),
        ("Video Formats", ["mp4", "mkv", "avi", "mov", "wmv", "flv", "webm", "m4v", "ts", "m2ts"])
    ]
    
    for category, items in patterns:
        print(f"\n{category}:")
        for item in items:
            print(f"  • {item}")

if __name__ == "__main__":
    if len(sys.argv) > 1 and sys.argv[1] == "--demo":
        demonstrate_usage()
    else:
        show_usage_examples()
        
        print(f"\n{'='*60}")
        print("To run a full demonstration with test files:")
        print("python example_usage.py --demo")
        print("=" * 60)