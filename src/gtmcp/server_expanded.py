"""Expanded Georgia Tech MCP Server with multi-system integration."""

import argparse
import asyncio
import logging
from typing import Any, Dict, List, Optional
import json

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
server = Server("gtmcp-expanded")

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
                        "subject_areas": {
                            "type": "array", 
                            "items": {"type": "string"},
                            "description": "Subject areas to filter by"
                        },
                        "date_from": {
                            "type": "string",
                            "description": "Start date for search (YYYY-MM-DD)"
                        },
                        "date_until": {
                            "type": "string",
                            "description": "End date for search (YYYY-MM-DD)"
                        },
                        "max_results": {
                            "type": "integer",
                            "description": "Maximum number of results to return",
                            "default": 50
                        }
                    },
                    "required": []
                }
            ),
            Tool(
                name="find_faculty_research",
                description="Find faculty research profiles and interests by research area",
                inputSchema={
                    "type": "object",
                    "properties": {
                        "research_area": {
                            "type": "string",
                            "description": "Research area to search for (e.g., 'robotics', 'AI')"
                        }
                    },
                    "required": ["research_area"]
                }
            ),
            Tool(
                name="analyze_research_trends",
                description="Analyze research trends over time for given keywords",
                inputSchema={
                    "type": "object",
                    "properties": {
                        "keywords": {
                            "type": "array",
                            "items": {"type": "string"},
                            "description": "Keywords to analyze trends for"
                        },
                        "years": {
                            "type": "integer",
                            "description": "Number of years to analyze",
                            "default": 5
                        }
                    },
                    "required": ["keywords"]
                }
            ),
            Tool(
                name="get_repository_info",
                description="Get information about the Georgia Tech research repository",
                inputSchema={
                    "type": "object",
                    "properties": {},
                    "required": []
                }
            ),
            
            # Campus & Location Tools
            Tool(
                name="search_campus_locations",
                description="Search for campus buildings and locations by name or services",
                inputSchema={
                    "type": "object",
                    "properties": {
                        "query": {
                            "type": "string",
                            "description": "Search query for building/location name"
                        },
                        "services": {
                            "type": "array",
                            "items": {"type": "string"},
                            "description": "Required services (e.g., 'AV equipment', 'catering')"
                        },
                        "accessible": {
                            "type": "boolean",
                            "description": "Filter for wheelchair accessible locations",
                            "default": false
                        }
                    },
                    "required": []
                }
            ),
            Tool(
                name="get_location_details",
                description="Get detailed information about a specific campus location",
                inputSchema={
                    "type": "object",
                    "properties": {
                        "building_id": {
                            "type": "string",
                            "description": "Building ID or identifier"
                        }
                    },
                    "required": ["building_id"]
                }
            ),
            Tool(
                name="find_nearby_locations",
                description="Find locations near a specific building or area",
                inputSchema={
                    "type": "object",
                    "properties": {
                        "center_building_id": {
                            "type": "string",
                            "description": "Building ID to search around"
                        },
                        "radius_meters": {
                            "type": "integer",
                            "description": "Search radius in meters",
                            "default": 500
                        },
                        "services": {
                            "type": "array",
                            "items": {"type": "string"},
                            "description": "Required services to filter by"
                        }
                    },
                    "required": ["center_building_id"]
                }
            ),
            Tool(
                name="get_accessibility_info",
                description="Get detailed accessibility information for a building",
                inputSchema={
                    "type": "object",
                    "properties": {
                        "building_id": {
                            "type": "string",
                            "description": "Building ID to get accessibility info for"
                        }
                    },
                    "required": ["building_id"]
                }
            ),
            
            # Cross-System Integration Tools
            Tool(
                name="suggest_research_collaborators",
                description="Suggest potential research collaborators based on research interests",
                inputSchema={
                    "type": "object",
                    "properties": {
                        "research_area": {
                            "type": "string",
                            "description": "Research area for collaboration"
                        },
                        "keywords": {
                            "type": "array",
                            "items": {"type": "string"},
                            "description": "Specific research keywords"
                        }
                    },
                    "required": ["research_area"]
                }
            ),
            Tool(
                name="find_courses_for_research",
                description="Find courses related to a specific research area or topic",
                inputSchema={
                    "type": "object",
                    "properties": {
                        "research_topic": {
                            "type": "string",
                            "description": "Research topic or area"
                        },
                        "term_code": {
                            "type": "string",
                            "description": "Semester to search in"
                        }
                    },
                    "required": ["research_topic"]
                }
            ),
            Tool(
                name="check_system_health",
                description="Check the health status of all integrated GT systems",
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
    logger.info(f"Calling tool: {name} with arguments: {arguments}")
    
    try:
        if not name:
            raise ToolError("Tool name is required")
        
        # Course & Academic Tools
        if name == "get_available_semesters":
            return await _get_available_semesters()
        elif name == "get_subjects":
            return await _get_subjects(arguments)
        elif name == "search_courses":
            return await _search_courses(arguments)
        elif name == "get_course_details":
            return await _get_course_details(arguments)
            
        # Research & Knowledge Tools
        elif name == "search_research_papers":
            return await _search_research_papers(arguments)
        elif name == "find_faculty_research":
            return await _find_faculty_research(arguments)
        elif name == "analyze_research_trends":
            return await _analyze_research_trends(arguments)
        elif name == "get_repository_info":
            return await _get_repository_info()
            
        # Campus & Location Tools
        elif name == "search_campus_locations":
            return await _search_campus_locations(arguments)
        elif name == "get_location_details":
            return await _get_location_details(arguments)
        elif name == "find_nearby_locations":
            return await _find_nearby_locations(arguments)
        elif name == "get_accessibility_info":
            return await _get_accessibility_info(arguments)
            
        # Cross-System Integration Tools
        elif name == "suggest_research_collaborators":
            return await _suggest_research_collaborators(arguments)
        elif name == "find_courses_for_research":
            return await _find_courses_for_research(arguments)
        elif name == "check_system_health":
            return await _check_system_health()
        
        else:
            raise ToolError(f"Unknown tool: {name}")
            
    except Exception as e:
        logger.error(f"Error in tool {name}: {e}")
        return CallToolResult(
            content=[TextContent(type="text", text=f"Error: {str(e)}")],
            isError=True
        )


# Course & Academic Tool Implementations
async def _get_available_semesters() -> CallToolResult:
    """Get available semesters from OSCAR."""
    try:
        with oscar_client as client:
            semesters = client.get_available_semesters()
            
        result_text = f"Found {len(semesters)} available semesters:\n\n"
        for semester in semesters:
            status = " (View Only)" if semester.view_only else ""
            result_text += f"• {semester.name} (Code: {semester.code}){status}\n"
        
        return CallToolResult(
            content=[TextContent(type="text", text=result_text)]
        )
    except Exception as e:
        raise ToolError(f"Failed to get available semesters: {e}")


async def _get_subjects(arguments: Dict[str, Any]) -> CallToolResult:
    """Get subjects for a given term."""
    term_code = arguments.get("term_code")
    if not term_code:
        raise ToolError("term_code is required")
    
    try:
        with oscar_client as client:
            subjects = client.get_subjects(term_code)
            
        result_text = f"Found {len(subjects)} subjects for term {term_code}:\n\n"
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
        with oscar_client as client:
            courses = client.search_courses(term_code, subject, course_num, title)
            
        result_text = f"Found {len(courses)} courses for {subject} in {term_code}:\n\n"
        for course in courses[:20]:  # Limit to first 20 results
            result_text += f"• CRN {course.crn}: {course.title}\n"
            result_text += f"  {course.subject} {course.course_number} Section {course.section}\n\n"
        
        if len(courses) > 20:
            result_text += f"... and {len(courses) - 20} more courses\n"
        
        return CallToolResult(
            content=[TextContent(type="text", text=result_text)]
        )
    except Exception as e:
        raise ToolError(f"Failed to search courses: {e}")


async def _get_course_details(arguments: Dict[str, Any]) -> CallToolResult:
    """Get detailed course information."""
    term_code = arguments.get("term_code")
    crn = arguments.get("crn")
    
    if not term_code or not crn:
        raise ToolError("term_code and crn are required")
    
    try:
        with oscar_client as client:
            details = client.get_course_details(term_code, crn)
            
        result_text = f"Course Details for CRN {details.crn}:\n\n"
        result_text += f"Title: {details.title}\n"
        result_text += f"Course: {details.subject} {details.course_number} Section {details.section}\n"
        result_text += f"Term: {details.term}\n"
        result_text += f"Credits: {details.credits}\n"
        result_text += f"Schedule Type: {details.schedule_type}\n"
        result_text += f"Campus: {details.campus}\n"
        result_text += f"Levels: {', '.join(details.levels)}\n\n"
        
        result_text += "Registration Information:\n"
        result_text += f"• Seats: {details.registration.seats_actual}/{details.registration.seats_capacity} "
        result_text += f"({details.registration.seats_remaining} remaining)\n"
        result_text += f"• Waitlist: {details.registration.waitlist_actual}/{details.registration.waitlist_capacity} "
        result_text += f"({details.registration.waitlist_remaining} remaining)\n\n"
        
        if details.restrictions:
            result_text += f"Restrictions: {', '.join(details.restrictions)}\n\n"
        
        if details.catalog_url:
            result_text += f"Catalog URL: {details.catalog_url}\n"
        
        return CallToolResult(
            content=[TextContent(type="text", text=result_text)]
        )
    except Exception as e:
        raise ToolError(f"Failed to get course details: {e}")


# Research & Knowledge Tool Implementations
async def _search_research_papers(arguments: Dict[str, Any]) -> CallToolResult:
    """Search research papers in SMARTech repository."""
    keywords = arguments.get("keywords", [])
    subject_areas = arguments.get("subject_areas", [])
    date_from = arguments.get("date_from")
    date_until = arguments.get("date_until")
    max_results = arguments.get("max_results", 50)
    
    try:
        with smartech_client as client:
            results = client.search_records(
                keywords=keywords,
                subject_areas=subject_areas,
                date_from=date_from,
                date_until=date_until,
                max_records=max_results
            )
            
        papers = results['papers']
        
        result_text = f"Found {len(papers)} research papers"
        if keywords:
            result_text += f" for keywords: {', '.join(keywords)}"
        if subject_areas:
            result_text += f" in areas: {', '.join(subject_areas)}"
        result_text += "\n\n"
        
        for paper in papers[:10]:  # Show first 10
            result_text += f"• {paper.title}\n"
            result_text += f"  Authors: {', '.join(paper.authors[:3])}\n"
            if len(paper.authors) > 3:
                result_text += f"  ... and {len(paper.authors) - 3} more authors\n"
            result_text += f"  Published: {paper.publication_date.strftime('%Y-%m-%d')}\n"
            result_text += f"  Subject Areas: {', '.join(paper.subject_areas[:3])}\n"
            if paper.abstract:
                abstract_preview = paper.abstract[:200] + "..." if len(paper.abstract) > 200 else paper.abstract
                result_text += f"  Abstract: {abstract_preview}\n"
            result_text += "\n"
        
        if len(papers) > 10:
            result_text += f"... and {len(papers) - 10} more papers\n"
        
        return CallToolResult(
            content=[TextContent(type="text", text=result_text)]
        )
    except Exception as e:
        raise ToolError(f"Failed to search research papers: {e}")


async def _find_faculty_research(arguments: Dict[str, Any]) -> CallToolResult:
    """Find faculty research profiles."""
    research_area = arguments.get("research_area")
    if not research_area:
        raise ToolError("research_area is required")
    
    try:
        with smartech_client as client:
            profiles = client.find_faculty_research(research_area)
            
        result_text = f"Found {len(profiles)} faculty members with research in '{research_area}':\n\n"
        
        for profile in profiles[:10]:  # Show first 10
            result_text += f"• {profile.name}\n"
            if profile.department:
                result_text += f"  Department: {profile.department}\n"
            result_text += f"  Research Interests: {', '.join(profile.research_interests[:5])}\n"
            result_text += f"  Recent Publications: {len(profile.recent_publications)} papers\n"
            
            if profile.recent_publications:
                recent_paper = profile.recent_publications[0]
                result_text += f"  Latest Paper: {recent_paper.title} ({recent_paper.publication_date.year})\n"
            result_text += "\n"
        
        if len(profiles) > 10:
            result_text += f"... and {len(profiles) - 10} more faculty members\n"
        
        return CallToolResult(
            content=[TextContent(type="text", text=result_text)]
        )
    except Exception as e:
        raise ToolError(f"Failed to find faculty research: {e}")


async def _analyze_research_trends(arguments: Dict[str, Any]) -> CallToolResult:
    """Analyze research trends over time."""
    keywords = arguments.get("keywords", [])
    years = arguments.get("years", 5)
    
    if not keywords:
        raise ToolError("keywords are required")
    
    try:
        with smartech_client as client:
            trends = client.analyze_research_trends(keywords, years)
            
        result_text = f"Research Trends Analysis for: {', '.join(keywords)}\n\n"
        result_text += f"Total Papers ({years} years): {trends['total_papers']}\n"
        result_text += f"Trend Direction: {trends['trend_direction']}\n"
        result_text += f"Peak Year: {trends['peak_year']}\n"
        result_text += f"Average per Year: {trends['average_per_year']:.1f}\n\n"
        
        result_text += "Year-by-Year Breakdown:\n"
        for year, data in trends['trends_by_year'].items():
            result_text += f"• {year}: {data['count']} papers\n"
        
        return CallToolResult(
            content=[TextContent(type="text", text=result_text)]
        )
    except Exception as e:
        raise ToolError(f"Failed to analyze research trends: {e}")


async def _get_repository_info() -> CallToolResult:
    """Get repository information."""
    try:
        with smartech_client as client:
            info = client.get_repository_info()
            
        result_text = "Georgia Tech Research Repository Information:\n\n"
        for key, value in info.items():
            if key and value:
                # Format key names nicely
                formatted_key = key.replace('_', ' ').title()
                result_text += f"• {formatted_key}: {value}\n"
        
        return CallToolResult(
            content=[TextContent(type="text", text=result_text)]
        )
    except Exception as e:
        raise ToolError(f"Failed to get repository info: {e}")


# Campus & Location Tool Implementations
async def _search_campus_locations(arguments: Dict[str, Any]) -> CallToolResult:
    """Search campus locations."""
    query = arguments.get("query")
    services = arguments.get("services", [])
    accessible = arguments.get("accessible", False)
    
    try:
        with places_client as client:
            locations = client.search_locations(
                query=query,
                services=services,
                accessible=accessible
            )
            
        result_text = f"Found {len(locations)} campus locations"
        if query:
            result_text += f" matching '{query}'"
        if services:
            result_text += f" with services: {', '.join(services)}"
        if accessible:
            result_text += " (wheelchair accessible)"
        result_text += "\n\n"
        
        for location in locations[:15]:  # Show first 15
            result_text += f"• {location.building_name}\n"
            if location.address:
                result_text += f"  Address: {location.address}\n"
            if location.available_services:
                result_text += f"  Services: {', '.join(location.available_services[:3])}\n"
            if location.accessibility_features:
                result_text += f"  Accessibility: {', '.join(location.accessibility_features)}\n"
            result_text += "\n"
        
        if len(locations) > 15:
            result_text += f"... and {len(locations) - 15} more locations\n"
        
        return CallToolResult(
            content=[TextContent(type="text", text=result_text)]
        )
    except Exception as e:
        raise ToolError(f"Failed to search campus locations: {e}")


async def _get_location_details(arguments: Dict[str, Any]) -> CallToolResult:
    """Get detailed location information."""
    building_id = arguments.get("building_id")
    if not building_id:
        raise ToolError("building_id is required")
    
    try:
        with places_client as client:
            location = client.get_location_by_id(building_id)
            
        if not location:
            return CallToolResult(
                content=[TextContent(type="text", text=f"No location found with ID: {building_id}")]
            )
            
        result_text = f"Location Details for {location.building_name}:\n\n"
        result_text += f"Building ID: {location.building_id}\n"
        if location.address:
            result_text += f"Address: {location.address}\n"
        if location.gps_coordinates:
            lat, lon = location.gps_coordinates
            result_text += f"Coordinates: {lat:.6f}, {lon:.6f}\n"
        
        if location.available_services:
            result_text += f"\nAvailable Services:\n"
            for service in location.available_services:
                result_text += f"• {service}\n"
        
        if location.accessibility_features:
            result_text += f"\nAccessibility Features:\n"
            for feature in location.accessibility_features:
                result_text += f"• {feature}\n"
        
        if location.operating_hours:
            result_text += f"\nOperating Hours:\n"
            for day, hours in location.operating_hours.items():
                result_text += f"• {day}: {hours}\n"
        
        if location.capacity_info:
            result_text += f"\nCapacity Information:\n"
            for capacity_type, count in location.capacity_info.items():
                result_text += f"• {capacity_type}: {count}\n"
        
        return CallToolResult(
            content=[TextContent(type="text", text=result_text)]
        )
    except Exception as e:
        raise ToolError(f"Failed to get location details: {e}")


async def _find_nearby_locations(arguments: Dict[str, Any]) -> CallToolResult:
    """Find nearby locations."""
    center_building_id = arguments.get("center_building_id")
    radius_meters = arguments.get("radius_meters", 500)
    services = arguments.get("services", [])
    
    if not center_building_id:
        raise ToolError("center_building_id is required")
    
    try:
        with places_client as client:
            # First get the center location
            center_location = client.get_location_by_id(center_building_id)
            if not center_location:
                raise ToolError(f"Center location not found: {center_building_id}")
            
            nearby_locations = client.find_nearby_locations(
                center_location=center_location,
                radius_meters=radius_meters,
                services=services
            )
            
        result_text = f"Found {len(nearby_locations)} locations within {radius_meters}m of {center_location.building_name}"
        if services:
            result_text += f" with services: {', '.join(services)}"
        result_text += "\n\n"
        
        for location in nearby_locations[:10]:  # Show first 10
            result_text += f"• {location.building_name}\n"
            if location.address:
                result_text += f"  Address: {location.address}\n"
            if location.available_services:
                result_text += f"  Services: {', '.join(location.available_services[:3])}\n"
            result_text += "\n"
        
        if len(nearby_locations) > 10:
            result_text += f"... and {len(nearby_locations) - 10} more locations\n"
        
        return CallToolResult(
            content=[TextContent(type="text", text=result_text)]
        )
    except Exception as e:
        raise ToolError(f"Failed to find nearby locations: {e}")


async def _get_accessibility_info(arguments: Dict[str, Any]) -> CallToolResult:
    """Get accessibility information."""
    building_id = arguments.get("building_id")
    if not building_id:
        raise ToolError("building_id is required")
    
    try:
        with places_client as client:
            accessibility = client.get_accessibility_info(building_id)
            
        result_text = f"Accessibility Information for Building {building_id}:\n\n"
        
        result_text += f"Wheelchair Accessible: {'Yes' if accessibility['wheelchair_accessible'] else 'No'}\n"
        result_text += f"Elevator Access: {'Yes' if accessibility['elevator_access'] else 'No'}\n"
        
        if accessibility['accessible_entrances']:
            result_text += f"\nAccessible Entrances:\n"
            for entrance in accessibility['accessible_entrances']:
                result_text += f"• {entrance}\n"
        
        if accessibility['accessible_restrooms']:
            result_text += f"\nAccessible Restrooms:\n"
            for restroom in accessibility['accessible_restrooms']:
                result_text += f"• {restroom}\n"
        
        if accessibility['accessible_parking']:
            result_text += f"\nAccessible Parking:\n"
            for parking in accessibility['accessible_parking']:
                result_text += f"• {parking}\n"
        
        if accessibility['assistance_services']:
            result_text += f"\nAssistance Services:\n"
            for service in accessibility['assistance_services']:
                result_text += f"• {service}\n"
        
        if accessibility['notes']:
            result_text += f"\nAdditional Notes:\n{accessibility['notes']}\n"
        
        return CallToolResult(
            content=[TextContent(type="text", text=result_text)]
        )
    except Exception as e:
        raise ToolError(f"Failed to get accessibility info: {e}")


# Cross-System Integration Tools
async def _suggest_research_collaborators(arguments: Dict[str, Any]) -> CallToolResult:
    """Suggest research collaborators."""
    research_area = arguments.get("research_area")
    keywords = arguments.get("keywords", [])
    
    if not research_area:
        raise ToolError("research_area is required")
    
    try:
        # Find faculty in the research area
        with smartech_client as client:
            faculty_profiles = client.find_faculty_research(research_area)
            
        # Also search for recent papers to find additional collaborators
        search_keywords = [research_area] + keywords
        with smartech_client as client:
            recent_papers = client.search_records(
                keywords=search_keywords,
                max_records=100
            )
            
        result_text = f"Research Collaboration Suggestions for '{research_area}':\n\n"
        
        # Top faculty by publication count
        result_text += "Top Faculty Researchers:\n"
        for profile in faculty_profiles[:5]:
            result_text += f"• {profile.name}\n"
            result_text += f"  Research Interests: {', '.join(profile.research_interests[:3])}\n"
            result_text += f"  Recent Publications: {len(profile.recent_publications)}\n"
            if profile.recent_publications:
                latest = profile.recent_publications[0]
                result_text += f"  Latest: {latest.title} ({latest.publication_date.year})\n"
            result_text += "\n"
        
        # Recent active researchers
        if recent_papers['papers']:
            result_text += "Recently Active Researchers:\n"
            recent_authors = {}
            for paper in recent_papers['papers'][:20]:
                for author in paper.authors:
                    clean_author = author.split(',')[0].strip()  # Remove affiliations
                    if clean_author not in recent_authors:
                        recent_authors[clean_author] = []
                    recent_authors[clean_author].append(paper)
            
            # Sort by recent activity
            sorted_authors = sorted(recent_authors.items(), 
                                  key=lambda x: len(x[1]), reverse=True)
            
            for author, papers in sorted_authors[:5]:
                result_text += f"• {author}\n"
                result_text += f"  Recent Papers: {len(papers)}\n"
                if papers:
                    result_text += f"  Latest: {papers[0].title} ({papers[0].publication_date.year})\n"
                result_text += "\n"
        
        return CallToolResult(
            content=[TextContent(type="text", text=result_text)]
        )
    except Exception as e:
        raise ToolError(f"Failed to suggest collaborators: {e}")


async def _find_courses_for_research(arguments: Dict[str, Any]) -> CallToolResult:
    """Find courses related to research topic."""
    research_topic = arguments.get("research_topic")
    term_code = arguments.get("term_code")
    
    if not research_topic:
        raise ToolError("research_topic is required")
    
    try:
        # If no term code provided, get the latest semester
        if not term_code:
            with oscar_client as client:
                semesters = client.get_available_semesters()
                # Get the most recent non-view-only semester
                current_semesters = [s for s in semesters if not s.view_only]
                if current_semesters:
                    term_code = current_semesters[0].code
                else:
                    raise ToolError("No current semesters available")
        
        # Get subjects to search through
        with oscar_client as client:
            subjects = client.get_subjects(term_code)
            
        # Search for relevant subjects based on research topic
        relevant_subjects = []
        topic_words = research_topic.lower().split()
        
        for subject in subjects:
            subject_text = f"{subject.code} {subject.name}".lower()
            if any(word in subject_text for word in topic_words):
                relevant_subjects.append(subject)
        
        # If no obviously relevant subjects, try common ones
        if not relevant_subjects:
            common_codes = ['CS', 'ECE', 'MATH', 'PHYS', 'CHEM', 'BIOL', 'ME', 'AE']
            relevant_subjects = [s for s in subjects if s.code in common_codes]
        
        result_text = f"Courses related to '{research_topic}' in {term_code}:\n\n"
        
        found_courses = []
        # Search courses in relevant subjects
        for subject in relevant_subjects[:5]:  # Limit subjects to search
            try:
                with oscar_client as client:
                    courses = client.search_courses(term_code, subject.code)
                    
                # Filter courses by research topic relevance
                for course in courses:
                    course_text = f"{course.title} {course.subject} {course.course_number}".lower()
                    if any(word in course_text for word in topic_words):
                        found_courses.append((course, subject.name))
                        
            except Exception as e:
                logger.warning(f"Error searching courses in {subject.code}: {e}")
                continue
        
        if found_courses:
            result_text += f"Found {len(found_courses)} relevant courses:\n\n"
            for course, subject_name in found_courses[:15]:  # Show first 15
                result_text += f"• {course.subject} {course.course_number}: {course.title}\n"
                result_text += f"  CRN: {course.crn}, Section: {course.section}\n"
                result_text += f"  Subject Area: {subject_name}\n\n"
                
            if len(found_courses) > 15:
                result_text += f"... and {len(found_courses) - 15} more courses\n"
        else:
            result_text += f"No courses found directly matching '{research_topic}'.\n"
            result_text += f"Consider searching in these relevant subjects:\n"
            for subject in relevant_subjects[:10]:
                result_text += f"• {subject.code}: {subject.name}\n"
        
        return CallToolResult(
            content=[TextContent(type="text", text=result_text)]
        )
    except Exception as e:
        raise ToolError(f"Failed to find courses for research: {e}")


async def _check_system_health() -> CallToolResult:
    """Check health of all GT systems."""
    try:
        health_status = {
            "timestamp": asyncio.get_event_loop().time(),
            "systems": {}
        }
        
        # Check OSCAR system
        try:
            with oscar_client as client:
                oscar_health = client.get_health_status()
                health_status["systems"]["OSCAR"] = oscar_health
        except Exception as e:
            health_status["systems"]["OSCAR"] = {
                "status": "error",
                "error": str(e)
            }
        
        # Check SMARTech system
        try:
            with smartech_client as client:
                smartech_health = client.get_health_status()
                health_status["systems"]["SMARTech"] = smartech_health
        except Exception as e:
            health_status["systems"]["SMARTech"] = {
                "status": "error", 
                "error": str(e)
            }
        
        # Check Places system
        try:
            with places_client as client:
                places_health = client.get_health_status()
                health_status["systems"]["Places"] = places_health
        except Exception as e:
            health_status["systems"]["Places"] = {
                "status": "error",
                "error": str(e)
            }
        
        # Format results
        result_text = "Georgia Tech Systems Health Check:\n\n"
        
        for system_name, status in health_status["systems"].items():
            result_text += f"• {system_name}: {status['status'].upper()}\n"
            if status['status'] == 'error':
                result_text += f"  Error: {status.get('error', 'Unknown error')}\n"
            elif 'base_url' in status:
                result_text += f"  Endpoint: {status['base_url']}\n"
            result_text += "\n"
        
        # Overall status
        all_healthy = all(s['status'] == 'healthy' for s in health_status["systems"].values())
        overall_status = "All systems operational" if all_healthy else "Some systems have issues"
        result_text += f"Overall Status: {overall_status}\n"
        
        return CallToolResult(
            content=[TextContent(type="text", text=result_text)]
        )
    except Exception as e:
        raise ToolError(f"Failed to check system health: {e}")


async def main():
    """Main function to run the expanded MCP server."""
    global config, oscar_client, smartech_client, places_client
    
    # Parse command line arguments
    parser = argparse.ArgumentParser(description="Georgia Tech Expanded MCP Server")
    parser.add_argument("--config", help="Path to configuration file")
    parser.add_argument("--host", help="Override server host")
    parser.add_argument("--port", type=int, help="Override server port")
    parser.add_argument("--log-level", help="Override log level")
    
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
    
    logger.info("Starting Georgia Tech Expanded MCP Server")
    
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
    
    # Start server
    logger.info(f"Starting Georgia Tech Expanded MCP Server")
    logger.info(f"Course system delay: {config.scraper.delay}s")
    
    # Run stdio server
    async with stdio_server() as streams:
        await server.run(
            streams[0], streams[1],
            server.create_initialization_options()
        )


if __name__ == "__main__":
    import sys
    sys.exit(asyncio.run(main()))