# Georgia Tech Comprehensive MCP Server

An advanced MCP (Model Context Protocol) server that provides LLMs with comprehensive access to Georgia Tech's academic and research ecosystem, integrating multiple GT systems for intelligent workflows. **Now with OSCAR 500 error fixes for reliable course searching and ChatGPT HTTP integration.**

## Features

### ChatGPT Integration ✨ **NEW: HTTP API Server**
- **FastAPI HTTP Server**: Complete HTTP API for ChatGPT Custom Tools integration
- **CORS Enabled**: Cross-origin requests from ChatGPT domains supported
- **JSON Responses**: All endpoints return proper JSON for ChatGPT consumption
- **Auto Documentation**: Interactive OpenAPI/Swagger docs at `/docs` endpoint
- **Health Monitoring**: Real-time service health checks and monitoring

### Core Course Scheduling (OSCAR System) ✨ **500 Error Fixes Applied**
- **Available Semesters**: Get list of available semesters for course searches
- **Subject Lookup**: Get available departments/subjects for a given semester  
- **Course Search**: Search for courses by subject, course number, or title with improved reliability
- **Course Details**: Get detailed information including seat availability, waitlist info, and restrictions
- **Improved Workflow**: Fixed 500 server errors by implementing proper GT navigation patterns

### Research & Knowledge Systems (SMARTech Repository)
- **Research Paper Search**: Search 500+ research papers, theses, and publications
- **Faculty Research Matching**: Find faculty by research interests and collaboration history
- **Research Trend Analysis**: Analyze publication trends over time
- **Cross-Referencing**: Link research areas to related courses

### Campus Infrastructure (Places & GIS)
- **Location Services**: Search campus buildings and facilities
- **Accessibility Information**: Detailed accessibility features and routing
- **Service Discovery**: Find buildings with specific services (AV equipment, catering, etc.)
- **Spatial Analysis**: Route planning and proximity searches

### Cross-System Integration
- **Research-Course Correlation**: "What courses support my robotics research?"
- **Faculty-Course Matching**: "Who teaches courses related to my research area?"
- **Resource Optimization**: "Find labs with networking equipment near CS building"
- **Academic Planning**: "Plan degree path with research opportunities"

## Setup

### Automated Setup (Recommended)

1. **Run the setup script:**
   ```bash
   ./setup.sh
   ```
   This will automatically create the conda environment and install all dependencies.

2. **Start the server:**
   ```bash
   # For ChatGPT integration (HTTP API server):
   ./start_server_chatgpt.sh
   
   # For EXPANDED functionality (all GT systems):
   ./start_server_expanded.sh
   
   # For original course scheduling only:
   ./start_server.sh
   ```

### Manual Setup

1. **Create conda environment:**
   ```bash
   conda create -n gtmcp python=3.11 -y
   conda activate gtmcp
   ```

2. **Install dependencies:**
   ```bash
   pip install -r requirements.txt
   pip install -e .
   ```

3. **Test the functionality:**
   ```bash
   # Test original course scheduling:
   python test_server.py
   
   # Test expanded multi-system functionality:
   python test_expanded_server.py
   ```

4. **Run unit tests:**
   ```bash
   python -m pytest tests/ -v
   ```

5. **Run the server:**
   ```bash
   # ChatGPT HTTP API server:
   python -m gtmcp.server_fastapi --host 0.0.0.0 --port 8080
   
   # Expanded server (recommended):
   python -m gtmcp.server_expanded
   
   # Original course scheduling only:
   python -m gtmcp.server
   ```

## ChatGPT Integration Setup

### Quick Start
1. **Start the HTTP server:**
   ```bash
   ./start_server_chatgpt.sh
   ```
   Server will run on `http://0.0.0.0:8080` by default.

2. **Configure ChatGPT:**
   - Open ChatGPT settings
   - Go to Beta Features  
   - Enable "Custom GPTs & Tools"
   - Create new custom tool:
     - **Name**: Georgia Tech MCP Server
     - **Description**: Access GT course schedules and research
     - **URL**: `http://localhost:8080`

### Available HTTP Endpoints
```
GET  /                           # Server information and capabilities
GET  /health                     # System health status
GET  /tools                      # Available MCP tools
GET  /api/semesters             # Available academic semesters
GET  /api/subjects/{term_code}   # Subjects for specific semester
GET  /api/courses               # Course search (query params: term_code, subject)
GET  /api/courses/{term}/{crn}  # Detailed course information
GET  /api/research              # Research paper search (query params: keywords, max_records)
GET  /docs                      # Interactive API documentation
GET  /openapi.json              # OpenAPI specification
GET  /.well-known/ai-plugin.json # ChatGPT AI plugin manifest
GET  /legal                     # Legal information and terms
```

### Example ChatGPT Queries
- "What CS courses are available for Spring 2025?"
- "Find research papers about machine learning"
- "Get details for course CRN 12345 in Spring 2025"
- "What subjects are available for Fall 2024?"

## MCP Tools (17 Comprehensive Tools)

### Course & Academic Tools

#### `get_available_semesters`
Get list of available semesters.
- **Input**: None
- **Output**: List of semesters with codes and names

#### `get_subjects` 
Get available subjects/departments for a semester.
- **Input**: `term_code` (e.g., "202502" for Spring 2025)
- **Output**: List of subject codes and names

#### `search_courses`
Search for courses in a given semester and subject.
- **Input**: 
  - `term_code`: Semester code
  - `subject`: Subject code (e.g., "CS", "MATH")
  - `course_num` (optional): Course number filter
  - `title` (optional): Title search filter
- **Output**: List of matching courses with CRNs

#### `get_course_details`
Get detailed information for a specific course.
- **Input**:
  - `term_code`: Semester code  
  - `crn`: Course Reference Number
- **Output**: Detailed course info including seats, waitlist, restrictions

### Research & Knowledge Tools

#### `search_research_papers`
Search Georgia Tech research repository for papers.
- **Input**: 
  - `keywords`: Array of search keywords
  - `subject_areas`: Subject areas to filter by
  - `date_from/date_until`: Date range filters
  - `max_results`: Maximum results to return
- **Output**: List of research papers with abstracts and metadata

#### `find_faculty_research`
Find faculty research profiles by research area.
- **Input**: `research_area` (e.g., "robotics", "AI")
- **Output**: Faculty profiles with research interests and publications

#### `analyze_research_trends`
Analyze research trends over time for keywords.
- **Input**: 
  - `keywords`: Keywords to analyze
  - `years`: Number of years to analyze
- **Output**: Trend analysis with yearly publication counts

#### `get_repository_info`
Get information about the GT research repository.
- **Input**: None
- **Output**: Repository metadata and statistics

### Campus & Location Tools

#### `search_campus_locations`
Search for campus buildings and locations.
- **Input**:
  - `query`: Search query for building/location name
  - `services`: Required services (e.g., "AV equipment")
  - `accessible`: Filter for wheelchair accessible locations
- **Output**: List of matching campus locations

#### `get_location_details`
Get detailed information about a specific location.
- **Input**: `building_id`: Building identifier
- **Output**: Complete location details including services and accessibility

#### `find_nearby_locations`
Find locations near a specific building.
- **Input**:
  - `center_building_id`: Building to search around
  - `radius_meters`: Search radius
  - `services`: Services to filter by
- **Output**: List of nearby locations within radius

#### `get_accessibility_info`
Get detailed accessibility information for a building.
- **Input**: `building_id`: Building identifier
- **Output**: Comprehensive accessibility features and services

### Cross-System Integration Tools

#### `suggest_research_collaborators`
Suggest potential collaborators based on research interests.
- **Input**: 
  - `research_area`: Research area for collaboration
  - `keywords`: Specific research keywords
- **Output**: Suggested faculty and researchers with overlap analysis

#### `find_courses_for_research`
Find courses related to a specific research area.
- **Input**:
  - `research_topic`: Research topic or area
  - `term_code`: Semester to search in (optional)
- **Output**: Related courses with research connections

#### `check_system_health`
Check health status of all integrated GT systems.
- **Input**: None
- **Output**: Status report for OSCAR, SMARTech, Places, and other systems

## Configuration

The server can be configured via `config.json`:

```json
{
  "server": {
    "host": "0.0.0.0",
    "port": 8080,
    "log_level": "INFO"
  },
  "scraper": {
    "delay": 1.0,
    "timeout": 30,
    "max_retries": 3
  },
  "cache": {
    "enabled": true,
    "ttl_seconds": 3600
  }
}
```

### Command Line Options

```bash
# Run with custom config file
python -m gtmcp.server --config /path/to/config.json

# Override specific settings
python -m gtmcp.server --host 127.0.0.1 --port 9000 --log-level DEBUG

# Use startup script with custom args
./start_server.sh --host 127.0.0.1 --port 9000
```

## Usage Examples

### Basic Course Scheduling
```python
# Search for CS courses in Spring 2025
search_courses(term_code="202502", subject="CS")

# Get details for a specific course
get_course_details(term_code="202502", crn="25645")
```

### Research & Faculty Discovery
```python
# Find research papers on machine learning
search_research_papers(keywords=["machine learning", "AI"], max_results=10)

# Find faculty working on robotics
find_faculty_research(research_area="robotics")

# Analyze AI research trends over 5 years
analyze_research_trends(keywords=["artificial intelligence"], years=5)
```

### Campus Navigation & Services
```python
# Find accessible buildings with AV equipment
search_campus_locations(services=["AV equipment"], accessible=True)

# Find locations near the library
find_nearby_locations(center_building_id="library", radius_meters=500)

# Get accessibility details for a building
get_accessibility_info(building_id="klaus_building")
```

### Cross-System Intelligence
```python
# Find courses that support sustainability research
find_courses_for_research(research_topic="sustainability", term_code="202502")

# Suggest collaborators for networking research
suggest_research_collaborators(research_area="networking", keywords=["wireless", "5G"])

# Check health of all GT systems
check_system_health()
```

## Rate Limiting

The scraper includes configurable delays and retry logic to be respectful to the GT OSCAR system:
- Default 1-second delay between requests
- 30-second timeout per request
- Up to 3 retries with exponential backoff

## Testing

The project includes comprehensive testing for all integrated systems:

### Comprehensive Test Suite (124+ Tests)
- **38 HTTP Server Tests**: FastAPI endpoint testing and ChatGPT integration validation
- **17 External Server Tests**: Real HTTP server integration testing with subprocess management
- **69+ MCP Unit Tests**: Original MCP functionality validation and client testing

### HTTP Server & ChatGPT Integration Tests
```bash
# Run all HTTP integration tests (38 tests)
python -m pytest tests/test_fastapi_server.py tests/test_external_server.py -v

# Run FastAPI server tests (21 tests)
python -m pytest tests/test_fastapi_server.py -v

# Run external server tests (17 tests)  
python -m pytest tests/test_external_server.py -v

# Run specific test categories
python -m pytest tests/test_fastapi_server.py::TestFastAPIServerBasic -v
python -m pytest tests/test_external_server.py::TestExternalServerChatGPTCompatibility -v
```

### Unit Tests
- **Model Tests**: Data validation and serialization
- **Configuration Tests**: Config loading and validation  
- **Client Tests**: All GT system clients with mocked responses
- **Server Tests**: MCP server tools and error handling
- **Integration Tests**: Cross-system workflow validation

Run all tests:
```bash
python -m pytest tests/ -v
```

Run specific test modules:
```bash
python -m pytest tests/test_oscar_client.py -v
python -m pytest tests/test_smartech_client.py -v
python -m pytest tests/test_places_client.py -v
python -m pytest tests/test_server_expanded.py -v
```

### Integration Tests
```bash
# Test original course scheduling:
python test_server.py

# Test expanded multi-system functionality:
python test_expanded_server.py
```

### Test Categories

#### FastAPI Server Tests (21 tests)
- ✅ **Basic Functionality**: Root, health, and tools endpoints
- ✅ **OSCAR Integration**: Semesters, subjects, courses, and details with mocked data
- ✅ **Research Integration**: Paper search and research endpoints
- ✅ **ChatGPT Compatibility**: CORS, JSON responses, AI plugin manifest, legal endpoint
- ✅ **Performance**: Concurrent requests, large responses, error recovery

#### External Server Tests (17 tests)  
- ✅ **Real HTTP Server**: Subprocess startup and external HTTP testing
- ✅ **ChatGPT Integration**: Cross-origin requests and response validation
- ✅ **Server Reliability**: Load testing, memory stability, error recovery
- ✅ **API Documentation**: OpenAPI spec and interactive docs validation

### System Health Checks
```bash
# Quick health check of all systems:
python -c "
from gtmcp.server_expanded import *
import asyncio
asyncio.run(main())
" --help
```

## Error Handling

The application includes comprehensive error handling:

- **Network Errors**: Retry logic with exponential backoff
- **Parse Errors**: Graceful handling of malformed HTML
- **Validation Errors**: Input validation with clear error messages
- **Server Errors**: Structured error responses for MCP tools

All errors are logged with appropriate severity levels and include helpful context for debugging.

## Note on Data Availability

Georgia Tech may not maintain course details beyond the next semester, even though older semesters appear in the dropdown. Always check that courses are actually available for the requested semester.