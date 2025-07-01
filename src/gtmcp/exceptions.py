"""Custom exceptions for Georgia Tech MCP Server."""


class GTMCPError(Exception):
    """Base exception for all GTMCP errors."""
    pass


class ScraperError(GTMCPError):
    """Base exception for scraper-related errors."""
    pass


class NetworkError(ScraperError):
    """Raised when network requests fail."""
    pass


class ParseError(ScraperError):
    """Raised when HTML parsing fails."""
    pass


class ValidationError(ScraperError):
    """Raised when data validation fails."""
    pass


class ConfigurationError(GTMCPError):
    """Raised when configuration is invalid."""
    pass


class ServerError(GTMCPError):
    """Raised when server operations fail."""
    pass


class ToolError(ServerError):
    """Raised when MCP tool execution fails."""
    pass