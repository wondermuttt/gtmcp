# Georgia Tech MCP Server

An MCP (Model Context Protocol) server that provides LLMs with access to Georgia Tech's OSCAR course schedule system.

## Features

- **Available Semesters**: Get list of available semesters for course searches
- **Subject Lookup**: Get available departments/subjects for a given semester  
- **Course Search**: Search for courses by subject, course number, or title
- **Course Details**: Get detailed information including seat availability, waitlist info, and restrictions

## Setup

### Automated Setup (Recommended)

1. **Run the setup script:**
   ```bash
   ./setup.sh
   ```
   This will automatically create the conda environment and install all dependencies.

2. **Start the server:**
   ```bash
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

3. **Test the scraper:**
   ```bash
   python test_server.py
   ```

4. **Run unit tests:**
   ```bash
   python -m pytest tests/ -v
   ```

5. **Run the MCP server:**
   ```bash
   python -m gtmcp.server
   ```

## MCP Tools

### `get_available_semesters`
Get list of available semesters.
- **Input**: None
- **Output**: List of semesters with codes and names

### `get_subjects` 
Get available subjects/departments for a semester.
- **Input**: `term_code` (e.g., "202502" for Spring 2025)
- **Output**: List of subject codes and names

### `search_courses`
Search for courses in a given semester and subject.
- **Input**: 
  - `term_code`: Semester code
  - `subject`: Subject code (e.g., "CS", "MATH")
  - `course_num` (optional): Course number filter
  - `title` (optional): Title search filter
- **Output**: List of matching courses with CRNs

### `get_course_details`
Get detailed information for a specific course.
- **Input**:
  - `term_code`: Semester code  
  - `crn`: Course Reference Number
- **Output**: Detailed course info including seats, waitlist, restrictions

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

```python
# Search for CS courses in Spring 2025
search_courses(term_code="202502", subject="CS")

# Get details for a specific course
get_course_details(term_code="202502", crn="25645")
```

## Rate Limiting

The scraper includes configurable delays and retry logic to be respectful to the GT OSCAR system:
- Default 1-second delay between requests
- 30-second timeout per request
- Up to 3 retries with exponential backoff

## Testing

The project includes comprehensive unit tests covering all modules:

- **Model Tests**: Data validation and serialization
- **Configuration Tests**: Config loading and validation  
- **Scraper Tests**: Web scraping functionality with mocked responses
- **Server Tests**: MCP server tools and error handling

Run all tests:
```bash
python -m pytest tests/ -v
```

Run specific test modules:
```bash
python -m pytest tests/test_scraper.py -v
python -m pytest tests/test_server.py -v
```

Run integration test:
```bash
python test_server.py
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