"""FastAPI-based HTTP server for ChatGPT MCP integration."""

import asyncio
import argparse
import json
import logging
from typing import Any, Dict, List, Optional
from pydantic import BaseModel
from contextlib import asynccontextmanager

from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from fastapi.staticfiles import StaticFiles
import uvicorn

from .config import Config, load_config
from .clients.oscar_client import OscarClient
from .clients.smartech_client import SMARTechClient
from .clients.places_client import PlacesClient

# Global configuration and clients
config: Config = None
oscar_client: OscarClient = None
smartech_client: SMARTechClient = None
places_client: PlacesClient = None
logger = logging.getLogger(__name__)


@asynccontextmanager
async def lifespan(app: FastAPI):
    """Application lifespan manager."""
    global config, oscar_client, smartech_client, places_client
    
    # Initialize clients on startup
    logger.info("Initializing GT MCP clients...")
    
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
    
    yield
    
    # Cleanup on shutdown
    logger.info("Shutting down GT MCP server...")


# Create FastAPI app
app = FastAPI(
    title="Georgia Tech MCP Server",
    description="HTTP API for Georgia Tech course schedules, research papers, and campus information",
    version="2.1.0",
    lifespan=lifespan
)

# Add CORS middleware for ChatGPT integration
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # ChatGPT needs access
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


@app.get("/",
         tags=["Server Info"],
         summary="Server information",
         description="Get basic server information, features, and available endpoints",
         response_description="Server metadata and endpoint listing")
async def root():
    """Get server information, features, and available endpoints."""
    return {
        "name": "Georgia Tech MCP Server",
        "version": "2.1.0",
        "description": "HTTP API for GT course schedules, research papers, and campus information",
        "features": [
            "OSCAR course search with 500 error fixes",
            "Research paper search",
            "System health monitoring"
        ],
        "endpoints": {
            "health": "/health",
            "tools": "/tools",
            "semesters": "/api/semesters",
            "subjects": "/api/subjects/{term_code}",
            "courses": "/api/courses",
            "course_details": "/api/courses/{term_code}/{crn}",
            "research": "/api/research",
            "openapi": "/openapi.json",
            "ai_plugin": "/.well-known/ai-plugin.json"
        }
    }


@app.get("/.well-known/ai-plugin.json")
async def ai_plugin_manifest():
    """ChatGPT AI Plugin manifest for discovery."""
    # Get the server configuration for the correct base URL
    global config
    
    # Determine the base URL - use the configured host/port
    if config and hasattr(config, 'server'):
        host = config.server.host if config.server.host != "0.0.0.0" else "localhost"
        port = config.server.port
        base_url = f"http://{host}:{port}"
    else:
        # Fallback if config not available
        base_url = "http://localhost:8080"
    
    return {
        "schema_version": "v1",
        "name_for_human": "GT MCP Server",
        "name_for_model": "gt_mcp",
        "description_for_human": "Access Georgia Tech course schedules, research papers, and campus information.",
        "description_for_model": "Plugin for accessing Georgia Tech courses, semesters, subjects, course details, and research papers. Provides comprehensive access to OSCAR course system and SMARTech research repository with 500 error fixes applied.",
        "auth": {
            "type": "none"
        },
        "api": {
            "type": "openapi",
            "url": f"{base_url}/openapi.json",
            "is_user_authenticated": False
        },
        "logo_url": f"{base_url}/static/logo.png",
        "contact_email": "support@gtmcp.example.com",
        "legal_info_url": f"{base_url}/legal"
    }


@app.get("/legal")
async def legal_info():
    """Legal information endpoint."""
    return {
        "service_name": "Georgia Tech MCP Server",
        "version": "2.1.0",
        "terms_of_service": "This service provides access to publicly available Georgia Tech course and research information. Use of this service is subject to Georgia Tech's acceptable use policies.",
        "privacy_policy": "This service does not collect or store personal information. All data accessed is publicly available through Georgia Tech's official systems.",
        "disclaimer": "This is an unofficial service not affiliated with Georgia Tech. Course and research information is provided as-is without warranty.",
        "data_sources": [
            "Georgia Tech OSCAR course system",
            "Georgia Tech SMARTech research repository"
        ],
        "contact": "For questions about this service, please refer to the source code repository.",
        "last_updated": "2024-01-01"
    }


# Mount static files for logo and other assets
# Note: Create a static directory with logo.png if needed
try:
    app.mount("/static", StaticFiles(directory="static"), name="static")
except RuntimeError:
    # Static directory doesn't exist, that's okay
    pass


@app.get("/health",
         tags=["Server Info"],
         summary="Health check",
         description="Check the health status of the server and connected services",
         response_description="Health status of server and all integrated services")
async def health_check():
    """Check the health status of the server and all connected services."""
    health_status = {
        "status": "healthy",
        "timestamp": asyncio.get_event_loop().time(),
        "services": {}
    }
    
    # Check OSCAR
    try:
        with oscar_client:
            oscar_healthy = oscar_client.test_connection()
        health_status["services"]["oscar"] = {
            "status": "healthy" if oscar_healthy else "unhealthy",
            "name": "OSCAR Course System"
        }
    except Exception as e:
        health_status["services"]["oscar"] = {
            "status": "error",
            "name": "OSCAR Course System",
            "error": str(e)
        }
    
    # Check SMARTech
    try:
        with smartech_client:
            smartech_healthy = smartech_client.test_connection()
        health_status["services"]["smartech"] = {
            "status": "healthy" if smartech_healthy else "unhealthy",
            "name": "SMARTech Research Repository"
        }
    except Exception as e:
        health_status["services"]["smartech"] = {
            "status": "error",
            "name": "SMARTech Research Repository",
            "error": str(e)
        }
    
    return health_status


@app.get("/tools",
         tags=["Server Info"],
         summary="List MCP tools",
         description="Get list of available MCP tools and their parameters",
         response_description="Complete list of MCP tools with descriptions and parameters")
async def list_tools():
    """Get list of available MCP tools and their parameters."""
    return {
        "tools": [
            {
                "name": "get_available_semesters",
                "description": "Get list of available semesters for course searches",
                "parameters": {}
            },
            {
                "name": "get_subjects",
                "description": "Get list of available subjects/departments for a given semester",
                "parameters": {
                    "term_code": "string (required) - Semester code (e.g., '202502')"
                }
            },
            {
                "name": "search_courses",
                "description": "Search for courses by subject, course number, or title",
                "parameters": {
                    "term_code": "string (required) - Semester code",
                    "subject": "string (required) - Subject code (e.g., 'CS')",
                    "course_num": "string (optional) - Course number filter",
                    "title": "string (optional) - Course title filter"
                }
            },
            {
                "name": "get_course_details",
                "description": "Get detailed information for a specific course",
                "parameters": {
                    "term_code": "string (required) - Semester code",
                    "crn": "string (required) - Course Reference Number"
                }
            },
            {
                "name": "search_research_papers",
                "description": "Search research papers in GT repository",
                "parameters": {
                    "keywords": "array (required) - Keywords to search for",
                    "max_records": "integer (optional) - Maximum records to return"
                }
            }
        ]
    }


@app.get("/api/semesters", 
         tags=["Academic"],
         summary="Get available semesters",
         description="Retrieve list of available academic semesters for course searches",
         response_description="List of semesters with codes, names, and availability status")
async def get_available_semesters():
    """Get available semesters for course searches."""
    try:
        with oscar_client:
            semesters = oscar_client.get_available_semesters()
        
        return {
            "count": len(semesters),
            "semesters": [
                {
                    "code": semester.code,
                    "name": semester.name,
                    "view_only": semester.view_only
                }
                for semester in semesters
            ]
        }
    except Exception as e:
        logger.error(f"Error getting semesters: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@app.get("/api/subjects/{term_code}",
         tags=["Academic"],
         summary="Get subjects for semester",
         description="Retrieve available subjects/departments for a specific semester",
         response_description="List of subjects with codes and names")
async def get_subjects(term_code: str):
    """Get available subjects/departments for a specific semester."""
    try:
        with oscar_client:
            subjects = oscar_client.get_subjects(term_code)
        
        return {
            "term_code": term_code,
            "count": len(subjects),
            "subjects": [
                {
                    "code": subject.code,
                    "name": subject.name
                }
                for subject in subjects
            ]
        }
    except Exception as e:
        logger.error(f"Error getting subjects: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@app.get("/api/courses",
         tags=["Academic"],
         summary="Search courses",
         description="Search for courses by semester, subject, course number, or title",
         response_description="List of matching courses with details")
async def search_courses(
    term_code: str,
    subject: str,
    course_num: Optional[str] = None,
    title: Optional[str] = None
):
    """Search for courses by semester, subject, course number, or title."""
    try:
        with oscar_client:
            courses = oscar_client.search_courses(term_code, subject, course_num, title)
        
        return {
            "term_code": term_code,
            "subject": subject,
            "count": len(courses),
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
    except Exception as e:
        logger.error(f"Error searching courses: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@app.get("/api/courses/{term_code}/{crn}",
         tags=["Academic"],
         summary="Get course details",
         description="Get detailed information for a specific course including registration info",
         response_description="Detailed course information with seats, waitlist, and restrictions")
async def get_course_details(term_code: str, crn: str):
    """Get detailed information for a specific course including registration status."""
    try:
        with oscar_client:
            details = oscar_client.get_course_details(term_code, crn)
        
        return {
            "crn": details.crn,
            "title": details.title,
            "subject": details.subject,
            "course_number": details.course_number,
            "section": details.section,
            "credits": details.credits,
            "schedule_type": details.schedule_type,
            "campus": details.campus,
            "term": details.term,
            "registration": {
                "seats_capacity": details.registration.seats_capacity,
                "seats_actual": details.registration.seats_actual,
                "seats_remaining": details.registration.seats_remaining,
                "waitlist_capacity": details.registration.waitlist_capacity,
                "waitlist_actual": details.registration.waitlist_actual,
                "waitlist_remaining": details.registration.waitlist_remaining
            } if details.registration else None,
            "prerequisites": details.prerequisites,
            "restrictions": details.restrictions,
            "meeting_times": details.meeting_times,
            "instructors": details.instructors
        }
    except Exception as e:
        logger.error(f"Error getting course details: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@app.get("/api/research",
         tags=["Research"],
         summary="Search research papers",
         description="Search Georgia Tech research papers and publications by keywords",
         response_description="List of research papers matching the search criteria")
async def search_research_papers(
    keywords: str,  # Comma-separated keywords
    max_records: int = 10
):
    """Search Georgia Tech research papers and publications by keywords."""
    try:
        keyword_list = [k.strip() for k in keywords.split(",")]
        
        with smartech_client:
            results = smartech_client.search_records(
                keywords=keyword_list,
                max_records=max_records
            )
        
        papers = results.get('papers', [])
        
        return {
            "keywords": keyword_list,
            "count": len(papers),
            "max_records": max_records,
            "papers": [
                {
                    "title": paper.title,
                    "authors": paper.authors,
                    "abstract": paper.abstract[:200] + "..." if len(paper.abstract) > 200 else paper.abstract,
                    "publication_date": paper.publication_date.isoformat(),
                    "subject_areas": paper.subject_areas,
                    "citation_count": paper.citation_count,
                    "related_courses": paper.related_courses
                }
                for paper in papers
            ]
        }
    except Exception as e:
        logger.error(f"Error searching research papers: {e}")
        raise HTTPException(status_code=500, detail=str(e))


def main():
    """Main function to run the FastAPI server."""
    global config
    
    # Parse command line arguments
    parser = argparse.ArgumentParser(description="Georgia Tech FastAPI MCP Server")
    parser.add_argument("--config", help="Path to configuration file")
    parser.add_argument("--host", default="0.0.0.0", help="Server host")
    parser.add_argument("--port", type=int, default=8080, help="Server port")
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
    
    logger.info(f"Starting Georgia Tech FastAPI MCP Server on {args.host}:{args.port}")
    
    # Run the server
    uvicorn.run(
        app,
        host=args.host,
        port=args.port,
        log_level=args.log_level.lower()
    )


if __name__ == "__main__":
    main()