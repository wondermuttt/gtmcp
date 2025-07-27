#!/usr/bin/env python3
"""
Georgia Tech MCP Server using FastMCP framework
Implements search and fetch tools for ChatGPT integration
"""

import os
import logging
import re
from typing import List, Dict, Any, Optional
from datetime import datetime, timedelta

from fastmcp import FastMCP
from pydantic import Field
import uvicorn

# Import our existing clients
from .clients.oscar_client import OscarClient
from .clients.smartech_client import SMARTechClient

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Initialize FastMCP server
mcp = FastMCP("Georgia Tech MCP Server")

# Client configuration
CLIENT_CONFIG = {
    "timeout": 30,
    "max_retries": 3
}

# Cache for search results (used by fetch)
SEARCH_CACHE = {}
CACHE_EXPIRY = timedelta(hours=8)
CACHE_TIMESTAMPS = {}

# Semester term exclusion list to prevent "Fall" from being interpreted as subject
SEMESTER_TERMS = {'FALL', 'SPRING', 'SUMMER', 'WINTER'}


def is_cache_expired(key: str) -> bool:
    """Check if a cache entry has expired"""
    if key not in CACHE_TIMESTAMPS:
        return True
    return datetime.now() - CACHE_TIMESTAMPS[key] > CACHE_EXPIRY


def get_term_name(term_code: str) -> str:
    """Convert term code to human-readable name"""
    try:
        year = term_code[:4]
        suffix = term_code[4:6]
        season_map = {"02": "Spring", "05": "Summer", "08": "Fall"}
        season = season_map.get(suffix, "Unknown")
        return f"{season} {year}"
    except:
        return term_code


@mcp.tool()
def search(query: str = Field(description="Search query - can be course codes (CS 6515), topics (machine learning), semesters (Fall 2025 CS), or research papers")) -> List[Dict[str, Any]]:
    """
    Search Georgia Tech courses and research papers.
    
    COURSE SEARCHES:
    - By code: "CS 6515" (Graduate Algorithms), "CS 7641" (Machine Learning)
    - By number: "6515", "1301", "7641"
    - By topic: "machine learning", "algorithms", "software engineering"
    - By semester: "Fall 2025", "Spring 2025 CS", "Fall 2025 OMSCS"
    - OMSCS: "OMSCS algorithms", "online CS 6300"
    
    RESEARCH SEARCHES:
    - Add "research" or "papers": "neural networks research", "robotics papers"
    
    TIPS:
    - Course codes work best (e.g., CS 6515)
    - Semesters: Spring (02), Summer (05), Fall (08)
    - Returns up to 10 results with id, title, text, url
    - Use fetch with returned id for full details
    """
    query = query.strip()
    if not query:
        return [{
            "id": "help_empty_query",
            "title": "Empty search query - Examples provided",
            "text": "Please provide a search query. Examples:\n" +
                    "• Course by code: 'CS 6515' or 'MATH 1551'\n" +
                    "• Course by topic: 'machine learning' or 'algorithms'\n" +
                    "• By semester: 'Fall 2025 CS' or 'Spring 2025 OMSCS'\n" +
                    "• Research: 'neural networks research' or 'robotics papers'\n" +
                    "• OMSCS: 'OMSCS CS 6300' or 'online algorithms'",
            "url": "https://oscar.gatech.edu"
        }]
    
    results = []
    query_upper = query.upper()
    
    # Determine search type
    is_research_search = any(term in query.lower() for term in ['research', 'paper', 'publication', 'thesis', 'dissertation'])
    is_course_search = not is_research_search  # Default to course search
    
    # Search courses
    if is_course_search:
        try:
            oscar_client = OscarClient(**CLIENT_CONFIG)
            with oscar_client:
                # Get available semesters
                semesters = oscar_client.get_available_semesters()
                
                # Filter out malformed semester codes
                valid_semesters = []
                for sem in semesters:
                    if re.match(r'^\d{4}(02|05|08)$', sem.code):
                        valid_semesters.append(sem)
                    else:
                        logger.warning(f"Skipping malformed semester code: {sem.code} - {sem.name}")
                
                # Check if query mentions a specific semester
                semester_match = re.search(r'(fall|spring|summer)\s+(\d{4})', query.lower())
                requested_semester = None
                if semester_match:
                    season, year = semester_match.groups()
                    suffix_map = {'spring': '02', 'summer': '05', 'fall': '08'}
                    requested_semester = f"{year}{suffix_map[season]}"
                    logger.info(f"Detected semester request: {season.capitalize()} {year} -> {requested_semester}")
                
                # Extract subject code if present (e.g., "CS 6515" -> "CS")
                subject_match = re.match(r'^([A-Z]{2,4})\s+\d+', query_upper)
                
                # Check if the match is actually a semester term
                if subject_match and subject_match.group(1) in SEMESTER_TERMS:
                    subject_match = None
                
                # Determine which semesters to search
                if requested_semester:
                    # Search only the requested semester
                    semesters_to_search = [s for s in valid_semesters if s.code == requested_semester]
                    if not semesters_to_search:
                        logger.warning(f"Requested semester {requested_semester} not found in available semesters")
                        # Fall back to recent semesters
                        semesters_to_search = valid_semesters[:3]
                else:
                    # Search recent semesters (limit to 3 for performance)
                    semesters_to_search = valid_semesters[:3]
                
                for semester in semesters_to_search:
                    term_code = semester.code
                    term_info = semester
                    
                    # Skip view-only semesters unless specifically requested
                    if semester.view_only and not requested_semester:
                        continue
                    
                    # Get subjects for this term
                    subjects_to_search = []
                    
                    if subject_match:
                        # If we have a subject code, use it
                        subjects_to_search = [subject_match.group(1)]
                    else:
                        # Otherwise, check common CS-related subjects
                        all_subjects = oscar_client.get_subjects(term_code)
                        cs_subjects = ['CS', 'CSE', 'ECE', 'MATH', 'ISYE', 'MGT', 'PUBP']
                        subjects_to_search = [s.code for s in all_subjects if s.code in cs_subjects]
                    
                    # Search each relevant subject
                    for subject in subjects_to_search:
                        try:
                            courses = oscar_client.get_courses_by_subject(term_code, subject)
                            
                            # Filter courses based on query
                            filtered_courses = []
                            for course in courses:
                                course_str = f"{course.subject} {course.course_number} {course.title}".lower()
                                
                                # Check if course matches query
                                if any(term in course_str for term in query.lower().split()):
                                    filtered_courses.append(course)
                            
                            # Add filtered courses to results
                            for course in filtered_courses[:5]:  # Limit per subject/term
                                result_id = f"course_{term_code}_{course.crn}"
                                
                                # Build description
                                desc_parts = []
                                if hasattr(course, 'section'):
                                    desc_parts.append(f"Section {course.section}")
                                desc_parts.append(f"CRN: {course.crn}")
                                if term_info:
                                    desc_parts.append(f"Term: {term_info.name}")
                                
                                description = " | ".join(desc_parts) if desc_parts else "No additional details"
                                
                                result = {
                                    "id": result_id,
                                    "title": f"{course.subject} {course.course_number}: {course.title}",
                                    "text": f"{course.title} | {description}",
                                    "url": f"https://oscar.gatech.edu/course/{term_code}/{course.crn}"
                                }
                                
                                # Cache the course data for fetch
                                SEARCH_CACHE[result_id] = {
                                    "course": course,
                                    "term_code": term_code,
                                    "type": "course"
                                }
                                CACHE_TIMESTAMPS[result_id] = datetime.now()
                                
                                results.append(result)
                                
                        except Exception as e:
                            logger.error(f"Error searching {subject} in {term_code}: {e}")
                    
                    # Stop if we have enough results
                    if len(results) >= 10:
                        break
                        
        except Exception as e:
            logger.error(f"Error searching courses: {e}")
            return [{
                "id": "error_course_search",
                "title": "Error searching courses - Connection issue",
                "text": f"Unable to search courses due to: {str(e)}\n\n" +
                        "This usually means the OSCAR system is temporarily unavailable.\n\n" +
                        "Try these examples when the system is back:\n" +
                        "• 'CS 6515' - Graduate Algorithms\n" +
                        "• 'Fall 2025 CS' - CS courses in Fall 2025\n" +
                        "• 'OMSCS algorithms' - Online MS algorithm courses\n" +
                        "• 'machine learning' - ML-related courses",
                "url": "https://oscar.gatech.edu"
            }]
    
    # Search research papers
    if is_research_search:
        try:
            smartech_client = SMARTechClient(**CLIENT_CONFIG)
            with smartech_client:
                # Split query into keywords
                keywords = query.split()
                research_results = smartech_client.search_records(
                    keywords=keywords,
                    max_records=10
                )
                
                papers = research_results.get('papers', [])
                for paper in papers:
                    # Use oai_identifier as the unique ID
                    result_id = f"research_{paper.oai_identifier.replace('/', '_').replace(':', '_')}"
                    
                    # Extract metadata
                    authors = ", ".join(paper.authors[:3]) if paper.authors else "Unknown"
                    if len(paper.authors) > 3:
                        authors += f" et al."
                    date = paper.publication_date.strftime('%Y-%m-%d') if paper.publication_date else 'Unknown date'
                    
                    result = {
                        "id": result_id,
                        "title": paper.title,
                        "text": f"{paper.abstract[:200] if paper.abstract else 'No abstract available'}... | Authors: {authors} | Date: {date}",
                        "url": f"https://smartech.gatech.edu/handle/{paper.oai_identifier.split(':')[-1]}"
                    }
                    
                    # Cache full paper data for fetch
                    SEARCH_CACHE[result_id] = {
                        "paper": paper,
                        "type": "research"
                    }
                    CACHE_TIMESTAMPS[result_id] = datetime.now()
                    
                    results.append(result)
                
        except Exception as e:
            logger.error(f"Error searching research: {e}")
            if results:  # If we have some results, return them
                return results[:10]
            return [{
                "id": "error_research_search",
                "title": "Error searching research papers - Connection issue",
                "text": f"Unable to search research papers due to: {str(e)}\n\n" +
                        "This usually means the SMARTech system is temporarily unavailable.\n\n" +
                        "Try these examples when the system is back:\n" +
                        "• 'machine learning research'\n" +
                        "• 'neural networks papers'\n" +
                        "• 'robotics research papers'\n" +
                        "• 'computer vision papers'",
                "url": "https://smartech.gatech.edu"
            }]
    
    # Check if we have any results
    if not results:
        # Provide helpful examples based on what was searched
        help_text = f"No results found for '{query}'.\n\n"
        
        if is_course_search:
            help_text += "Try these course search examples:\n"
            help_text += "• Specific course: 'CS 6515' or 'CS 1301'\n"
            help_text += "• By number only: '6515' or '7641'\n"
            help_text += "• By topic: 'algorithms' or 'machine learning'\n"
            help_text += "• With semester: 'Fall 2025 CS' or 'Spring 2025 algorithms'\n"
            help_text += "• OMSCS courses: 'OMSCS CS 6300' or 'online CS 6515'\n\n"
            help_text += "Note: Fall=08, Spring=02, Summer=05 in semester codes"
        else:
            help_text += "Try these research search examples:\n"
            help_text += "• 'machine learning research'\n"
            help_text += "• 'neural networks papers'\n"
            help_text += "• 'robotics research papers'\n"
            help_text += "• 'computer vision papers'"
        
        return [{
            "id": "no_results_found",
            "title": "No results found - See examples below",
            "text": help_text,
            "url": "https://oscar.gatech.edu" if is_course_search else "https://smartech.gatech.edu"
        }]
    
    return results[:10]  # Limit to 10 results total


@mcp.tool()
def fetch(id: str = Field(description="Unique identifier from search results (e.g., 'course_202508_86143')")) -> Optional[Dict[str, Any]]:
    """
    Fetch full content for a document by ID.
    
    Use the exact ID returned from search results to get:
    
    FOR COURSES:
    - Full course details (credits, schedule type, campus)
    - Section information (CRN, instructor)
    - Registration status (seats available, waitlist)
    - Prerequisites and restrictions
    
    FOR RESEARCH:
    - Complete abstract
    - All authors
    - Publication date and subject areas
    - Related courses
    
    Returns: Single object with id, title, text (full content), url, metadata
    
    Note: ID format is 'course_TERMCODE_CRN' or 'research_IDENTIFIER'
    """
    # Check if this is a cached search result
    if id in SEARCH_CACHE and not is_cache_expired(id):
        cached = SEARCH_CACHE[id]
        
        if cached['type'] == 'course':
            course = cached['course']
            term_code = cached['term_code']
            
            # Get full course details
            try:
                oscar_client = OscarClient(**CLIENT_CONFIG)
                with oscar_client:
                    # Get detailed course information
                    details = oscar_client.get_course_details(term_code, course.crn)
                    
                    # Format full course details
                    text = f"""Course: {details.subject} {details.course_number} - {details.title}

Section: {details.section}
CRN: {details.crn}
Term: {details.term}
Credits: {details.credits}
Schedule Type: {details.schedule_type}
Campus: {details.campus}
Levels: {', '.join(details.levels)}

Registration:
- Seats: {details.registration.seats_actual}/{details.registration.seats_capacity} (Remaining: {details.registration.seats_remaining})
- Waitlist: {details.registration.waitlist_actual}/{details.registration.waitlist_capacity} (Remaining: {details.registration.waitlist_remaining})
"""
                    
                    if details.restrictions:
                        text += f"\nRestrictions:\n- " + "\n- ".join(details.restrictions)
                    
                    return {
                        "id": id,
                        "title": f"{details.subject} {details.course_number}: {details.title}",
                        "text": text,
                        "url": f"https://oscar.gatech.edu/course/{term_code}/{details.crn}",
                        "metadata": {
                            "course_number": f"{details.subject} {details.course_number}",
                            "section": details.section,
                            "term": details.term,
                            "campus": details.campus
                        }
                    }
            except Exception as e:
                logger.error(f"Error fetching course details: {e}")
                # Return cached basic info as fallback with error note
                return {
                    "id": id,
                    "title": f"{course.subject} {course.course_number}: {course.title}",
                    "text": f"Course: {course.subject} {course.course_number} - {course.title}\n" +
                            f"Section: {course.section}\n" +
                            f"CRN: {course.crn}\n" +
                            f"Term: {get_term_name(term_code)}\n\n" +
                            f"Note: Detailed information temporarily unavailable due to: {str(e)}\n\n" +
                            "Full details usually include:\n" +
                            "• Credits and schedule type\n" +
                            "• Campus and instructor info\n" +
                            "• Registration status (seats/waitlist)\n" +
                            "• Prerequisites and restrictions\n\n" +
                            "Try again later for complete information.",
                    "url": f"https://oscar.gatech.edu/course/{term_code}/{course.crn}",
                    "metadata": {
                        "partial_data": True,
                        "error": str(e)
                    }
                }
                
        elif cached['type'] == 'research':
            paper = cached['paper']
            
            # Return full paper details
            authors = ", ".join(paper.authors) if paper.authors else "Unknown"
            date = paper.publication_date.strftime('%Y-%m-%d') if paper.publication_date else 'Unknown date'
            subjects = ", ".join(paper.subject_areas) if paper.subject_areas else "Not specified"
            
            return {
                "id": id,
                "title": paper.title,
                "text": f"""Title: {paper.title}

Authors: {authors}

Publication Date: {date}

Subject Areas: {subjects}

Abstract:
{paper.abstract if paper.abstract else 'No abstract available'}

Related Courses: {', '.join(paper.related_courses) if paper.related_courses else 'None specified'}
""",
                "url": f"https://smartech.gatech.edu/handle/{paper.oai_identifier.split(':')[-1]}",
                "metadata": {
                    "type": "research",
                    "authors": paper.authors,
                    "date": date,
                    "subjects": paper.subject_areas
                }
            }
    
    # If we reach here, the ID was not found or expired
    return {
        "id": id,
        "title": "Document not found or expired",
        "text": f"The document with ID '{id}' was not found or has expired from cache.\n\n" +
                "This can happen if:\n" +
                "• The search was performed more than 8 hours ago\n" +
                "• The ID was modified or typed incorrectly\n" +
                "• The server was restarted since the search\n\n" +
                "To get fresh results:\n" +
                "1. Run a new search (e.g., 'CS 6515' or 'Fall 2025 CS')\n" +
                "2. Use the exact ID from the search results\n" +
                "3. Fetch immediately after searching for best results\n\n" +
                "Example IDs look like:\n" +
                "• course_202508_86143 (for courses)\n" +
                "• research_oai_smartech_1853_54434 (for papers)",
        "url": "https://oscar.gatech.edu",
        "metadata": {
            "error": "not_found",
            "suggestion": "Run a fresh search and use the returned IDs"
        }
    }


if __name__ == "__main__":
    # Get host and port from environment
    host = os.environ.get('MCP_HOST', '0.0.0.0')
    port = int(os.environ.get('MCP_PORT', '8080'))
    
    # Check if SSL certificates exist
    cert_path = os.environ.get('SSL_CERT', '/etc/letsencrypt/live/wmjump1.henkelman.net/fullchain.pem')
    key_path = os.environ.get('SSL_KEY', '/etc/letsencrypt/live/wmjump1.henkelman.net/privkey.pem')
    
    # For FastMCP with SSE transport, we need to use the ASGI app
    # Get the ASGI app from FastMCP
    app = mcp.http_app
    
    # Run with uvicorn directly for SSL support
    if os.path.exists(cert_path) and os.path.exists(key_path):
        logger.info(f"Starting FastMCP server with SSL on https://{host}:{port}")
        uvicorn.run(
            app,
            host=host,
            port=port,
            ssl_certfile=cert_path,
            ssl_keyfile=key_path,
            log_level="info"
        )
    else:
        logger.info(f"Starting FastMCP server without SSL on http://{host}:{port}")
        uvicorn.run(
            app,
            host=host,
            port=port,
            log_level="info"
        )