# Georgia Tech MCP Testing Documentation

## Overview
This document consolidates all testing-related documentation for the Georgia Tech MCP Server project.

## Table of Contents
1. [Test Suite Overview](#test-suite-overview)
2. [Running Tests](#running-tests)
3. [Test Categories](#test-categories)
4. [Test-Driven Development](#test-driven-development)
5. [Deployment Testing](#deployment-testing)
6. [Adding New Tests](#adding-new-tests)
7. [Historical Fixes](#historical-fixes)

## Test Suite Overview

The Georgia Tech MCP Server uses a comprehensive test suite (`test_suite.py`) that manages both unit and integration tests. The suite supports:
- Running all tests or specific categories
- Pre-deployment (unit) and post-deployment (integration) testing
- Individual test execution
- Special handling for tests with import dependencies

### Key Components
- `test_suite.py` - Main test runner
- `run_test_with_server.py` - Helper for tests requiring server imports
- `pre_deploy_tests.sh` - Pre-deployment validation script
- `post_deploy_tests.sh` - Post-deployment validation script
- `tests/` - Directory containing all test files organized by type and category

### Directory Structure
```
tests/
├── unit/
│   ├── parsing/      # Query parsing, semester logic, course codes
│   ├── cache/        # Cache behavior and performance
│   ├── search/       # Search functionality tests
│   ├── fetch/        # Fetch operations and ChatGPT compatibility
│   └── error_handling/ # Error handling scenarios
└── integration/
    ├── mcp_protocol/ # MCP protocol validation
    ├── scenarios/    # Real-world usage scenarios
    ├── performance/  # Performance benchmarks
    └── api/          # API endpoint tests
```

## Running Tests

### Dynamic Test Suite (Recommended)
The new dynamic test suite automatically discovers tests based on directory structure - no manual configuration needed!

```bash
# Run all tests
./test_suite_dynamic.py

# Run unit tests only (pre-deployment)
./test_suite_dynamic.py --unit
# or
./pre_deploy_tests.sh

# Run integration tests only (post-deployment)
./test_suite_dynamic.py --integration
# or
./post_deploy_tests.sh

# Run specific category
./test_suite_dynamic.py --category fetch

# Run single test (multiple ways)
./test_suite_dynamic.py --test test_course_capacity_data.py
./test_suite_dynamic.py --test test_course_capacity_data
./test_suite_dynamic.py --test tests/integration/api/test_course_capacity_data.py

# List all automatically discovered tests
./test_suite_dynamic.py --list
```

#### Benefits of Dynamic Test Suite
- **Zero Configuration**: Just create a test file starting with `test_` in the appropriate directory
- **Automatic Discovery**: Finds all tests based on directory structure
- **Smart Import Handling**: Automatically detects and handles import errors
- **Flexible Test Selection**: Find tests by name, partial name, or full path

### Legacy Test Suite
The original test suite (`test_suite.py`) requires manual configuration but is still available:

```bash
# Run all tests
./test_suite.py

# Run specific category
./test_suite.py --category fetch

# Run single test
./test_suite.py --test test_fetch_omscs_filtering.py

# List all available tests
./test_suite.py --list
```

## Test Categories

### Unit Tests
Tests that verify individual components without external dependencies. Located in `tests/unit/`.

#### parsing (`tests/unit/parsing/`)
- `test_omscs_filtering_logic.py` - OMSCS section filtering logic
- `test_next_semester_logic.py` - Semester defaulting behavior
- `test_hyphenated_courses.py` - Hyphenated course code parsing (CS 8803-O20)
- `test_semester_defaulting.py` - Semester determination logic
- `test_omscs_section_pattern.py` - OMSCS section pattern validation (O01 vs O3, OSZ)

#### cache (`tests/unit/cache/`)
- `test_cache_behavior.py` - Cache storage and retrieval
- `test_fast_cache.py` - FastCache implementation
- `test_cache_performance.py` - Cache performance benchmarks
- `test_pickle_edge_cases.py` - Pickle serialization edge cases

#### search (`tests/unit/search/`)
- `test_search_filtering_bug.py` - Search filtering issues
- `test_comprehensive_search.py` - Comprehensive search scenarios
- `test_section_searches.py` - Section-specific searches
- `test_search_format_bug.py` - Search result formatting
- `test_omscs.py` - OMSCS-specific searches

#### fetch (`tests/unit/fetch/`)
- `test_fetch_omscs_filtering.py` - Fetch with OMSCS filtering
- `test_chatgpt_exact_flow.py` - ChatGPT's exact API flow
- `test_fetch_course_codes.py` - Fetch using course codes (CS 6515)
- `test_chatgpt_fetch_scenarios.py` - ChatGPT fetch scenarios
- `test_omscs_filtering_precise.py` - Precise OMSCS filtering (O01 only, not O3/OSZ)

#### error_handling (`tests/unit/error_handling/`)
- `test_error_handling.py` - Error handling scenarios

### Integration Tests
Tests that verify the system works end-to-end with all components. Located in `tests/integration/`.

#### mcp_protocol (`tests/integration/mcp_protocol/`)
- `POST_DEPLOYMENT_VALIDATION_V2.py` - Comprehensive MCP protocol validation
- `test_mcp_server.py` - MCP server functionality
- `test_live_server.py` - Live server tests
- `test_mcp_protocol_layer.py` - Protocol layer tests
- `test_mcp_response_format.py` - Response formatting
- `test_mcp_tools_list.py` - Tools listing
- `test_mcp_format_fix.py` - Format fixes

#### scenarios (`tests/integration/scenarios/`)
- `test_all_chatgpt_scenarios.py` - All ChatGPT usage scenarios
- `test_search_then_fetch.py` - Search followed by fetch
- `test_fetch_via_mcp.py` - Fetch through MCP protocol
- `test_chatgpt_format.py` - ChatGPT format compatibility
- `test_chatgpt_fix_verification.py` - Fix verification
- `test_single_fetch.py` - Single fetch operations

#### performance (`tests/integration/performance/`)
- `benchmark_serialization_v2.py` - Serialization performance
- `cache_performance_comparison.py` - Cache backend comparison
- `test_concurrent_fetch.py` - Concurrent operations

#### api (`tests/integration/api/`)
- `test_direct_api.py` - Direct API calls
- `test_actual_response.py` - Response validation
- `test_expanded_server.py` - Extended server features
- `test_server.py` - Basic server functionality

## Test-Driven Development

We follow TDD principles, as demonstrated in the campus_code fix:

1. **Write Test First**: Create a test that catches the bug
   ```python
   # test_fetch_omscs_filtering.py
   # Tests that campus_code AttributeError is caught
   ```

2. **Verify Test Fails**: Run test to confirm it catches the bug
   ```bash
   ./test_suite.py --test test_fetch_omscs_filtering.py
   # ✗ ERROR: 'CourseInfo' object has no attribute 'campus_code'
   ```

3. **Fix the Code**: Implement the fix
   ```python
   # Change from: c.campus_code == 'O'
   # To: c.section.startswith('O')
   ```

4. **Verify Test Passes**: Confirm the fix works
   ```bash
   ./test_suite.py --test test_fetch_omscs_filtering.py
   # ✓ All tests passed!
   ```

## Deployment Testing

### Pre-Deployment
Run before deploying changes to ensure code quality:
```bash
./pre_deploy_tests.sh
```
This runs all unit tests to verify:
- Parsing logic works correctly
- Cache operations are functional
- Search and fetch handle all cases
- Error handling is robust

### Post-Deployment
Run after deployment to ensure the live system works:
```bash
./post_deploy_tests.sh
```
This runs all integration tests to verify:
- MCP protocol communication works
- ChatGPT scenarios function correctly
- Performance meets requirements
- API endpoints respond properly

## Adding New Tests

### 1. Create Test File
Follow naming convention: `test_<feature>_<specifics>.py`

Place it in the appropriate directory:
- Unit tests: `tests/unit/<category>/`
- Integration tests: `tests/integration/<category>/`

### 2. Add to Test Suite
Edit `test_suite.py` and add your test to the appropriate category:
```python
UNIT_TESTS = {
    "category_name": [
        "tests/unit/category_name/existing_test.py",
        "tests/unit/category_name/your_new_test.py",  # Add here
    ],
}
```

### 3. Handle Import Issues
If your test imports from `fastmcp_server_v2`, add just the filename to the special_tests list in `test_suite.py`:
```python
special_tests = [
    'existing_test.py',
    'your_new_test.py',  # Add filename only
]
```

### 4. Test Your Test
```bash
# Run individually first
./test_suite.py --test tests/unit/category_name/your_new_test.py

# Then run the category
./test_suite.py --category category_name
```

## Historical Fixes

### Major Issues Resolved Through Testing

#### 1. ChatGPT List Error (CHATGPT_LIST_ERROR_FIX.md)
- **Issue**: 'list' object has no attribute 'get' error
- **Fix**: Ensured search always returns dict with 'results' key
- **Test**: `test_chatgpt_format.py`

#### 2. Session Requirements (SESSION_FIX_SUMMARY.md)
- **Issue**: FastMCP required sessions, ChatGPT couldn't handle
- **Fix**: Added `stateless_http=True` to FastMCP initialization
- **Test**: `POST_DEPLOYMENT_VALIDATION_V2.py`

#### 3. Fetch with Course Codes (FETCH_COURSE_CODES_IMPLEMENTATION.md)
- **Issue**: ChatGPT sends "CS 6515" instead of "course_202508_86143"
- **Fix**: Added course code parsing to fetch function
- **Test**: `test_fetch_course_codes.py`

#### 4. OMSCS Filtering (Fixed via TDD)
- **Issue**: Code tried to access non-existent campus_code attribute
- **Fix**: Use section.startswith('O') for OMSCS detection
- **Test**: `test_fetch_omscs_filtering.py`

#### 5. Precise OMSCS Section Pattern (Fixed via TDD)
- **Issue**: startswith('O') matched O3, OSZ which aren't OMSCS sections
- **Fix**: Check for pattern O## (len=3, O + 2 digits)
- **Test**: `test_omscs_section_pattern.py`

#### 6. Course Capacity Data Missing (Fixed via TDD)
- **Issue**: Capacity data showing as N/A instead of actual values
- **Root Cause 1**: Fetch function tried to access `details.seats_capacity` directly instead of `details.registration.seats_capacity`
- **Root Cause 2**: OSCAR parser checked for 'Seats' which matched 'Waitlist Seats' first, swapping the data
- **Fix 1**: Access registration attributes via `details.registration` object
- **Fix 2**: Check for 'Waitlist' first in parser to avoid false matches
- **Tests**: `test_course_capacity_data.py`, `test_capacity_formatting.py`

### Performance Improvements (PERFORMANCE_SUMMARY.md)
- Pickle+gzip caching: 2.3x faster
- Concurrent fetching: 6.2x speedup
- Tests: `benchmark_serialization_v2.py`, `cache_performance_comparison.py`

## Best Practices

1. **Always Test First**: Write tests before implementing features
2. **Test at Multiple Levels**: Unit tests for logic, integration tests for workflows
3. **Use Descriptive Names**: Test names should clearly indicate what they test
4. **Keep Tests Fast**: Unit tests should run quickly; longer tests go in integration
5. **Test Edge Cases**: Include tests for error conditions and boundary cases
6. **Document Failures**: When a test catches a bug, document it in the test

## Continuous Integration

For CI/CD integration, use exit codes:
- 0: All tests passed
- 1: One or more tests failed
- 2: Error running tests

Example GitHub Actions workflow:
```yaml
- name: Run pre-deployment tests
  run: ./pre_deploy_tests.sh
  
- name: Deploy
  run: ./deploy.sh
  
- name: Run post-deployment tests
  run: ./post_deploy_tests.sh
```

## Future Improvements

### Directory Reorganization
Consider organizing tests into subdirectories:
```
tests/
├── unit/
│   ├── parsing/
│   ├── cache/
│   ├── search/
│   ├── fetch/
│   └── error_handling/
└── integration/
    ├── mcp_protocol/
    ├── scenarios/
    ├── performance/
    └── api/
```

### Old Test Framework
The `tests/` directory contains tests from the old framework. These are being phased out in favor of the new test suite.

## Troubleshooting

### Import Errors
If a test fails with import errors, ensure it's in the special_tests list in `test_suite.py`.

### Timeout Issues
Tests have a 2-minute timeout. For longer operations, run outside the test suite.

### Server Not Running
Integration tests require the MCP server. The test suite will attempt to start it automatically.

### Cache Issues
Some tests may fail if cache is stale. Clear cache with:
```bash
rm -rf cache/*.pkl.gz
```

### SSE Headers
MCP protocol tests require proper SSE headers:
```
Accept: application/json,text/event-stream
```

## Performance Benchmarks

Recent performance metrics:
- Cache with pickle+gzip: 96% size reduction
- Cached search response: ~0.027s
- Single fetch time: ~0.8s
- Concurrent fetching: 6.2x speedup over sequential

## Related Documentation

### Core Project Documentation
- **README.md** - Main project documentation
- **DEPLOYMENT.md** - Deployment instructions
- **SSL_SETUP.md** - SSL/HTTPS configuration

### Implementation Documentation
- **FASTMCP_IMPLEMENTATION.md** - FastMCP framework implementation
- **MCP_MIGRATION_TODO.md** - Migration from old to new implementation
- **V2_IMPROVEMENTS.md** - Version 2 improvements
- **PERFORMANCE_SUMMARY.md** - Performance improvements and benchmarks
- **ERROR_HANDLING_IMPROVEMENTS.md** - Error handling enhancements
- **SEARCH_FILTERING_BUG_PREVENTION.md** - Search optimization details

### Historical Documentation
- **UPDATES_SUMMARY.md** - Project update history
- **DEPENDENCY_UPDATES.md** - Dependency management
- **OSCAR_IMPROVEMENTS.md** - OSCAR client improvements
- **FINAL_STATUS_REPORT.md** - Project status summary

### Archived Test Documentation
The following test documentation has been consolidated into this document and archived in `archive/`:

**Test Documentation** (in `archive/test_docs/`):
- TEST_INVENTORY.md - Original test inventory
- TEST_MIGRATION_PLAN.md - Migration planning
- TEST_SUITE_README.md - Original test suite docs
- VALIDATION_REPORT.md - Validation metrics

**Fix Documentation** (in `archive/fix_docs/`):
- CHATGPT_LIST_ERROR_FIX.md - List error fix details
- COMPREHENSIVE_SEARCH_FIX.md - Search fix details
- FETCH_COURSE_CODES_IMPLEMENTATION.md - Fetch implementation
- SESSION_FIX_SUMMARY.md - Session fix details

---

*This document consolidates all testing documentation. Old individual test docs have been archived in the `archive/` directory for historical reference.*