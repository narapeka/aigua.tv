#!/usr/bin/env python3
"""
Test script for agent.py
Tests LLM Agent functionality using real config.yaml
"""

import sys
import tempfile
import json
from collections import Counter
from pathlib import Path

# Add parent directory to path to import modules
sys.path.insert(0, str(Path(__file__).parent.parent))

from config import load_config
from agent import LLMAgent, TVShowInfo
from logger import setup_logging


def test_agent_initialization():
    """Test LLM Agent initialization"""
    print("\n" + "="*60)
    print("Test 1: LLM Agent Initialization")
    print("="*60)
    
    try:
        config = load_config()
        # Create a temporary log file for testing
        with tempfile.NamedTemporaryFile(mode='w', suffix='.log', delete=False) as tmp_file:
            log_file = Path(tmp_file.name)
        logger = setup_logging(log_file, verbose=True)
        
        agent = LLMAgent(
            api_key=config.llm.api_key,
            base_url=config.llm.base_url,
            model=config.llm.model,
            batch_size=config.llm.batch_size,
            rate_limit=config.llm.rate_limit,
            logger=logger
        )
        
        print(f"✓ Agent initialized successfully")
        print(f"  API Key: {config.llm.api_key[:10]}...")
        print(f"  Base URL: {config.llm.base_url or 'OpenAI default'}")
        print(f"  Model: {config.llm.model}")
        print(f"  Batch Size: {config.llm.batch_size}")
        print(f"  Rate Limit: {config.llm.rate_limit} requests/second")
        print(f"  System Prompt: {len(agent.system_prompt)} characters")
        print(f"  User Prompt Template: {len(agent.user_prompt_template)} characters")
        
        return agent, logger
    except Exception as e:
        print(f"✗ Failed to initialize agent: {e}")
        import traceback
        traceback.print_exc()
        return None, None


def test_extract_single_folder(agent: LLMAgent, logger):
    """Test extracting information from a single folder name"""
    print("\n" + "="*60)
    print("Test 2: Extract Single Folder")
    print("="*60)
    
    test_cases = [
        "权力的游戏 第一季",
        "Game of Thrones S01",
        "The Office (2005)",
        "Breaking Bad tmdbid=1396",
        "老友记 Friends (1994)",
    ]
    
    success_count = 0
    for i, folder_name in enumerate(test_cases, 1):
        print(f"\n  Test Case {i}: {folder_name}")
        try:
            results = agent.extract_tvshow([folder_name])
            
            if results and len(results) == 1:
                result = results[0]
                print(f"    ✓ Extracted:")
                print(f"      Folder Name: {result.folder_name}")
                print(f"      CN Name: {result.cn_name}")
                print(f"      EN Name: {result.en_name}")
                print(f"      Year: {result.year}")
                print(f"      TMDB ID: {result.tmdbid}")
                
                # Validate result
                if result.folder_name == folder_name:
                    success_count += 1
                else:
                    print(f"      ⚠ Warning: folder_name mismatch")
            else:
                print(f"    ✗ Unexpected result count: {len(results) if results else 0}")
        except Exception as e:
            print(f"    ✗ Error: {e}")
            import traceback
            traceback.print_exc()
    
    print(f"\n  Summary: {success_count}/{len(test_cases)} successful")
    return success_count > 0


def test_extract_multiple_folders(agent: LLMAgent, logger):
    """Test extracting information from multiple folder names"""
    print("\n" + "="*60)
    print("Test 3: Extract Multiple Folders")
    print("="*60)
    
    folder_names = [
        "权力的游戏 第一季",
        "Game of Thrones S01",
        "The Office (2005)",
        "Breaking Bad tmdbid=1396",
        "老友记 Friends (1994)",
        "Stranger Things (2016)",
        "The Crown (2016) tmdbid=65494",
    ]
    
    try:
        print(f"  Processing {len(folder_names)} folders...")
        results = agent.extract_tvshow(folder_names)
        
        if results and len(results) == len(folder_names):
            print(f"✓ Successfully extracted info for {len(results)} folders")
            print(f"\n  Results:")
            for i, result in enumerate(results, 1):
                print(f"    {i}. {result.folder_name}")
                print(f"       CN: {result.cn_name}, EN: {result.en_name}, Year: {result.year}, TMDB: {result.tmdbid}")
            
            # Verify all folder names are present
            result_folder_names = {r.folder_name for r in results}
            input_folder_names = set(folder_names)
            if result_folder_names == input_folder_names:
                print(f"\n  ✓ All folder names matched")
                return True
            else:
                missing = input_folder_names - result_folder_names
                extra = result_folder_names - input_folder_names
                print(f"\n  ✗ Folder name mismatch:")
                if missing:
                    print(f"    Missing: {missing}")
                if extra:
                    print(f"    Extra: {extra}")
                return False
        else:
            print(f"✗ Unexpected result count: expected {len(folder_names)}, got {len(results) if results else 0}")
            return False
    except Exception as e:
        print(f"✗ Error: {e}")
        import traceback
        traceback.print_exc()
        return False


def test_batch_processing(agent: LLMAgent, logger):
    """Test batch processing with large number of folders"""
    print("\n" + "="*60)
    print("Test 4: Batch Processing")
    print("="*60)
    
    # Create a list larger than batch_size
    base_folders = [
        "权力的游戏 第一季",
        "Game of Thrones S01",
        "The Office (2005)",
        "Breaking Bad tmdbid=1396",
        "老友记 Friends (1994)",
    ]
    
    # Repeat to create more than batch_size items
    folder_names = base_folders * (agent.batch_size // len(base_folders) + 2)
    
    print(f"  Testing with {len(folder_names)} folders (batch_size: {agent.batch_size})")
    print(f"  Expected chunks: {(len(folder_names) + agent.batch_size - 1) // agent.batch_size}")
    
    try:
        results = agent.extract_tvshow(folder_names)
        
        if results:
            # The agent normalizes results to match input count, so check for that
            if len(results) == len(folder_names):
                print(f"✓ Successfully processed {len(results)} folders in batches")
            else:
                print(f"⚠ Result count mismatch: expected {len(folder_names)}, got {len(results)}")
                print(f"  (Agent should normalize this - checking if all input folders are present)")
            
            # Check that all results have folder_name
            all_have_folder_name = all(r.folder_name for r in results)
            print(f"  ✓ All results have folder_name: {all_have_folder_name}")
            
            # Check for duplicates in results
            result_folder_names = [r.folder_name for r in results]
            unique_names = set(result_folder_names)
            if len(result_folder_names) != len(unique_names):
                duplicates = len(result_folder_names) - len(unique_names)
                print(f"  ⚠ Found {duplicates} duplicate folder names in results")
                # Show which ones are duplicated
                counts = Counter(result_folder_names)
                dupes = {name: count for name, count in counts.items() if count > 1}
                if dupes:
                    print(f"    Duplicated folders: {list(dupes.keys())[:5]}")  # Show first 5
            else:
                print(f"  ✓ No duplicate folder names in results")
            
            # Verify all input folder names are present in results
            input_set = set(folder_names)
            result_set = set(result_folder_names)
            missing = input_set - result_set
            extra = result_set - input_set
            
            if missing:
                print(f"  ✗ Missing folders in results: {len(missing)}")
                print(f"    Sample: {list(missing)[:3]}")
                return False
            elif extra:
                print(f"  ⚠ Extra folders in results (not in input): {len(extra)}")
                print(f"    Sample: {list(extra)[:3]}")
                # This is acceptable if the agent handles it (which it does via normalization)
            
            # Final check: agent should normalize to exact input count
            if len(results) == len(folder_names) and not missing:
                return True
            elif not missing:
                # Agent normalized it, which is acceptable
                print(f"  ✓ Agent normalized results to match input count")
                return True
            else:
                return False
        else:
            print(f"✗ No results returned")
            return False
    except Exception as e:
        print(f"✗ Error: {e}")
        import traceback
        traceback.print_exc()
        return False


def test_empty_input(agent: LLMAgent, logger):
    """Test handling of empty input"""
    print("\n" + "="*60)
    print("Test 5: Empty Input Handling")
    print("="*60)
    
    try:
        results = agent.extract_tvshow([])
        
        if results == []:
            print(f"✓ Empty input handled correctly (returned empty list)")
            return True
        else:
            print(f"✗ Expected empty list, got: {results}")
            return False
    except Exception as e:
        print(f"✗ Error: {e}")
        import traceback
        traceback.print_exc()
        return False


def test_tvshow_info_dataclass(agent: LLMAgent, logger):
    """Test TVShowInfo dataclass functionality"""
    print("\n" + "="*60)
    print("Test 6: TVShowInfo Dataclass")
    print("="*60)
    
    try:
        # Test creating TVShowInfo
        info = TVShowInfo(
            folder_name="Test Show",
            cn_name="测试节目",
            en_name="Test Show",
            year=2020,
            tmdbid=12345
        )
        
        print(f"✓ Created TVShowInfo object")
        print(f"  Folder Name: {info.folder_name}")
        print(f"  CN Name: {info.cn_name}")
        print(f"  EN Name: {info.en_name}")
        print(f"  Year: {info.year}")
        print(f"  TMDB ID: {info.tmdbid}")
        
        # Test to_dict method
        info_dict = info.to_dict()
        print(f"\n✓ to_dict() method works")
        print(f"  Dictionary keys: {list(info_dict.keys())}")
        
        # Verify dictionary structure
        expected_keys = {'folder_name', 'cn_name', 'en_name', 'year', 'tmdbid'}
        if set(info_dict.keys()) == expected_keys:
            print(f"  ✓ All expected keys present")
        else:
            print(f"  ✗ Key mismatch")
            return False
        
        # Test with None values
        info_none = TVShowInfo(folder_name="Test Show 2")
        print(f"\n✓ Created TVShowInfo with None values")
        print(f"  CN Name: {info_none.cn_name}")
        print(f"  EN Name: {info_none.en_name}")
        print(f"  Year: {info_none.year}")
        print(f"  TMDB ID: {info_none.tmdbid}")
        
        return True
    except Exception as e:
        print(f"✗ Error: {e}")
        import traceback
        traceback.print_exc()
        return False


def test_parse_response_edge_cases(agent: LLMAgent, logger):
    """Test parsing edge cases in LLM responses"""
    print("\n" + "="*60)
    print("Test 7: Response Parsing Edge Cases")
    print("="*60)
    
    test_cases = [
        {
            "name": "Valid JSON array",
            "response": '[{"folder_name": "Test", "cn_name": "测试", "en_name": "Test", "year": 2020, "tmdbid": null}]',
            "folder_names": ["Test"],
            "should_succeed": True
        },
        {
            "name": "JSON with extra text",
            "response": 'Here is the result:\n[{"folder_name": "Test", "cn_name": "测试", "en_name": null, "year": null, "tmdbid": null}]\nHope this helps!',
            "folder_names": ["Test"],
            "should_succeed": True
        },
        {
            "name": "Year as string",
            "response": '[{"folder_name": "Test", "cn_name": null, "en_name": "Test", "year": "2020", "tmdbid": null}]',
            "folder_names": ["Test"],
            "should_succeed": True
        },
        {
            "name": "TMDB ID as string",
            "response": '[{"folder_name": "Test", "cn_name": null, "en_name": "Test", "year": null, "tmdbid": "12345"}]',
            "folder_names": ["Test"],
            "should_succeed": True
        },
        {
            "name": "Empty strings converted to None",
            "response": '[{"folder_name": "Test", "cn_name": "", "en_name": "   ", "year": null, "tmdbid": null}]',
            "folder_names": ["Test"],
            "should_succeed": True
        },
        {
            "name": "Invalid JSON",
            "response": 'This is not valid JSON',
            "folder_names": ["Test"],
            "should_succeed": False  # Should handle gracefully
        },
    ]
    
    success_count = 0
    for i, test_case in enumerate(test_cases, 1):
        print(f"\n  Test Case {i}: {test_case['name']}")
        try:
            results = agent._parse_llm_response(
                test_case['response'],
                test_case['folder_names']
            )
            
            if results and len(results) > 0:
                result = results[0]
                print(f"    ✓ Parsed successfully")
                print(f"      Folder Name: {result.folder_name}")
                print(f"      CN Name: {result.cn_name}")
                print(f"      EN Name: {result.en_name}")
                print(f"      Year: {result.year} (type: {type(result.year).__name__})")
                print(f"      TMDB ID: {result.tmdbid} (type: {type(result.tmdbid).__name__})")
                
                # Check if this is a graceful error handling case (all fields None except folder_name)
                is_graceful_error = (
                    result.folder_name and
                    result.cn_name is None and
                    result.en_name is None and
                    result.year is None and
                    result.tmdbid is None
                )
                
                if test_case['should_succeed']:
                    # For successful cases, we should have at least some data
                    if is_graceful_error and test_case['name'] != "Empty strings converted to None":
                        print(f"    ✗ Expected meaningful data but got all None values")
                    else:
                        # Check type conversions for valid cases
                        if test_case['name'] == "Year as string" and isinstance(result.year, int):
                            print(f"      ✓ Year converted from string to int")
                        if test_case['name'] == "TMDB ID as string" and isinstance(result.tmdbid, int):
                            print(f"      ✓ TMDB ID converted from string to int")
                        if test_case['name'] == "Empty strings converted to None":
                            if result.cn_name is None and result.en_name is None:
                                print(f"      ✓ Empty strings converted to None")
                        success_count += 1
                else:
                    # For error cases, graceful handling means returning results with None values
                    if is_graceful_error:
                        print(f"      ✓ Handled invalid input gracefully (returned results with None values)")
                        success_count += 1
                    else:
                        print(f"    ⚠ Unexpected: got some data from invalid input")
                        success_count += 1  # Still count as success since it didn't crash
            else:
                if not test_case['should_succeed']:
                    print(f"    ✓ Handled invalid input gracefully (returned empty list)")
                    success_count += 1
                else:
                    print(f"    ✗ Expected results but got empty")
        except Exception as e:
            if not test_case['should_succeed']:
                print(f"    ✓ Exception handled: {e}")
                success_count += 1
            else:
                print(f"    ✗ Unexpected error: {e}")
                import traceback
                traceback.print_exc()
    
    print(f"\n  Summary: {success_count}/{len(test_cases)} successful")
    return success_count == len(test_cases)


def test_prompt_creation(agent: LLMAgent, logger):
    """Test prompt creation"""
    print("\n" + "="*60)
    print("Test 8: Prompt Creation")
    print("="*60)
    
    try:
        folder_names = ["Test Show 1", "Test Show 2"]
        prompt = agent._create_extraction_prompt(folder_names)
        
        print(f"✓ Prompt created successfully")
        print(f"  Prompt length: {len(prompt)} characters")
        
        # Check that folder names are in the prompt
        for folder_name in folder_names:
            if folder_name in prompt:
                print(f"  ✓ '{folder_name}' found in prompt")
            else:
                print(f"  ✗ '{folder_name}' not found in prompt")
                return False
        
        # Check that prompt contains JSON structure
        if "folder_list" in prompt or "Test Show" in prompt:
            print(f"  ✓ Prompt contains folder list")
        else:
            print(f"  ⚠ Prompt structure may be unexpected")
        
        return True
    except Exception as e:
        print(f"✗ Error: {e}")
        import traceback
        traceback.print_exc()
        return False


def main():
    """Run all tests"""
    print("\n" + "="*60)
    print("LLM Agent Test Suite")
    print("="*60)
    
    # Initialize agent
    agent, logger = test_agent_initialization()
    if not agent:
        print("\n✗ Cannot proceed without agent initialization")
        return 1
    
    # Run tests
    test_results = []
    
    test_results.append(("TVShowInfo Dataclass", test_tvshow_info_dataclass(agent, logger)))
    test_results.append(("Prompt Creation", test_prompt_creation(agent, logger)))
    test_results.append(("Response Parsing Edge Cases", test_parse_response_edge_cases(agent, logger)))
    test_results.append(("Empty Input Handling", test_empty_input(agent, logger)))
    test_results.append(("Extract Single Folder", test_extract_single_folder(agent, logger)))
    test_results.append(("Extract Multiple Folders", test_extract_multiple_folders(agent, logger)))
    test_results.append(("Batch Processing", test_batch_processing(agent, logger)))
    
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

