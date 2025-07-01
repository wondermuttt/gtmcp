"""Georgia Tech MCP Server implementation."""

import argparse
import asyncio
import logging
from typing import Any, Dict, List

from mcp.server import Server
from mcp.server.stdio import stdio_server
from mcp.types import (
    CallToolResult,
    ListToolsResult, 
    TextContent,
    Tool,
)

from .config import Config, load_config
from .exceptions import GTMCPError, ScraperError, ToolError
from .models import CourseDetails, CourseInfo, Semester, Subject
from .scraper import GTOscarScraper

# Global configuration
config: Config = None
logger = logging.getLogger(__name__)

# Initialize the MCP server
server = Server("gtmcp")

# Initialize the scraper (will be configured in main)
scraper: GTOscarScraper = None


@server.list_tools()
async def list_tools() -> ListToolsResult:
    """List available tools."""
    return ListToolsResult(
        tools=[
            Tool(
                name="get_available_semesters",
                description="Get list of available semesters for course searches",
                inputSchema={
                    "type": "object",
                    "properties": {},
                    "required": []
                }
            ),
            Tool(
                name="get_subjects",
                description="Get list of available subjects/departments for a given semester",
                inputSchema={
                    "type": "object",
                    "properties": {
                        "term_code": {
                            "type": "string",
                            "description": "Semester code (e.g., '202502' for Spring 2025)"
                        }
                    },
                    "required": ["term_code"]
                }
            ),
            Tool(
                name="search_courses", 
                description="Search for courses in a given semester and subject",
                inputSchema={
                    "type": "object",
                    "properties": {
                        "term_code": {
                            "type": "string",
                            "description": "Semester code (e.g., '202502' for Spring 2025)"
                        },
                        "subject": {
                            "type": "string", 
                            "description": "Subject code (e.g., 'CS', 'MATH', 'EE')"
                        },
                        "course_num": {
                            "type": "string",
                            "description": "Optional course number filter (e.g., '1100')",
                            "optional": True
                        },
                        "title": {
                            "type": "string",
                            "description": "Optional course title search filter",
                            "optional": True
                        }
                    },
                    "required": ["term_code", "subject"]
                }
            ),
            Tool(
                name="get_course_details",
                description="Get detailed information for a specific course including seats and restrictions",
                inputSchema={
                    "type": "object",
                    "properties": {
                        "term_code": {
                            "type": "string",
                            "description": "Semester code (e.g., '202502' for Spring 2025)"
                        },
                        "crn": {
                            "type": "string",
                            "description": "Course Reference Number (CRN)"
                        }
                    },
                    "required": ["term_code", "crn"]
                }
            )
        ]
    )


@server.call_tool()
async def call_tool(name: str, arguments: Dict[str, Any]) -> CallToolResult:
    """Handle tool calls."""
    logger.info(f"Calling tool: {name} with arguments: {arguments}")
    
    try:
        if not name:
            raise ToolError("Tool name is required")
            
        if name == "get_available_semesters":
            return await _get_available_semesters()
        elif name == "get_subjects":
            return await _get_subjects(arguments)
        elif name == "search_courses":
            return await _search_courses(arguments)
        elif name == "get_course_details":
            return await _get_course_details(arguments)
        else:
            raise ToolError(f"Unknown tool: {name}")
            
    except ToolError as e:
        logger.error(f"Tool error in {name}: {e}")
        return CallToolResult(
            content=[TextContent(type="text", text=f"Tool Error: {str(e)}")],
            isError=True
        )
    except ScraperError as e:
        logger.error(f"Scraper error in tool {name}: {e}")
        return CallToolResult(
            content=[TextContent(type="text", text=f"Data Retrieval Error: {str(e)}")],
            isError=True
        )
    except GTMCPError as e:
        logger.error(f"GTMCP error in tool {name}: {e}")
        return CallToolResult(
            content=[TextContent(type="text", text=f"Application Error: {str(e)}")],
            isError=True
        )
    except Exception as e:
        logger.error(f"Unexpected error in tool {name}: {e}", exc_info=True)
        return CallToolResult(
            content=[TextContent(type="text", text=f"Unexpected Error: {str(e)}")],
            isError=True
        )


async def _get_available_semesters() -> CallToolResult:
    """Get available semesters."""
    try:
        if not scraper:
            raise ToolError("Scraper not initialized")
            
        def get_semesters() -> List[Semester]:
            return scraper.get_available_semesters()
        
        # Run scraper in thread to avoid blocking
        loop = asyncio.get_event_loop()
        semesters = await loop.run_in_executor(None, get_semesters)
        
        if semesters is None:
            raise ToolError("Failed to retrieve semesters")
        
        # Format response
        result = {
            "semesters": [
                {
                    "code": sem.code,
                    "name": sem.name, 
                    "view_only": sem.view_only
                } 
                for sem in semesters
            ],
            "count": len(semesters)
        }
        
        logger.info(f"Successfully retrieved {len(semesters)} semesters")
        return CallToolResult(
            content=[TextContent(type="text", text=str(result))]
        )
        
    except Exception as e:
        logger.error(f"Error getting available semesters: {e}")
        raise


async def _get_subjects(arguments: Dict[str, Any]) -> CallToolResult:
    """Get subjects for a term."""
    try:
        if not scraper:
            raise ToolError("Scraper not initialized")
            
        if not arguments:
            raise ToolError("Arguments are required")
            
        term_code = arguments.get("term_code")
        if not term_code or not term_code.strip():
            raise ToolError("term_code is required and cannot be empty")
        
        term_code = term_code.strip()
        
        def get_subjects() -> List[Subject]:
            return scraper.get_subjects(term_code)
        
        loop = asyncio.get_event_loop()
        subjects = await loop.run_in_executor(None, get_subjects)
        
        if subjects is None:
            raise ToolError("Failed to retrieve subjects")
        
        result = {
            "term_code": term_code,
            "subjects": [
                {
                    "code": subj.code,
                    "name": subj.name
                }
                for subj in subjects
            ],
            "count": len(subjects)
        }
        
        logger.info(f"Successfully retrieved {len(subjects)} subjects for term {term_code}")
        return CallToolResult(
            content=[TextContent(type="text", text=str(result))]
        )
        
    except Exception as e:
        logger.error(f"Error getting subjects: {e}")
        raise


async def _search_courses(arguments: Dict[str, Any]) -> CallToolResult:
    """Search for courses.""" 
    term_code = arguments.get("term_code")
    subject = arguments.get("subject")
    course_num = arguments.get("course_num")
    title = arguments.get("title")
    
    if not term_code or not subject:
        raise ValueError("term_code and subject are required")
    
    def search() -> List[CourseInfo]:
        return scraper.search_courses(term_code, subject, course_num, title)
    
    loop = asyncio.get_event_loop()
    courses = await loop.run_in_executor(None, search)
    
    result = {
        "term_code": term_code,
        "subject": subject,
        "course_num": course_num,
        "title": title,
        "courses": [
            {
                "crn": course.crn,
                "title": course.title,
                "subject": course.subject,
                "course_number": course.course_number,
                "section": course.section
            }
            for course in courses
        ]
    }
    
    return CallToolResult(
        content=[TextContent(type="text", text=str(result))]
    )


async def _get_course_details(arguments: Dict[str, Any]) -> CallToolResult:
    """Get detailed course information."""
    term_code = arguments.get("term_code")
    crn = arguments.get("crn")
    
    if not term_code or not crn:
        raise ValueError("term_code and crn are required")
    
    def get_details() -> CourseDetails:
        return scraper.get_course_details(term_code, crn)
    
    loop = asyncio.get_event_loop()
    details = await loop.run_in_executor(None, get_details)
    
    result = {
        "crn": details.crn,
        "title": details.title,
        "subject": details.subject,
        "course_number": details.course_number,
        "section": details.section,
        "term": details.term,
        "credits": details.credits,
        "schedule_type": details.schedule_type,
        "campus": details.campus,
        "levels": details.levels,
        "registration": {
            "seats": {
                "capacity": details.registration.seats_capacity,
                "actual": details.registration.seats_actual,
                "remaining": details.registration.seats_remaining
            },
            "waitlist": {
                "capacity": details.registration.waitlist_capacity,
                "actual": details.registration.waitlist_actual,
                "remaining": details.registration.waitlist_remaining
            }
        },
        "restrictions": details.restrictions,
        "catalog_url": details.catalog_url
    }
    
    return CallToolResult(
        content=[TextContent(type="text", text=str(result))]
    )


async def main():
    """Main entry point for the MCP server."""
    global config, scraper
    
    # Parse command line arguments
    parser = argparse.ArgumentParser(description="Georgia Tech MCP Server")
    parser.add_argument("--config", "-c", help="Path to configuration file")
    parser.add_argument("--host", help="Host to bind to (overrides config)")
    parser.add_argument("--port", type=int, help="Port to bind to (overrides config)")
    parser.add_argument("--log-level", help="Log level (overrides config)")
    args = parser.parse_args()
    
    # Load configuration
    config = load_config(args.config)
    
    # Override config with command line arguments
    if args.host:
        config.server.host = args.host
    if args.port:
        config.server.port = args.port
    if args.log_level:
        config.server.log_level = args.log_level
    
    # Configure logging
    logging.basicConfig(
        level=getattr(logging, config.server.log_level.upper()),
        format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
    )
    
    # Initialize scraper with configuration
    scraper = GTOscarScraper(
        delay=config.scraper.delay,
        timeout=config.scraper.timeout,
        max_retries=config.scraper.max_retries
    )
    
    logger.info(f"Starting Georgia Tech MCP Server on {config.server.host}:{config.server.port}")
    logger.info(f"Scraper configured with {config.scraper.delay}s delay")
    
    async with stdio_server() as streams:
        await server.run(
            streams[0], streams[1], server.create_initialization_options()
        )


if __name__ == "__main__":
    asyncio.run(main())