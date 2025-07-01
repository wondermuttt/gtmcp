"""HTTP-based Georgia Tech MCP Server for ChatGPT integration."""

import argparse
import asyncio
import logging
from typing import Any, Dict, List, Optional
import json

from mcp.server import Server
from mcp.server.streamable_http import StreamableHTTPServerTransport
from mcp.types import (
    CallToolResult,
    ListToolsResult, 
    TextContent,
    Tool,
)

from .config import Config, load_config
from .exceptions import GTMCPError, ScraperError, ToolError
from .models import (
    CourseDetails, CourseInfo, Semester, Subject,
    ResearchPaper, FacultyResearchProfile, CampusLocation,
    RouteOptimization, ResearchEquipment
)
from .clients.oscar_client import OscarClient
from .clients.smartech_client import SMARTechClient
from .clients.places_client import PlacesClient

# Global configuration
config: Config = None
logger = logging.getLogger(__name__)

# Initialize the MCP server
server = Server("gtmcp-http")

# Initialize clients (will be configured in main)
oscar_client: OscarClient = None
smartech_client: SMARTechClient = None
places_client: PlacesClient = None


@server.list_tools()
async def list_tools() -> ListToolsResult:
    """List all available tools across all GT systems."""
    return ListToolsResult(
        tools=[
            # Course & Academic Tools
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
                description="Search for courses by subject, course number, or title",
                inputSchema={
                    "type": "object",
                    "properties": {
                        "term_code": {
                            "type": "string", 
                            "description": "Semester code (e.g., '202502')"
                        },
                        "subject": {
                            "type": "string",
                            "description": "Subject code (e.g., 'CS', 'MATH')"
                        },
                        "course_num": {
                            "type": "string",
                            "description": "Course number filter (optional)"
                        },
                        "title": {
                            "type": "string", 
                            "description": "Course title search filter (optional)"
                        }
                    },
                    "required": ["term_code", "subject"]
                }
            ),
            Tool(
                name="get_course_details",
                description="Get detailed information for a specific course including seats and waitlist",
                inputSchema={
                    "type": "object",
                    "properties": {
                        "term_code": {
                            "type": "string",
                            "description": "Semester code"
                        },
                        "crn": {
                            "type": "string", 
                            "description": "Course Reference Number"
                        }
                    },
                    "required": ["term_code", "crn"]
                }
            ),
            
            # Research & Knowledge Tools
            Tool(
                name="search_research_papers",
                description="Search Georgia Tech research repository for papers by keywords and subjects",
                inputSchema={
                    "type": "object",
                    "properties": {
                        "keywords": {
                            "type": "array",
                            "items": {"type": "string"},
                            "description": "Keywords to search for"
                        },
                        "max_records": {
                            "type": "integer",
                            "description": "Maximum number of records to return (default: 10)",
                            "default": 10
                        }
                    },
                    "required": ["keywords"]
                }
            ),
            
            # System Health Tool
            Tool(
                name="get_system_health_status",
                description="Get health status of all GT systems",
                inputSchema={
                    "type": "object",
                    "properties": {},
                    "required": []
                }
            )
        ]
    )


@server.call_tool()
async def call_tool(name: str, arguments: Dict[str, Any]) -> CallToolResult:
    """Handle tool calls for all GT systems."""
    logger.info(f"HTTP MCP - Calling tool: {name} with arguments: {arguments}")
    
    try:
        if not name:
            raise ToolError("Tool name is required")
        
        # Course & Academic Tools
        if name == "get_available_semesters":
            return await _get_available_semesters(arguments)
        elif name == "get_subjects":
            return await _get_subjects(arguments)
        elif name == "search_courses":
            return await _search_courses(arguments)
        elif name == "get_course_details":
            return await _get_course_details(arguments)
        elif name == "search_research_papers":
            return await _search_research_papers(arguments)
        elif name == "get_system_health_status":
            return await _get_system_health_status(arguments)
        else:
            raise ToolError(f"Unknown tool: {name}")
            
    except Exception as e:
        logger.error(f"Error in tool {name}: {e}")
        raise ToolError(f"Tool execution failed: {e}")


# Tool implementation functions (same as server_expanded.py)
async def _get_available_semesters(arguments: Dict[str, Any]) -> CallToolResult:
    """Get available semesters."""
    try:
        with oscar_client:
            semesters = oscar_client.get_available_semesters()
        
        result_text = f"Found {len(semesters)} available semesters:\n\n"
        
        for semester in semesters:
            view_only_text = " (View Only)" if semester.view_only else ""
            result_text += f"• {semester.name} (Code: {semester.code}){view_only_text}\n"
        
        return CallToolResult(
            content=[TextContent(type="text", text=result_text)]
        )
    except Exception as e:
        raise ToolError(f"Failed to get available semesters: {e}")


async def _get_subjects(arguments: Dict[str, Any]) -> CallToolResult:
    """Get subjects for a semester."""
    term_code = arguments.get("term_code")
    if not term_code:
        raise ToolError("term_code is required")
    
    try:
        with oscar_client:
            subjects = oscar_client.get_subjects(term_code)
        
        result_text = f"Found {len(subjects)} subjects for {term_code}:\n\n"
        
        for subject in subjects:
            result_text += f"• {subject.code}: {subject.name}\n"
        
        return CallToolResult(
            content=[TextContent(type="text", text=result_text)]
        )
    except Exception as e:
        raise ToolError(f"Failed to get subjects: {e}")


async def _search_courses(arguments: Dict[str, Any]) -> CallToolResult:
    """Search for courses."""
    term_code = arguments.get("term_code")
    subject = arguments.get("subject")
    course_num = arguments.get("course_num")
    title = arguments.get("title")
    
    if not term_code or not subject:
        raise ToolError("term_code and subject are required")
    
    try:
        with oscar_client:
            courses = oscar_client.search_courses(term_code, subject, course_num, title)
        
        result_text = f"Found {len(courses)} courses for {subject} in {term_code}:\n\n"
        
        if courses:
            for course in courses:
                result_text += f"• {course.subject} {course.course_number}: {course.title}\n"
                result_text += f"  CRN: {course.crn}, Section: {course.section}\n\n"
        else:
            result_text += "No courses found matching the criteria.\n"
        
        return CallToolResult(
            content=[TextContent(type="text", text=result_text)]
        )
    except Exception as e:
        raise ToolError(f"Failed to search courses: {e}")


async def _get_course_details(arguments: Dict[str, Any]) -> CallToolResult:
    """Get course details."""
    term_code = arguments.get("term_code")
    crn = arguments.get("crn")
    
    if not term_code or not crn:
        raise ToolError("term_code and crn are required")
    
    try:
        with oscar_client:
            details = oscar_client.get_course_details(term_code, crn)
        
        result_text = f"Course Details for CRN {details.crn}:\n\n"
        result_text += f"Title: {details.title}\n"
        result_text += f"Course: {details.subject} {details.course_number} Section {details.section}\n"
        result_text += f"Term: {details.term}\n"
        result_text += f"Credits: {details.credits}\n"
        result_text += f"Schedule Type: {details.schedule_type}\n"
        result_text += f"Campus: {details.campus}\n"
        
        if details.registration:
            result_text += f"\nRegistration Information:\n"
            result_text += f"• Seats: {details.registration.seats_actual}/{details.registration.seats_capacity} ({details.registration.seats_remaining} remaining)\n"
            result_text += f"• Waitlist: {details.registration.waitlist_actual}/{details.registration.waitlist_capacity} ({details.registration.waitlist_remaining} remaining)\n"
        
        return CallToolResult(
            content=[TextContent(type="text", text=result_text)]
        )
    except Exception as e:
        raise ToolError(f"Failed to get course details: {e}")


async def _search_research_papers(arguments: Dict[str, Any]) -> CallToolResult:
    """Search research papers."""
    keywords = arguments.get("keywords", [])
    max_records = arguments.get("max_records", 10)
    
    if not keywords:
        raise ToolError("keywords are required")
    
    try:
        with smartech_client:
            results = smartech_client.search_records(keywords=keywords, max_records=max_records)
        
        papers = results.get('papers', [])
        result_text = f"Found {len(papers)} research papers:\n\n"
        
        for i, paper in enumerate(papers[:max_records], 1):
            result_text += f"{i}. {paper.title}\n"
            result_text += f"   Authors: {', '.join(paper.authors[:3])}\n"
            result_text += f"   Date: {paper.publication_date.strftime('%Y-%m-%d')}\n"
            result_text += f"   Citations: {paper.citation_count}\n\n"
        
        return CallToolResult(
            content=[TextContent(type="text", text=result_text)]
        )
    except Exception as e:
        raise ToolError(f"Failed to search research papers: {e}")


async def _get_system_health_status(arguments: Dict[str, Any]) -> CallToolResult:
    """Get system health status."""
    try:
        health_status = {
            "timestamp": asyncio.get_event_loop().time(),
            "systems": {}
        }
        
        # Check OSCAR health
        try:
            with oscar_client:
                oscar_health = oscar_client.test_connection()
            health_status["systems"]["oscar"] = {
                "status": "healthy" if oscar_health else "unhealthy",
                "service": "OSCAR Course System"
            }
        except Exception as e:
            health_status["systems"]["oscar"] = {
                "status": "error",
                "service": "OSCAR Course System",
                "error": str(e)
            }
        
        # Check SMARTech health
        try:
            with smartech_client:
                smartech_health = smartech_client.test_connection()
            health_status["systems"]["smartech"] = {
                "status": "healthy" if smartech_health else "unhealthy",
                "service": "SMARTech Research Repository"
            }
        except Exception as e:
            health_status["systems"]["smartech"] = {
                "status": "error", 
                "service": "SMARTech Research Repository",
                "error": str(e)
            }
        
        result_text = "GT MCP Server Health Status:\n\n"
        
        for system_name, system_info in health_status["systems"].items():
            status_emoji = "✅" if system_info["status"] == "healthy" else "❌"
            result_text += f"{status_emoji} {system_info['service']}: {system_info['status'].upper()}\n"
            if "error" in system_info:
                result_text += f"   Error: {system_info['error']}\n"
            result_text += "\n"
        
        return CallToolResult(
            content=[TextContent(type="text", text=result_text)]
        )
    except Exception as e:
        raise ToolError(f"Failed to check system health: {e}")


async def main():
    """Main function to run the HTTP MCP server."""
    global config, oscar_client, smartech_client, places_client
    
    # Parse command line arguments
    parser = argparse.ArgumentParser(description="Georgia Tech HTTP MCP Server for ChatGPT")
    parser.add_argument("--config", help="Path to configuration file")
    parser.add_argument("--host", default="localhost", help="Server host")
    parser.add_argument("--port", type=int, default=8000, help="Server port")
    parser.add_argument("--log-level", default="INFO", help="Log level")
    
    args = parser.parse_args()
    
    # Load configuration
    try:
        config = load_config(args.config)
        
        # Apply command line overrides
        if args.host:
            config.server.host = args.host
        if args.port:
            config.server.port = args.port
        if args.log_level:
            config.server.log_level = args.log_level
            
    except Exception as e:
        print(f"Error loading configuration: {e}")
        return 1
    
    # Setup logging
    logging.basicConfig(
        level=getattr(logging, config.server.log_level.upper()),
        format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
    )
    
    logger.info("Starting Georgia Tech HTTP MCP Server for ChatGPT Integration")
    
    # Initialize clients
    try:
        oscar_client = OscarClient(
            delay=config.scraper.delay,
            timeout=config.scraper.timeout,
            max_retries=config.scraper.max_retries
        )
        
        smartech_client = SMARTechClient(
            timeout=config.scraper.timeout,
            max_retries=config.scraper.max_retries
        )
        
        places_client = PlacesClient(
            timeout=config.scraper.timeout,
            max_retries=config.scraper.max_retries
        )
        
        logger.info("All clients initialized successfully")
        
    except Exception as e:
        logger.error(f"Error initializing clients: {e}")
        return 1
    
    # Start HTTP server
    logger.info(f"Starting GT MCP HTTP Server on {args.host}:{args.port}")
    logger.info("Ready for ChatGPT integration")
    
    # Create HTTP transport
    transport = StreamableHTTPServerTransport(args.host, args.port)
    
    # Run the server with HTTP transport
    await server.run(transport)


if __name__ == "__main__":
    import sys
    sys.exit(asyncio.run(main()))