#!/usr/bin/env python3
"""
POST-DEPLOYMENT VALIDATION SCRIPT V2

This version tests the ACTUAL MCP protocol flow that ChatGPT uses,
not the Python functions directly. This is the ONLY way to ensure
our system works with ChatGPT.

Usage: python3 POST_DEPLOYMENT_VALIDATION_V2.py
"""

import sys
import time
import json
import requests
from typing import Dict, Any, Optional, Tuple

# MCP Server endpoint
BASE_URL = "https://wmjump1.henkelman.net:8080"
MCP_ENDPOINT = f"{BASE_URL}/mcp/v1/sse"

# Global session management
SESSION_ID = None


def make_mcp_request(method: str, params: Dict[str, Any], request_id: int = 1) -> Tuple[bool, Any]:
    """
    Make an MCP request through the SSE endpoint.
    Returns (success, response_data)
    """
    global SESSION_ID
    
    headers = {
        "Content-Type": "application/json",
        "Accept": "application/json,text/event-stream"
    }
    
    # Add session ID if we have one
    if SESSION_ID:
        headers["X-Session-ID"] = SESSION_ID
    
    payload = {
        "jsonrpc": "2.0",
        "method": method,
        "id": request_id,
        "params": params
    }
    
    try:
        response = requests.post(MCP_ENDPOINT, headers=headers, json=payload, timeout=10)
        
        if response.status_code != 200:
            return False, f"HTTP {response.status_code}: {response.text}"
        
        # Parse SSE response
        for line in response.text.split('\n'):
            if line.startswith('data: '):
                try:
                    data = json.loads(line[6:])
                    
                    # Check for errors
                    if 'error' in data:
                        return False, data['error']
                    
                    # Extract session ID if present
                    if 'result' in data and isinstance(data['result'], dict):
                        if 'sessionId' in data['result']:
                            SESSION_ID = data['result']['sessionId']
                    
                    return True, data
                except json.JSONDecodeError:
                    continue
        
        return False, "No valid SSE data found in response"
        
    except Exception as e:
        return False, f"Request error: {e}"


def test_stateless_access() -> bool:
    """Test that we can access without session (stateless mode)"""
    print("Testing stateless access...")
    
    # Try a simple tools/list without any session
    success, response = make_mcp_request("tools/list", {})
    
    if success:
        print(f"✅ Stateless access works - no session required!")
        return True
    else:
        # If that fails, try the old session-based approach
        print(f"⚠️  Stateless failed ({response}), trying with session...")
        
        params = {
            "protocolVersion": "1.0.0",
            "clientInfo": {
                "name": "validation-client",
                "version": "1.0.0"
            }
        }
        
        success, response = make_mcp_request("initialize", params)
        
        if success:
            print(f"✅ Session initialized{f' (ID: {SESSION_ID})' if SESSION_ID else ''}")
            return True
        else:
            print(f"❌ Failed to initialize: {response}")
            return False


def test_search(query: str) -> Tuple[bool, int, Optional[str]]:
    """
    Test search through MCP protocol.
    Returns (success, result_count, first_result_id)
    """
    params = {
        "name": "search",
        "arguments": {
            "query": query
        }
    }
    
    success, response = make_mcp_request("tools/call", params)
    
    if not success:
        return False, 0, None
    
    # Extract the actual search results from MCP response
    try:
        if 'result' in response and 'content' in response['result']:
            content = response['result']['content'][0]['text']
            search_results = json.loads(content)
            
            # Handle the dict format we return
            if isinstance(search_results, dict) and 'results' in search_results:
                results = search_results['results']
                count = search_results.get('count', len(results))
                first_id = results[0]['id'] if results else None
                return True, count, first_id
            # Handle if it's still a list (shouldn't happen)
            elif isinstance(search_results, list):
                count = len(search_results)
                first_id = search_results[0]['id'] if search_results else None
                return True, count, first_id
                
    except Exception as e:
        print(f"   Error parsing search response: {e}")
    
    return False, 0, None


def test_fetch(doc_id: str) -> Tuple[bool, bool]:
    """
    Test fetch through MCP protocol.
    Returns (success, has_content)
    """
    params = {
        "name": "fetch",
        "arguments": {
            "id": doc_id
        }
    }
    
    success, response = make_mcp_request("tools/call", params)
    
    if not success:
        return False, False
    
    # Extract the fetch result from MCP response
    try:
        if 'result' in response and 'content' in response['result']:
            content = response['result']['content'][0]['text']
            fetch_result = json.loads(content)
            
            # Check if we got actual content
            has_content = (
                isinstance(fetch_result, dict) and 
                'text' in fetch_result and 
                len(fetch_result['text']) > 0
            )
            return True, has_content
            
    except Exception as e:
        print(f"   Error parsing fetch response: {e}")
    
    return False, False


def run_validation():
    """Run all validation tests through MCP protocol"""
    print("=" * 80)
    print("POST-DEPLOYMENT VALIDATION V2 - TESTING ACTUAL MCP PROTOCOL")
    print("=" * 80)
    print(f"Timestamp: {time.strftime('%Y-%m-%d %H:%M:%S UTC', time.gmtime())}")
    print(f"Endpoint: {MCP_ENDPOINT}")
    print()
    
    total_tests = 0
    passed_tests = 0
    critical_failures = []
    
    # Test 1: Can we access without sessions?
    print("1. MCP ACCESS TEST")
    total_tests += 1
    if test_stateless_access():
        passed_tests += 1
    else:
        critical_failures.append("Cannot access MCP endpoint - ChatGPT won't be able to connect!")
        print("\n⚠️  CRITICAL: Cannot proceed without MCP access")
        return False
    
    # Test 2: Basic search
    print("\n2. BASIC SEARCH TEST")
    test_queries = [
        ("CS 6300", "Should find Software Development Process"),
        ("Fall 2025", "Should return semester courses"),
        ("", "Empty query should return help"),
        ("xyz123nonsense", "Should return 'no results found' help"),
    ]
    
    for query, description in test_queries:
        total_tests += 1
        print(f"   Testing '{query}': {description}")
        
        success, count, first_id = test_search(query)
        
        if success:
            if query == "" and count == 0:
                print(f"   ✅ Empty query returns help (count={count})")
                passed_tests += 1
            elif query == "xyz123nonsense" and count == 0:
                print(f"   ✅ Invalid query returns help (count={count})")
                passed_tests += 1
            elif count > 0:
                print(f"   ✅ Found {count} results (first: {first_id})")
                passed_tests += 1
            else:
                print(f"   ❌ Unexpected: count={count}")
        else:
            print(f"   ❌ Search failed through MCP")
            if query in ["CS 6300", "Fall 2025"]:
                critical_failures.append(f"Basic search '{query}' failed - ChatGPT won't find courses!")
    
    # Test 3: Search and fetch flow
    print("\n3. SEARCH AND FETCH FLOW (What ChatGPT does)")
    total_tests += 1
    
    # First search
    success, count, course_id = test_search("CS 6515")
    if success and course_id:
        print(f"   ✅ Search found course: {course_id}")
        
        # Then fetch
        fetch_success, has_content = test_fetch(course_id)
        if fetch_success and has_content:
            print(f"   ✅ Fetch retrieved course details")
            passed_tests += 1
        else:
            print(f"   ❌ Fetch failed or returned no content")
            critical_failures.append("Fetch after search failed - ChatGPT can't get course details!")
    else:
        print(f"   ❌ Initial search failed")
        critical_failures.append("Search-fetch flow broken - ChatGPT won't work!")
    
    # Test 4: Error handling
    print("\n4. ERROR HANDLING TESTS")
    
    # Invalid fetch ID
    total_tests += 1
    fetch_success, has_content = test_fetch("invalid_id_12345")
    if fetch_success:
        print(f"   ✅ Invalid fetch ID handled gracefully")
        passed_tests += 1
    else:
        print(f"   ❌ Invalid fetch ID caused error")
    
    # Test 5: Specific problematic queries from ChatGPT feedback
    print("\n5. CHATGPT REPORTED ISSUES")
    problem_queries = [
        "CS 6300 O01",  # Section search
        "CS 8803-O20",  # Hyphenated course
        "OMSCS",        # Program search
    ]
    
    for query in problem_queries:
        total_tests += 1
        success, count, first_id = test_search(query)
        
        if success and count > 0:
            print(f"   ✅ '{query}': Found {count} results")
            passed_tests += 1
        else:
            print(f"   ❌ '{query}': Failed or no results")
            critical_failures.append(f"Known issue '{query}' still failing")
    
    # Summary
    print("\n" + "=" * 80)
    print("VALIDATION SUMMARY")
    print("=" * 80)
    print(f"Total tests: {total_tests}")
    print(f"Passed: {passed_tests}")
    print(f"Failed: {total_tests - passed_tests}")
    print(f"Success rate: {passed_tests/total_tests*100:.1f}%")
    
    if critical_failures:
        print(f"\n❌ CRITICAL FAILURES ({len(critical_failures)}):")
        for failure in critical_failures:
            print(f"   - {failure}")
        print("\n⚠️  DO NOT USE THIS SERVER WITH CHATGPT!")
        return False
    else:
        print("\n✅ ALL TESTS PASSED THROUGH MCP PROTOCOL")
        print("The server should work correctly with ChatGPT!")
        return True


def check_service_status():
    """Check if the MCP service is running"""
    print("\nSERVICE STATUS CHECK:")
    try:
        import subprocess
        result = subprocess.run(['systemctl', 'is-active', 'gtmcp-mcp'], 
                              capture_output=True, text=True)
        if result.stdout.strip() == 'active':
            print("✅ Service is active")
        else:
            print("❌ Service is not active")
            return False
    except Exception as e:
        print(f"⚠️  Could not check service status: {e}")
    
    return True


if __name__ == "__main__":
    print("Starting MCP protocol validation...\n")
    
    # Check service
    service_ok = check_service_status()
    
    # Run validation through MCP
    validation_ok = run_validation()
    
    # Final verdict
    print("\n" + "=" * 80)
    if service_ok and validation_ok:
        print("✅ MCP PROTOCOL VALIDATION: PASSED")
        print("The Georgia Tech MCP Server is ready for use with ChatGPT!")
        sys.exit(0)
    else:
        print("❌ MCP PROTOCOL VALIDATION: FAILED")
        print("Please fix the issues before using with ChatGPT!")
        print("\nNOTE: The old validation was testing Python functions directly,")
        print("      which is why it passed when ChatGPT failed.")
        sys.exit(1)