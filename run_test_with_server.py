#!/usr/bin/env python3
"""
Test runner that ensures the MCP server is running before executing tests
This allows tests that import from fastmcp_server_v2 to work properly
"""

import sys
import subprocess
import time
import os
import signal

def check_server_status():
    """Check if the MCP server is running"""
    result = subprocess.run(['systemctl', 'is-active', 'gtmcp-mcp'], 
                          capture_output=True, text=True)
    return result.stdout.strip() == 'active'

def ensure_server_running():
    """Ensure the MCP server is running"""
    if not check_server_status():
        print("MCP server is not running. Starting it...")
        subprocess.run(['sudo', 'systemctl', 'start', 'gtmcp-mcp'])
        time.sleep(2)
        
        if not check_server_status():
            print("Failed to start MCP server!")
            return False
    
    print("MCP server is running")
    return True

def run_test_file(test_file):
    """Run a test file that may require server imports"""
    
    # For tests that need direct imports, we'll run them differently
    if test_file in ['test_chatgpt_exact_flow.py', 'test_hyphenated_courses.py', 
                     'test_concurrent_fetch.py', 'test_semester_defaulting.py']:
        
        # These tests import from fastmcp_server_v2 directly
        # We'll run them via the server's Python environment
        env = os.environ.copy()
        env['PYTHONPATH'] = '/home/wondermutt/gtmcp/src'
        
        # Use the conda environment's Python
        python_cmd = '/home/wondermutt/miniforge3/envs/gtmcp/bin/python'
        
        try:
            result = subprocess.run([python_cmd, test_file], 
                                  capture_output=True, text=True, env=env)
            print(result.stdout)
            if result.stderr:
                print(result.stderr, file=sys.stderr)
            return result.returncode
        except Exception as e:
            print(f"Error running test: {e}")
            return 1
    else:
        # Regular tests can run normally
        try:
            result = subprocess.run([sys.executable, test_file], 
                                  capture_output=True, text=True)
            print(result.stdout)
            if result.stderr:
                print(result.stderr, file=sys.stderr)
            return result.returncode
        except Exception as e:
            print(f"Error running test: {e}")
            return 1

if __name__ == "__main__":
    if len(sys.argv) < 2:
        print("Usage: run_test_with_server.py <test_file>")
        sys.exit(1)
    
    test_file = sys.argv[1]
    
    # Ensure server is running for integration tests
    if not test_file.startswith('test_omscs_filtering_logic'):
        if not ensure_server_running():
            sys.exit(1)
    
    # Run the test
    exit_code = run_test_file(test_file)
    sys.exit(exit_code)