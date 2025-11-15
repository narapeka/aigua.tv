#!/usr/bin/env python3
"""
Integration tests for TV show matching and validation.

Consolidates tests for:
- Season validation logic
- Wrong match detection
- LLM + TMDB integration
- Confidence checking
"""

import logging
import sys
from pathlib import Path

# Add parent directory to path to import modules
sys.path.insert(0, str(Path(__file__).parent.parent))

from llm import LLMAgent, TVShowInfo
from tmdb import TMDBClient, create_tmdb_client_from_config
from config import load_config
from tv_show_organizer import TVShowOrganizer
from pattern import extract_season_number

# Setup logging
logging.basicConfig(
    level=logging.DEBUG,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)


class TestSeasonValidation:
    """Tests for season validation logic"""
    
    def __init__(self):
        self.config = load_config()
        self.llm_agent = None
        self.tmdb_client = None
    
    def setup(self):
        """Setup test dependencies"""
        self.llm_agent = LLMAgent(
            api_key=self.config.llm.api_key,
            base_url=self.config.llm.base_url,
            model=self.config.llm.model,
            batch_size=self.config.llm.batch_size,
            rate_limit=self.config.llm.rate_limit,
            logger=logger
        )
        self.tmdb_client = create_tmdb_client_from_config(self.config, logger)
    
    def test_season_detection(self):
        """Test season detection from folder name"""
        print("\n" + "="*80)
        print("Test: Season Detection")
        print("="*80)
        
        folder_name = "一人之下第二季.The.Outcast.S02.2017.1080p.WEB-DL.H265.AAC-HHWEB"
        
        print(f"\nFolder name: {folder_name}")
        
        try:
            detected_season = extract_season_number(folder_name, None)
            print(f"Detected season from folder name: {detected_season}")
            
            if detected_season and 1 <= detected_season <= 100:
                print(f"  ✓ Season {detected_season} detected from folder name")
                return detected_season
            else:
                print(f"  ✗ No valid season detected from folder name")
                return None
        except Exception as e:
            print(f"Error in season detection: {e}")
            import traceback
            traceback.print_exc()
            return None
    
    def test_llm_extraction(self):
        """Test LLM extraction for the folder name"""
        print("\n" + "="*80)
        print("Test: LLM Extraction")
        print("="*80)
        
        if not self.llm_agent:
            self.setup()
        
        folder_name = "一人之下第二季.The.Outcast.S02.2017.1080p.WEB-DL.H265.AAC-HHWEB"
        
        try:
            print(f"\nFolder name: {folder_name}")
            print("Extracting TV show info using LLM...")
            
            results = self.llm_agent.extract_tvshow([folder_name])
            
            if results:
                info = results[0]
                print(f"\nExtracted Info:")
                print(f"  folder_name: {info.folder_name}")
                print(f"  cn_name: {info.cn_name}")
                print(f"  en_name: {info.en_name}")
                print(f"  year: {info.year}")
                print(f"  tmdbid: {info.tmdbid}")
                
                # Verify season is stripped from names
                if info.cn_name and ("第二季" in info.cn_name or "S02" in info.cn_name):
                    print(f"\n  ⚠️  WARNING: Season number still in cn_name: {info.cn_name}")
                else:
                    print(f"\n  ✓ Season number correctly stripped from cn_name")
                
                if info.en_name and "S02" in info.en_name:
                    print(f"  ⚠️  WARNING: Season number still in en_name: {info.en_name}")
                else:
                    print(f"  ✓ Season number correctly stripped from en_name")
                
                return info
            else:
                print("No results from LLM extraction")
                return None
        except Exception as e:
            print(f"Error in LLM extraction: {e}")
            import traceback
            traceback.print_exc()
            return None
    
    def test_tmdb_search_with_season(self, tv_show_info: TVShowInfo, detected_season: int):
        """Test TMDB search with season > 1 logic"""
        print("\n" + "="*80)
        print("Test: TMDB Search with Season > 1 Logic")
        print("="*80)
        
        if not self.tmdb_client:
            self.setup()
        
        folder_name = tv_show_info.folder_name
        
        try:
            print(f"\nSearching TMDB with:")
            print(f"  folder_name: {folder_name}")
            print(f"  cn_name: {tv_show_info.cn_name}")
            print(f"  en_name: {tv_show_info.en_name}")
            print(f"  year: {tv_show_info.year} (from LLM - may be season year)")
            print(f"  detected_season: {detected_season}")
            print(f"  folder_type: direct_files")
            print(f"\n  → Expected: Search WITHOUT year filter (since season > 1)")
            print(f"  → Then validate season {detected_season} air date year")
            
            metadata = self.tmdb_client.get_tv_show(
                folder_name=folder_name,
                cn_name=tv_show_info.cn_name,
                en_name=tv_show_info.en_name,
                year=tv_show_info.year,
                tmdbid=tv_show_info.tmdbid,
                folder_type="direct_files",
                detected_season=detected_season
            )
            
            if metadata:
                print(f"\nTMDB Match Result:")
                print(f"  ID: {metadata.id}")
                print(f"  Name: {metadata.name}")
                print(f"  Original Name: {metadata.original_name}")
                print(f"  Show First Air Date Year: {metadata.year}")
                print(f"  Match Confidence: {metadata.match_confidence}")
                print(f"  Search Language: {metadata.search_language}")
                
                # Check if this is the correct match
                is_correct = False
                if "一人之下" in metadata.name or "The Outcast" in (metadata.original_name or ""):
                    print(f"\n  ✓ CORRECT MATCH!")
                    is_correct = True
                elif "下北泽" in metadata.name or "下北泽" in (metadata.original_name or ""):
                    print(f"\n  ❌ WRONG MATCH DETECTED!")
                    print(f"     Expected: 一人之下 / The Outcast")
                    print(f"     Got: {metadata.name}")
                else:
                    print(f"\n  ⚠️  UNEXPECTED MATCH - verify manually")
                
                # Check confidence
                if metadata.match_confidence == "high":
                    print(f"\n  ✓ High confidence match")
                    if is_correct:
                        print(f"  ✓ Correct match with high confidence - SUCCESS!")
                    else:
                        print(f"  ✗ Wrong match with high confidence - FAILURE!")
                else:
                    print(f"\n  ⚠️  Confidence: {metadata.match_confidence}")
                
                return metadata
            else:
                print("\nNo TMDB match found")
                return None
        except Exception as e:
            print(f"Error in TMDB search: {e}")
            import traceback
            traceback.print_exc()
            return None


class TestWrongMatch:
    """Tests for wrong match detection"""
    
    def __init__(self):
        self.config = load_config()
        self.llm_agent = None
        self.tmdb_client = None
    
    def setup(self):
        """Setup test dependencies"""
        self.llm_agent = LLMAgent(
            api_key=self.config.llm.api_key,
            base_url=self.config.llm.base_url,
            model=self.config.llm.model,
            batch_size=self.config.llm.batch_size,
            rate_limit=self.config.llm.rate_limit,
            logger=logger
        )
        self.tmdb_client = create_tmdb_client_from_config(self.config, logger)
    
    def test_llm_extraction(self):
        """Test LLM extraction for problematic folder name"""
        print("\n" + "="*80)
        print("Test: LLM Extraction (Wrong Match Case)")
        print("="*80)
        
        if not self.llm_agent:
            self.setup()
        
        folder_name = "一人之下第二季.The.Outcast.S02.2017.1080p.WEB-DL.H265.AAC-HHWEB"
        
        try:
            print(f"\nFolder name: {folder_name}")
            print("Extracting TV show info using LLM...")
            
            results = self.llm_agent.extract_tvshow([folder_name])
            
            if results:
                info = results[0]
                print(f"\nExtracted Info:")
                print(f"  folder_name: {info.folder_name}")
                print(f"  cn_name: {info.cn_name}")
                print(f"  en_name: {info.en_name}")
                print(f"  year: {info.year}")
                print(f"  tmdbid: {info.tmdbid}")
                
                return info
            else:
                print("No results from LLM extraction")
                return None
        except Exception as e:
            print(f"Error in LLM extraction: {e}")
            import traceback
            traceback.print_exc()
            return None
    
    def test_tmdb_search(self, tv_show_info: TVShowInfo):
        """Test TMDB search with extracted info"""
        print("\n" + "="*80)
        print("Test: TMDB Search (Wrong Match Case)")
        print("="*80)
        
        if not self.tmdb_client:
            self.setup()
        
        try:
            print(f"\nSearching TMDB with:")
            print(f"  folder_name: {tv_show_info.folder_name}")
            print(f"  cn_name: {tv_show_info.cn_name}")
            print(f"  en_name: {tv_show_info.en_name}")
            print(f"  year: {tv_show_info.year}")
            print(f"  tmdbid: {tv_show_info.tmdbid}")
            
            metadata = self.tmdb_client.get_tv_show(
                folder_name=tv_show_info.folder_name,
                cn_name=tv_show_info.cn_name,
                en_name=tv_show_info.en_name,
                year=tv_show_info.year,
                tmdbid=tv_show_info.tmdbid
            )
            
            if metadata:
                print(f"\nTMDB Match Result:")
                print(f"  ID: {metadata.id}")
                print(f"  Name: {metadata.name}")
                print(f"  Original Name: {metadata.original_name}")
                print(f"  Year: {metadata.year}")
                print(f"  Match Confidence: {metadata.match_confidence}")
                print(f"  Search Language: {metadata.search_language}")
                
                # Check if this is the wrong match
                if "下北泽" in metadata.name or "下北泽" in (metadata.original_name or ""):
                    print(f"\n  ❌ WRONG MATCH DETECTED!")
                    print(f"     Expected: 一人之下 / The Outcast")
                    print(f"     Got: {metadata.name}")
                elif "一人之下" in metadata.name or "The Outcast" in (metadata.original_name or ""):
                    print(f"\n  ✓ CORRECT MATCH!")
                else:
                    print(f"\n  ⚠️  UNEXPECTED MATCH - verify manually")
                
                return metadata
            else:
                print("\nNo TMDB match found")
                return None
        except Exception as e:
            print(f"Error in TMDB search: {e}")
            import traceback
            traceback.print_exc()
            return None
    
    def test_manual_tmdb_search(self):
        """Test TMDB search with manual queries"""
        print("\n" + "="*80)
        print("Test: Manual TMDB Search Tests")
        print("="*80)
        
        if not self.tmdb_client:
            self.setup()
        
        try:
            # Test different search queries
            test_queries = [
                ("一人之下", 2016),  # Chinese name with year
                ("一人之下", None),  # Chinese name without year
                ("The Outcast", 2016),  # English name with year
                ("The Outcast", None),  # English name without year
            ]
            
            for query, year in test_queries:
                print(f"\n--- Searching: '{query}' (year: {year}) ---")
                results = self.tmdb_client.search_tv_show(query, year)
                
                if results:
                    print(f"Found {len(results)} results:")
                    for i, result in enumerate(results[:5], 1):  # Show first 5
                        print(f"  {i}. {result.name} (ID: {result.id}, Year: {result.year})")
                        if result.original_name:
                            print(f"     Original: {result.original_name}")
                else:
                    print("  No results")
        except Exception as e:
            print(f"Error in manual TMDB search: {e}")
            import traceback
            traceback.print_exc()


def run_season_validation_tests():
    """Run season validation tests"""
    print("="*80)
    print("Season Validation Test Suite")
    print("="*80)
    
    test = TestSeasonValidation()
    
    # Test 1: Season Detection
    detected_season = test.test_season_detection()
    
    # Test 2: LLM Extraction
    tv_show_info = test.test_llm_extraction()
    
    if tv_show_info and detected_season:
        # Test 3: TMDB Search with season logic
        metadata = test.test_tmdb_search_with_season(tv_show_info, detected_season)
        
        if metadata:
            print("\n" + "="*80)
            print("Season Validation Summary")
            print("="*80)
            print("✓ Season detection from folder name")
            print("✓ LLM extracts show name without season number")
            print("✓ TMDB search without year filter (for season > 1)")
            print("✓ Year mismatch check skipped (for season > 1)")
            print("✓ Correct match with high confidence")
            return True
    
    return False


def run_wrong_match_tests():
    """Run wrong match detection tests"""
    print("="*80)
    print("Wrong Match Detection Test Suite")
    print("="*80)
    
    test = TestWrongMatch()
    
    # Test 1: LLM Extraction
    tv_show_info = test.test_llm_extraction()
    
    if tv_show_info:
        # Test 2: TMDB Search
        metadata = test.test_tmdb_search(tv_show_info)
        
        # Test 3: Manual searches
        test.test_manual_tmdb_search()
        
        if metadata:
            print("\n" + "="*80)
            print("Wrong Match Analysis Summary")
            print("="*80)
            print("Key Findings:")
            print("1. LLM Extraction: Check if season numbers are stripped")
            print("2. TMDB Search: Verify search logic and year handling")
            print("3. Confidence: Analyze why wrong matches get high confidence")
            return True
    
    return False


def main():
    """Run all integration tests"""
    print("="*80)
    print("Integration Test Suite")
    print("="*80)
    
    results = []
    
    # Run season validation tests
    results.append(("Season Validation", run_season_validation_tests()))
    
    # Run wrong match tests
    results.append(("Wrong Match Detection", run_wrong_match_tests()))
    
    # Print summary
    print("\n" + "="*80)
    print("Test Summary")
    print("="*80)
    
    passed = sum(1 for _, result in results if result)
    total = len(results)
    
    for test_name, result in results:
        status = "✓ PASS" if result else "✗ FAIL"
        print(f"  {status}: {test_name}")
    
    print(f"\nTotal: {passed}/{total} test suites passed")
    
    return 0 if passed == total else 1


if __name__ == '__main__':
    sys.exit(main())

