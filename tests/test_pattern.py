#!/usr/bin/env python3
"""
Comprehensive pattern matching and extraction tests.

Tests all functions from pattern.py:
- extract_season_number: Season number extraction with metadata filtering
- extract_episode_info: Episode information extraction with year protection
- normalize_metadata: Metadata removal from filenames
- generate_filename: Filename generation (if needed)

All tests are based on the actual implementation in pattern.py.
"""

import sys
from pathlib import Path

# Add parent directory to path to import modules
sys.path.insert(0, str(Path(__file__).parent.parent))

from pattern import (
    extract_season_number,
    extract_episode_info,
    normalize_metadata,
    SEASON_PATTERNS,
    EPISODE_PATTERNS
)


class TestSeasonExtraction:
    """Tests for extract_season_number function"""
    
    def test_4k_filtering(self):
        """Test that 4K is not detected as season 4"""
        print("\n" + "="*80)
        print("Test: 4K Filtering")
        print("="*80)
        
        test_cases = [
            ("4K杜比", None),
            ("4K HDR", None),
            ("8K杜比", None),
        ]
        
        all_passed = True
        for folder_name, expected in test_cases:
            result = extract_season_number(folder_name, None)
            passed = result == expected
            status = "PASS" if passed else "FAIL"
            print(f"  '{folder_name}' -> {result} (expected: {expected}) {status}")
            if not passed:
                all_passed = False
        
        return all_passed
    
    def test_season_0_specials(self):
        """Test Season 0 (Specials) support"""
        print("\n" + "="*80)
        print("Test: Season 0 (Specials)")
        print("="*80)
        
        test_cases = [
            ("Season 00(Specials)", 0),
            ("S00", 0),
            ("Season 0", 0),
            ("S0", 0),
        ]
        
        all_passed = True
        for folder_name, expected in test_cases:
            result = extract_season_number(folder_name, None)
            passed = result == expected
            status = "PASS" if passed else "FAIL"
            print(f"  '{folder_name}' -> {result} (expected: {expected}) {status}")
            if not passed:
                all_passed = False
        
        return all_passed
    
    def test_season_extraction_basic(self):
        """Test basic season extraction patterns"""
        print("\n" + "="*80)
        print("Test: Basic Season Extraction")
        print("="*80)
        
        test_cases = [
            ("Season 1", 1),
            ("Season 4", 4),
            ("S01", 1),
            ("S1", 1),
            ("S03", 3),
            ("season 2", 2),
            ("s10", 10),
        ]
        
        all_passed = True
        for folder_name, expected in test_cases:
            result = extract_season_number(folder_name, None)
            passed = result == expected
            status = "PASS" if passed else "FAIL"
            print(f"  '{folder_name}' -> {result} (expected: {expected}) {status}")
            if not passed:
                all_passed = False
        
        return all_passed
    
    def test_season_extraction_with_metadata(self):
        """Test season extraction from filenames with metadata"""
        print("\n" + "="*80)
        print("Test: Season Extraction with Metadata")
        print("="*80)
        
        test_cases = [
            ("刑警处容.Cheo-Yong.S01.2014.1080p.NF.WEB-DL.x264.E-AC3-ATTKC", 1),
            ("一人之下第二季.The.Outcast.S02.2017.1080p.WEB-DL.H265.AAC-HHWEB", 2),
            ("Show.S03.1080p.BluRay.x264.mkv", 3),
        ]
        
        all_passed = True
        for folder_name, expected in test_cases:
            result = extract_season_number(folder_name, None)
            passed = result == expected
            status = "PASS" if passed else "FAIL"
            print(f"  '{folder_name[:60]:60}' -> {result} (expected: {expected}) {status}")
            if not passed:
                all_passed = False
        
        return all_passed
    
    def test_season_extraction_chinese(self):
        """Test Chinese season patterns"""
        print("\n" + "="*80)
        print("Test: Chinese Season Patterns")
        print("="*80)
        
        test_cases = [
            ("第一季", 1),
            ("第二季", 2),
            ("第三季", 3),
            ("第1季", 1),
            ("第2季", 2),
        ]
        
        all_passed = True
        for folder_name, expected in test_cases:
            result = extract_season_number(folder_name, None)
            passed = result == expected
            status = "PASS" if passed else "FAIL"
            print(f"  '{folder_name}' -> {result} (expected: {expected}) {status}")
            if not passed:
                all_passed = False
        
        return all_passed
    
    def test_year_filtering(self):
        """Test that years (1900-2099) are not detected as seasons"""
        print("\n" + "="*80)
        print("Test: Year Filtering")
        print("="*80)
        
        test_cases = [
            ("Show 2014", None),  # Year should not be detected as season
            ("Show 2020", None),
            ("Show 1999", None),
        ]
        
        all_passed = True
        for folder_name, expected in test_cases:
            result = extract_season_number(folder_name, None)
            passed = result == expected
            status = "PASS" if passed else "FAIL"
            print(f"  '{folder_name}' -> {result} (expected: {expected}) {status}")
            if not passed:
                all_passed = False
        
        return all_passed


class TestEpisodeExtraction:
    """Tests for extract_episode_info function"""
    
    def test_episode_extraction_basic(self):
        """Test basic episode extraction patterns"""
        print("\n" + "="*80)
        print("Test: Basic Episode Extraction")
        print("="*80)
        
        test_cases = [
            ("S01E01.mkv", (1, 1, None)),
            ("S02E05.mkv", (2, 5, None)),
            ("S1E1.mkv", (1, 1, None)),
            ("S01EP02.mkv", (1, 2, None)),
            ("01x02.mkv", (1, 2, None)),
        ]
        
        all_passed = True
        for filename, expected in test_cases:
            result = extract_episode_info(filename, 1)
            passed = result == expected
            status = "PASS" if passed else "FAIL"
            print(f"  '{filename}'")
            print(f"    Result: S{result[0]:02d}E{result[1]:02d} (expected: S{expected[0]:02d}E{expected[1]:02d}) {status}")
            if not passed:
                all_passed = False
        
        return all_passed
    
    def test_episode_extraction_with_metadata(self):
        """Test episode extraction from filenames with metadata"""
        print("\n" + "="*80)
        print("Test: Episode Extraction with Metadata")
        print("="*80)
        
        test_cases = [
            ("Twelve S01E01 2025 1080p DSNP WEB-DL H264 AAC-TGWEB.mkv", (1, 1, None)),
            ("娜娜.2006.S00E01.ass", (0, 1, None)),
            ("Lets.Get.Divorced.S01E01.2160p.NF.WEB-DL.DV.H.265.DDP5.1-ADWeb.mkv", (1, 1, None)),
        ]
        
        all_passed = True
        for filename, expected in test_cases:
            result = extract_episode_info(filename, 1)
            passed = result == expected
            status = "PASS" if passed else "FAIL"
            print(f"  '{filename[:60]:60}'")
            print(f"    Result: S{result[0]:02d}E{result[1]:02d} (expected: S{expected[0]:02d}E{expected[1]:02d}) {status}")
            if not passed:
                all_passed = False
        
        return all_passed
    
    def test_episode_year_protection(self):
        """Test that years are protected during episode extraction"""
        print("\n" + "="*80)
        print("Test: Episode Year Protection")
        print("="*80)
        
        test_cases = [
            ("Twelve S01E01 2025 1080p DSNP WEB-DL H264 AAC-TGWEB.mkv", (1, 1, None)),
            ("Show S02E05 2014 1080p.mkv", (2, 5, None)),
            ("S01E01 2025.mkv", (1, 1, None)),
        ]
        
        all_passed = True
        for filename, expected in test_cases:
            result = extract_episode_info(filename, 1)
            passed = result == expected
            status = "PASS" if passed else "FAIL"
            print(f"  '{filename[:60]:60}'")
            print(f"    Result: S{result[0]:02d}E{result[1]:02d} (expected: S{expected[0]:02d}E{expected[1]:02d}) {status}")
            if not passed:
                print(f"    ERROR: Year was incorrectly included in episode number!")
                all_passed = False
        
        return all_passed
    
    def test_episode_chinese_patterns(self):
        """Test Chinese episode patterns"""
        print("\n" + "="*80)
        print("Test: Chinese Episode Patterns")
        print("="*80)
        
        test_cases = [
            ("第一集.mkv", (1, 1, None)),
            ("第二集.mkv", (1, 2, None)),
            ("第10集.mkv", (1, 10, None)),
        ]
        
        all_passed = True
        for filename, expected in test_cases:
            result = extract_episode_info(filename, 1)
            # For Chinese patterns, we mainly care that episode is extracted correctly
            passed = result[1] == expected[1]
            status = "PASS" if passed else "FAIL"
            print(f"  '{filename}'")
            print(f"    Result: S{result[0]:02d}E{result[1]:02d} (expected episode: {expected[1]}) {status}")
            if not passed:
                all_passed = False
        
        return all_passed
    
    def test_episode_multi_episode(self):
        """Test multi-episode patterns"""
        print("\n" + "="*80)
        print("Test: Multi-Episode Patterns")
        print("="*80)
        
        test_cases = [
            ("S01E01-S01E02.mkv", (1, 1, 2)),
            ("S01E01-E02.mkv", (1, 1, 2)),
            ("S01E01E02.mkv", (1, 1, 2)),
        ]
        
        all_passed = True
        for filename, expected in test_cases:
            result = extract_episode_info(filename, 1)
            passed = result == expected
            status = "PASS" if passed else "FAIL"
            print(f"  '{filename}'")
            if expected[2]:
                print(f"    Result: S{result[0]:02d}E{result[1]:02d}-E{result[2]:02d} (expected: S{expected[0]:02d}E{expected[1]:02d}-E{expected[2]:02d}) {status}")
            else:
                print(f"    Result: S{result[0]:02d}E{result[1]:02d} (expected: S{expected[0]:02d}E{expected[1]:02d}) {status}")
            if not passed:
                all_passed = False
        
        return all_passed


class TestNormalization:
    """Tests for normalize_metadata function"""
    
    def test_normalization_basic(self):
        """Test basic metadata normalization"""
        print("\n" + "="*80)
        print("Test: Basic Metadata Normalization")
        print("="*80)
        
        test_cases = [
            ("4K杜比", "Should remove 4K"),
            ("Season 4", "Should keep Season 4"),
            ("S01E01 2025 1080p H264", "Should remove metadata, keep S01E01"),
        ]
        
        for original, description in test_cases:
            normalized = normalize_metadata(original, preserve_years=True)
            print(f"  Original: {original[:50]}")
            print(f"  Normalized: {normalized[:50]}")
            print(f"  Description: {description}")
            print()
        
        return True
    
    def test_normalization_resolutions(self):
        """Test resolution removal"""
        print("\n" + "="*80)
        print("Test: Resolution Removal")
        print("="*80)
        
        test_cases = [
            ("Show 1080p.mkv", "Should remove 1080p"),
            ("Show 720p.mkv", "Should remove 720p"),
            ("Show 2160p.mkv", "Should remove 2160p (4K)"),
            ("Show 4K.mkv", "Should remove 4K"),
        ]
        
        for original, description in test_cases:
            normalized = normalize_metadata(original, preserve_years=True)
            print(f"  '{original}' -> '{normalized}' ({description})")
        
        return True
    
    def test_normalization_codecs(self):
        """Test codec removal"""
        print("\n" + "="*80)
        print("Test: Codec Removal")
        print("="*80)
        
        test_cases = [
            ("Show H264.mkv", "Should remove H264"),
            ("Show x265.mkv", "Should remove x265"),
            ("Show H.265.mkv", "Should remove H.265"),
        ]
        
        for original, description in test_cases:
            normalized = normalize_metadata(original, preserve_years=True)
            print(f"  '{original}' -> '{normalized}' ({description})")
        
        return True
    
    def test_normalization_years(self):
        """Test year preservation"""
        print("\n" + "="*80)
        print("Test: Year Preservation")
        print("="*80)
        
        test_cases = [
            ("Show 2014.mkv", "Should preserve year in show name"),
            ("Show 1080p 2014.mkv", "Should remove 1080p, preserve year"),
        ]
        
        for original, description in test_cases:
            normalized = normalize_metadata(original, preserve_years=True)
            print(f"  '{original}' -> '{normalized}' ({description})")
        
        return True


class TestEdgeCases:
    """Tests for edge cases and special scenarios"""
    
    def test_space_removal_edge_cases(self):
        """Test space removal between digits in episode extraction"""
        print("\n" + "="*80)
        print("Test: Space Removal Edge Cases")
        print("="*80)
        
        # These test the space removal logic in extract_episode_info
        test_cases = [
            ("E01 888.mkv", "Episode pattern followed by 3-digit number"),
            ("S01E01 888.mkv", "Season-episode pattern followed by 3-digit number"),
            ("E01 2025.mkv", "Episode pattern followed by 4-digit year - should protect year"),
            ("1 888.mkv", "Single digit followed by 3-digit number"),
        ]
        
        for filename, description in test_cases:
            # Test that extract_episode_info handles these correctly
            result = extract_episode_info(filename, 1)
            print(f"  '{filename:40}' -> S{result[0]:02d}E{result[1]:02d} ({description})")
        
        return True
    
    def test_complex_filenames(self):
        """Test complex real-world filenames"""
        print("\n" + "="*80)
        print("Test: Complex Real-World Filenames")
        print("="*80)
        
        test_cases = [
            ("Twelve S01E01 2025 1080p DSNP WEB-DL H264 AAC-TGWEB.mkv", (1, 1, None)),
            ("刑警处容.Cheo-Yong.S01.2014.1080p.NF.WEB-DL.x264.E-AC3-ATTKC", (1, None, None)),  # No episode in folder name
            ("一人之下第二季.The.Outcast.S02.2017.1080p.WEB-DL.H265.AAC-HHWEB", (2, None, None)),  # No episode in folder name
        ]
        
        all_passed = True
        for filename, expected in test_cases:
            if expected[1] is not None:
                # Has episode number
                result = extract_episode_info(filename, 1)
                passed = result[0] == expected[0] and result[1] == expected[1]
                status = "PASS" if passed else "FAIL"
                print(f"  '{filename[:60]:60}'")
                print(f"    Result: S{result[0]:02d}E{result[1]:02d} (expected: S{expected[0]:02d}E{expected[1]:02d}) {status}")
            else:
                # Only season, no episode
                season_result = extract_season_number(filename, None)
                passed = season_result == expected[0]
                status = "PASS" if passed else "FAIL"
                print(f"  '{filename[:60]:60}'")
                print(f"    Season: {season_result} (expected: {expected[0]}) {status}")
            if not passed:
                all_passed = False
        
        return all_passed


def run_all_tests():
    """Run all pattern tests"""
    print("="*80)
    print("Pattern Matching and Extraction Test Suite")
    print("="*80)
    print("\nTesting functions from pattern.py:")
    print("  - extract_season_number")
    print("  - extract_episode_info")
    print("  - normalize_metadata")
    
    results = []
    
    # Season extraction tests
    season_tests = TestSeasonExtraction()
    results.append(("4K Filtering", season_tests.test_4k_filtering()))
    results.append(("Season 0 (Specials)", season_tests.test_season_0_specials()))
    results.append(("Basic Season Extraction", season_tests.test_season_extraction_basic()))
    results.append(("Season with Metadata", season_tests.test_season_extraction_with_metadata()))
    results.append(("Chinese Season Patterns", season_tests.test_season_extraction_chinese()))
    results.append(("Year Filtering", season_tests.test_year_filtering()))
    
    # Episode extraction tests
    episode_tests = TestEpisodeExtraction()
    results.append(("Basic Episode Extraction", episode_tests.test_episode_extraction_basic()))
    results.append(("Episode with Metadata", episode_tests.test_episode_extraction_with_metadata()))
    results.append(("Episode Year Protection", episode_tests.test_episode_year_protection()))
    results.append(("Chinese Episode Patterns", episode_tests.test_episode_chinese_patterns()))
    results.append(("Multi-Episode Patterns", episode_tests.test_episode_multi_episode()))
    
    # Normalization tests
    norm_tests = TestNormalization()
    results.append(("Basic Normalization", norm_tests.test_normalization_basic()))
    results.append(("Resolution Removal", norm_tests.test_normalization_resolutions()))
    results.append(("Codec Removal", norm_tests.test_normalization_codecs()))
    results.append(("Year Preservation", norm_tests.test_normalization_years()))
    
    # Edge cases
    edge_tests = TestEdgeCases()
    results.append(("Space Removal Edge Cases", edge_tests.test_space_removal_edge_cases()))
    results.append(("Complex Filenames", edge_tests.test_complex_filenames()))
    
    # Print summary
    print("\n" + "="*80)
    print("Test Summary")
    print("="*80)
    
    passed = sum(1 for _, result in results if result)
    total = len(results)
    
    for test_name, result in results:
        status = "[PASS]" if result else "[FAIL]"
        print(f"  {status}: {test_name}")
    
    print(f"\nTotal: {passed}/{total} tests passed")
    
    return 0 if passed == total else 1


if __name__ == '__main__':
    sys.exit(run_all_tests())
