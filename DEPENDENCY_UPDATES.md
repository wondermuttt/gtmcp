# Dependency Updates Summary

## Overview
This document summarizes the dependency updates made during the expansion of the GT MCP Server from a single-purpose course scheduling tool to a comprehensive multi-system integration platform.

## Version Changes
- **Project Version**: `0.1.0` → `2.0.0`
- **Python Requirement**: `>=3.11` (unchanged)

## New Core Dependencies

### Multi-System Integration
- **geopy>=2.3.0** - Spatial analysis and geographic calculations for campus navigation
- **networkx>=3.2.0** - Graph algorithms for route optimization and research collaboration networks
- **python-dateutil>=2.8.0** - Enhanced date parsing for research publication dates
- **aiohttp>=3.9.0** - Async HTTP client for improved performance
- **xmltodict>=0.13.0** - XML parsing for OAI-PMH protocol (SMARTech repository)

### MCP Server Framework
- **anyio>=4.5.0** - Async I/O library for cross-platform async support
- **httpx>=0.27.0** - Modern HTTP client for API requests
- **httpx-sse>=0.4.0** - Server-sent events support for real-time updates
- **pydantic-settings>=2.5.2** - Configuration management with environment variables
- **python-multipart>=0.0.9** - Multipart form data handling
- **sse-starlette>=1.6.1** - Server-sent events for Starlette framework
- **starlette>=0.27.0** - ASGI framework for high-performance web apps
- **uvicorn>=0.23.1** - ASGI server implementation
- **python-dotenv>=0.21.0** - Environment variable management

### Development & Testing
- **pytest-mock>=3.11.0** - Mocking capabilities for unit tests
- **responses>=0.23.0** - HTTP request mocking for testing
- **aioresponses>=0.7.4** - Async HTTP request mocking

## Updated Existing Dependencies
- **mcp>=1.0.0** - Core Model Context Protocol framework (unchanged)
- **requests>=2.31.0** - HTTP client library (unchanged)
- **beautifulsoup4>=4.12.0** - HTML parsing (unchanged)
- **lxml>=4.9.0** - XML/HTML processing (unchanged)
- **pydantic>=2.5.0** - Data validation and serialization (unchanged)

## New Optional Dependencies (Dev)
Added to the development dependencies for comprehensive testing:
- **pytest>=7.4.0** (unchanged)
- **pytest-asyncio>=0.21.0** (unchanged)
- **pytest-mock>=3.11.0** (new)
- **responses>=0.23.0** (new)
- **aioresponses>=0.7.4** (new)
- **black>=23.0.0** (unchanged)
- **ruff>=0.1.0** (unchanged)
- **mypy>=1.7.0** (unchanged)

## Installation Commands

### Fresh Installation
```bash
# Clone repository
git clone https://github.com/wondermuttt/gtmcp.git
cd gtmcp

# Install all dependencies
pip install -r requirements.txt

# Or install with optional dev dependencies
pip install -e ".[dev]"
```

### Upgrade Existing Installation
```bash
# Upgrade all dependencies
pip install -r requirements.txt --upgrade

# Or upgrade with dev dependencies
pip install -e ".[dev]" --upgrade
```

## Compatibility Notes

### Python Version
- **Minimum Python**: 3.11+ (unchanged)
- **Tested with**: Python 3.10.13 (development environment)
- **Production**: Python 3.11+ recommended

### Platform Support
- **Linux**: Fully supported ✅
- **macOS**: Fully supported ✅  
- **Windows**: Supported with standard Python installation ✅

### Docker Support
All dependencies are compatible with standard Python Docker images:
```dockerfile
FROM python:3.11-slim
COPY requirements.txt .
RUN pip install -r requirements.txt
```

## Dependency Justification

### Why These Dependencies?
1. **geopy & networkx**: Enable advanced campus navigation and route optimization
2. **xmltodict**: Required for SMARTech OAI-PMH protocol implementation
3. **aiohttp**: Provides async HTTP capabilities for better performance
4. **MCP framework dependencies**: Support the Model Context Protocol server implementation
5. **Testing dependencies**: Enable comprehensive unit and integration testing

### Security Considerations
- All dependencies are from trusted PyPI packages
- Version constraints prevent automatic upgrades to potentially breaking versions
- Regular dependency auditing recommended with `pip-audit`

## Breaking Changes
None. The expansion maintains backward compatibility with the original course scheduling functionality while adding new multi-system capabilities.

## Next Steps
1. **Regular Updates**: Monitor dependencies for security updates
2. **Dependency Auditing**: Use `pip-audit` to check for vulnerabilities
3. **Performance Monitoring**: Track impact of dependencies on startup time and memory usage
4. **Future Expansions**: Consider additional GT systems that may require new dependencies