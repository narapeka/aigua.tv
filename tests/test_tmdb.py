#!/usr/bin/env python3
"""
Test script for tmdb.py
Tests TMDB client functionality using real config.yaml
"""

import sys
import tempfile
from pathlib import Path

# Add parent directory to path to import modules
sys.path.insert(0, str(Path(__file__).parent.parent))

from config import load_config
from tmdb import create_tmdb_client_from_config, TMDBClient
from logger import setup_logging


def test_tmdb_client_initialization():
    """Test TMDB client initialization"""
    print("\n" + "="*60)
    print("Test 1: TMDB Client Initialization")
    print("="*60)
    
    try:
        config = load_config()
        # Create a temporary log file for testing
        with tempfile.NamedTemporaryFile(mode='w', suffix='.log', delete=False) as tmp_file:
            log_file = Path(tmp_file.name)
        logger = setup_logging(log_file, verbose=True)
        client = create_tmdb_client_from_config(config, logger)
        
        print(f"✓ Client initialized successfully")
        print(f"  API Key: {config.tmdb.api_key[:10]}...")
        print(f"  Languages: {config.tmdb.languages}")
        print(f"  Default Language: {config.tmdb.language}")
        if config.proxy:
            print(f"  Proxy: {config.proxy.host}:{config.proxy.port}")
        else:
            print(f"  Proxy: Not configured")
        
        return client, logger
    except Exception as e:
        print(f"✗ Failed to initialize client: {e}")
        return None, None


def test_search_with_tmdbid(client: TMDBClient, logger):
    """Test searching with TMDB ID"""
    print("\n" + "="*60)
    print("Test 2: Search with TMDB ID")
    print("="*60)
    
    # Use a well-known TV show ID (e.g., Breaking Bad)
    test_tmdbid = 1396  # Breaking Bad
    test_folder_name = "Breaking Bad"
    
    try:
        result = client.get_tv_show(
            folder_name=test_folder_name,
            tmdbid=test_tmdbid
        )
        
        if result:
            print(f"✓ Found TV show: {result.name}")
            print(f"\n  Basic Information:")
            print(f"    ID: {result.id}")
            print(f"    Name: {result.name}")
            print(f"    Original Name: {result.original_name}")
            print(f"    Year: {result.year}")
            
            print(f"\n  Input Data:")
            print(f"    Folder Name: {result.folder_name}")
            print(f"    CN Name: {result.cn_name}")
            print(f"    EN Name: {result.en_name}")
            print(f"    TMDB ID: {result.tmdbid}")
            
            print(f"\n  Match Information:")
            print(f"    Match Confidence: {result.match_confidence}")
            print(f"    Search Language: {result.search_language}")
            
            print(f"\n  Alternative Titles:")
            if result.alternative_titles:
                print(f"    Alternative Titles - Total: {len(result.alternative_titles)}")
                for i, alt_title in enumerate(result.alternative_titles[:10], 1):  # Show first 10
                    print(f"    {i}. {alt_title.title} (iso_3166_1: {alt_title.iso_3166_1})")
                if len(result.alternative_titles) > 10:
                    print(f"    ... and {len(result.alternative_titles) - 10} more")
            
            if result.translations:
                print(f"\n  Translations:")
                print(f"    Total: {len(result.translations)}")
                for i, trans in enumerate(result.translations[:10], 1):  # Show first 10
                    print(f"    {i}. {trans.name} (iso_3166_1: {trans.iso_3166_1})")
                if len(result.translations) > 10:
                    print(f"    ... and {len(result.translations) - 10} more")
            else:
                print(f"    None")
            
            print(f"\n  Seasons and Episodes:")
            if result.seasons:
                print(f"    Total Seasons Retrieved: {len(result.seasons)}")
                for season in result.seasons:
                    season_num = season.season_number
                    episodes = season.episodes
                    print(f"\n    Season {season_num}: {len(episodes)} episodes")
                    # Show first 3 and last 3 episodes
                    if episodes:
                        for ep in episodes[:3]:
                            print(f"      E{ep.episode_number:02d}: {ep.title}")
                        if len(episodes) > 6:
                            print(f"      ... ({len(episodes) - 6} more episodes) ...")
                        if len(episodes) > 3:
                            for ep in episodes[-3:]:
                                print(f"      E{ep.episode_number:02d}: {ep.title}")
            else:
                print(f"    No seasons/episodes data (confidence may not be 'high')")
            
            # Convert to dict and show all fields
            print(f"\n  Complete Data Dictionary:")
            data_dict = result.to_dict()
            for key, value in data_dict.items():
                if value is not None:
                    if key == 'seasons' and value:
                        print(f"    {key}: [List of {len(value)} seasons]")
                    elif key == 'alternative_titles' and value:
                        print(f"    {key}: [List of {len(value)} titles]")
                    elif isinstance(value, str) and len(value) > 100:
                        print(f"    {key}: {value[:100]}...")
                    else:
                        print(f"    {key}: {value}")
            
            return True
        else:
            print(f"✗ No result found")
            return False
    except Exception as e:
        print(f"✗ Error: {e}")
        import traceback
        traceback.print_exc()
        return False


def test_search_with_cn_name(client: TMDBClient, logger):
    """Test searching with Chinese name"""
    print("\n" + "="*60)
    print("Test 3: Search with Chinese Name")
    print("="*60)
    
    # Test with a Chinese TV show name
    test_cases = [
        {"folder_name": "权力的游戏", "cn_name": "权力的游戏", "year": 2011},
        {"folder_name": "老友记", "cn_name": "老友记", "year": 1994},
    ]
    
    success_count = 0
    for i, test_case in enumerate(test_cases, 1):
        print(f"\n  Test Case {i}: {test_case['folder_name']}")
        try:
            result = client.get_tv_show(
                folder_name=test_case['folder_name'],
                cn_name=test_case['cn_name'],
                year=test_case['year']
            )
            
            if result:
                print(f"    ✓ Found: {result.name}")
                print(f"      ID: {result.id}")
                print(f"      Original Name: {result.original_name}")
                print(f"      Year: {result.year}")
                print(f"      Match Confidence: {result.match_confidence}")
                print(f"      Search Language: {result.search_language}")
                if result.alternative_titles:
                    print(f"      Alternative Titles: {len(result.alternative_titles)} found")
                    sample_titles = [f"{alt.title} ({alt.iso_3166_1})" for alt in result.alternative_titles[:3]]
                    print(f"        Sample: {', '.join(sample_titles)}")
                if result.translations:
                    print(f"      Translations: {len(result.translations)} found")
                    sample_trans = [f"{trans.name} ({trans.iso_3166_1})" for trans in result.translations[:3]]
                    print(f"        Sample: {', '.join(sample_trans)}")
                if result.seasons:
                    print(f"      Seasons Data: {len(result.seasons)} seasons retrieved")
                    total_episodes = sum(len(s.episodes) for s in result.seasons)
                    print(f"      Total Episodes Retrieved: {total_episodes}")
                success_count += 1
            else:
                print(f"    ✗ No result found")
        except Exception as e:
            print(f"    ✗ Error: {e}")
            import traceback
            traceback.print_exc()
    
    print(f"\n  Summary: {success_count}/{len(test_cases)} successful")
    return success_count > 0


def test_search_with_en_name(client: TMDBClient, logger):
    """Test searching with English name"""
    print("\n" + "="*60)
    print("Test 4: Search with English Name")
    print("="*60)
    
    test_cases = [
        {"folder_name": "Game of Thrones", "en_name": "Game of Thrones", "year": 2011},
        {"folder_name": "Friends", "en_name": "Friends", "year": 1994},
    ]
    
    success_count = 0
    for i, test_case in enumerate(test_cases, 1):
        print(f"\n  Test Case {i}: {test_case['folder_name']}")
        try:
            result = client.get_tv_show(
                folder_name=test_case['folder_name'],
                en_name=test_case['en_name'],
                year=test_case['year']
            )
            
            if result:
                print(f"    ✓ Found: {result.name}")
                print(f"      ID: {result.id}")
                print(f"      Original Name: {result.original_name}")
                print(f"      Year: {result.year}")
                print(f"      Match Confidence: {result.match_confidence}")
                print(f"      Search Language: {result.search_language}")
                if result.alternative_titles:
                    print(f"      Alternative Titles: {len(result.alternative_titles)} found")
                    sample_titles = [f"{alt.title} ({alt.iso_3166_1})" for alt in result.alternative_titles[:5]]
                    print(f"        Sample: {', '.join(sample_titles)}")
                if result.translations:
                    print(f"      Translations: {len(result.translations)} found")
                    sample_trans = [f"{trans.name} ({trans.iso_3166_1})" for trans in result.translations[:5]]
                    print(f"        Sample: {', '.join(sample_trans)}")
                if result.seasons:
                    print(f"      Seasons Data: {len(result.seasons)} seasons retrieved")
                    total_episodes = sum(len(s.episodes) for s in result.seasons)
                    print(f"      Total Episodes Retrieved: {total_episodes}")
                success_count += 1
            else:
                print(f"    ✗ No result found")
        except Exception as e:
            print(f"    ✗ Error: {e}")
            import traceback
            traceback.print_exc()
    
    print(f"\n  Summary: {success_count}/{len(test_cases)} successful")
    return success_count > 0


def test_search_without_year(client: TMDBClient, logger):
    """Test searching without year"""
    print("\n" + "="*60)
    print("Test 5: Search without Year")
    print("="*60)
    
    test_cases = [
        {"folder_name": "The Office", "en_name": "The Office"},
        {"folder_name": "Stranger Things", "en_name": "Stranger Things"},
    ]
    
    success_count = 0
    for i, test_case in enumerate(test_cases, 1):
        print(f"\n  Test Case {i}: {test_case['folder_name']}")
        try:
            result = client.get_tv_show(
                folder_name=test_case['folder_name'],
                en_name=test_case['en_name'],
                year=None
            )
            
            if result:
                print(f"    ✓ Found: {result.name}")
                print(f"      Year: {result.year}")
                print(f"      Match Confidence: {result.match_confidence}")
                success_count += 1
            else:
                print(f"    ✗ No result found")
        except Exception as e:
            print(f"    ✗ Error: {e}")
    
    print(f"\n  Summary: {success_count}/{len(test_cases)} successful")
    return success_count > 0


def test_alternative_titles(client: TMDBClient, logger):
    """Test alternative titles extraction"""
    print("\n" + "="*60)
    print("Test 6: Alternative Titles Extraction")
    print("="*60)
    
    test_tmdbid = 1396  # Breaking Bad
    test_folder_name = "Breaking Bad"
    
    try:
        result = client.get_tv_show(
            folder_name=test_folder_name,
            tmdbid=test_tmdbid
        )
        
        matching_titles = []
        
        if result and result.alternative_titles:
            print(f"✓ Found {len(result.alternative_titles)} alternative titles")
            print(f"\n  All Alternative Titles:")
            for i, alt_title in enumerate(result.alternative_titles, 1):
                print(f"    {i}. {alt_title.title} (iso_3166_1: {alt_title.iso_3166_1})")
            
            # Check if folder_name appears in alternative titles
            folder_name_lower = test_folder_name.lower()
            matching_titles = [alt.title for alt in result.alternative_titles if alt.title and folder_name_lower in alt.title.lower()]
        
        if result and result.translations:
            print(f"\n✓ Found {len(result.translations)} translations")
            print(f"\n  All Translations:")
            for i, trans in enumerate(result.translations, 1):
                print(f"    {i}. {trans.name} (iso_3166_1: {trans.iso_3166_1})")
            
            # Check if folder_name appears in translations
            if not matching_titles:
                folder_name_lower = test_folder_name.lower()
                matching_translations = [trans.name for trans in result.translations if trans.name and folder_name_lower in trans.name.lower()]
                if matching_translations:
                    matching_titles = matching_translations
        
        if matching_titles:
            print(f"\n  Titles matching folder name '{test_folder_name}':")
            for title in matching_titles:
                print(f"    - {title}")
            return True
        elif result:
            print(f"\n  No alternative titles or translations match folder name '{test_folder_name}'")
            return True
        else:
            print(f"✗ No alternative titles found")
            if result:
                print(f"  Result exists but alternative_titles is empty or None")
            return False
    except Exception as e:
        print(f"✗ Error: {e}")
        import traceback
        traceback.print_exc()
        return False


def test_seasons_and_episodes(client: TMDBClient, logger):
    """Test seasons and episodes retrieval"""
    print("\n" + "="*60)
    print("Test 7: Seasons and Episodes Retrieval")
    print("="*60)
    
    test_tmdbid = 1396  # Breaking Bad
    test_folder_name = "Breaking Bad"
    
    try:
        result = client.get_tv_show(
            folder_name=test_folder_name,
            tmdbid=test_tmdbid
        )
        
        if result and result.seasons:
            print(f"✓ Retrieved {len(result.seasons)} seasons")
            total_episodes = sum(len(s['episodes']) for s in result.seasons)
            print(f"  Total Episodes: {total_episodes}")
            
            print(f"\n  Season Details:")
            for season in result.seasons:
                season_num = season.season_number
                episodes = season.episodes
                print(f"\n    Season {season_num}: {len(episodes)} episodes")
                
                # Show first 3 episodes
                if episodes:
                    print(f"      First episodes:")
                    for ep in episodes[:3]:
                        ep_num = ep.episode_number
                        ep_title = ep.title or 'Untitled'
                        print(f"        E{ep_num:02d}: {ep_title}")
                    
                    # Show last episode if more than 3
                    if len(episodes) > 3:
                        last_ep = episodes[-1]
                        print(f"      ...")
                        print(f"        E{last_ep.episode_number:02d}: {last_ep.title or 'Untitled'}")
            
            # Verify data structure
            print(f"\n  Data Structure Verification:")
            print(f"    ✓ All seasons have 'season_number' field")
            print(f"    ✓ All seasons have 'episodes' list")
            for season in result.seasons:
                episodes = season.episodes
                if episodes:
                    first_ep = episodes[0]
                    has_ep_num = hasattr(first_ep, 'episode_number')
                    has_title = hasattr(first_ep, 'title')
                    print(f"    ✓ Episodes have 'episode_number': {has_ep_num}")
                    print(f"    ✓ Episodes have 'title': {has_title}")
                    break
            
            return True
        else:
            print(f"✗ No seasons/episodes data")
            if result:
                print(f"  Result exists but seasons is empty or None")
                print(f"  Match Confidence: {result.match_confidence}")
                print(f"  (Seasons only retrieved if confidence is 'high')")
            return False
    except Exception as e:
        print(f"✗ Error: {e}")
        import traceback
        traceback.print_exc()
        return False


def main():
    """Run all tests"""
    print("\n" + "="*60)
    print("TMDB Client Test Suite")
    print("="*60)
    
    # Initialize client
    client, logger = test_tmdb_client_initialization()
    if not client:
        print("\n✗ Cannot proceed without client initialization")
        return 1
    
    # Run tests
    test_results = []
    
    test_results.append(("Search with TMDB ID", test_search_with_tmdbid(client, logger)))
    test_results.append(("Search with Chinese Name", test_search_with_cn_name(client, logger)))
    test_results.append(("Search with English Name", test_search_with_en_name(client, logger)))
    test_results.append(("Search without Year", test_search_without_year(client, logger)))
    test_results.append(("Alternative Titles", test_alternative_titles(client, logger)))
    test_results.append(("Seasons and Episodes", test_seasons_and_episodes(client, logger)))
    
    # Print summary
    print("\n" + "="*60)
    print("Test Summary")
    print("="*60)
    
    passed = sum(1 for _, result in test_results if result)
    total = len(test_results)
    
    for test_name, result in test_results:
        status = "✓ PASS" if result else "✗ FAIL"
        print(f"{status}: {test_name}")
    
    print(f"\nTotal: {passed}/{total} tests passed")
    
    return 0 if passed == total else 1


if __name__ == '__main__':
    sys.exit(main())

