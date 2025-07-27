#!/usr/bin/env python3
"""
Georgia Tech MCP Server
Implements Model Context Protocol for ChatGPT integration
"""

import asyncio
import json
import logging
import os
import re
from datetime import datetime, timedelta
from typing import Dict, List, Any, Optional
from urllib.parse import quote

from fastapi import FastAPI, Request, Response
from fastapi.responses import StreamingResponse
from fastapi.middleware.cors import CORSMiddleware
import uvicorn

from gtmcp.clients.oscar_client import OscarClient
from gtmcp.clients.smartech_client import SMARTechClient

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Initialize FastAPI app
app = FastAPI(
    title="Georgia Tech MCP Server",
    description="MCP server for Georgia Tech course and research data",
    version="3.0.0"
)

# Configure CORS for ChatGPT
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # Allow all origins for ChatGPT
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
    expose_headers=["*"]
)

# Client configuration
CLIENT_CONFIG = {
    "timeout": 30,
    "max_retries": 3
}

# Enhanced caching system
from datetime import timedelta

# Store for search results to enable fetch (legacy by ID)
SEARCH_CACHE: Dict[str, Dict[str, Any]] = {}

# New intelligent cache for courses by course number
# Key format: "CS 6515" -> List of course instances across terms
COURSE_CACHE: Dict[str, List[Dict[str, Any]]] = {}
CACHE_EXPIRY_HOURS = 8
CACHE_TIMESTAMPS: Dict[str, datetime] = {}


def is_cache_expired(cache_key: str) -> bool:
    """Check if a cache entry is expired"""
    if cache_key not in CACHE_TIMESTAMPS:
        return True
    
    timestamp = CACHE_TIMESTAMPS[cache_key]
    expiry = timestamp + timedelta(hours=CACHE_EXPIRY_HOURS)
    return datetime.now() > expiry


def add_to_course_cache(course: Any, term_code: str) -> None:
    """Add a course to the intelligent cache"""
    course_key = f"{course.subject} {course.course_number}"
    
    # Create course data entry
    course_data = {
        "course": course,
        "term_code": term_code,
        "crn": course.crn,
        "title": course.title,
        "cached_at": datetime.now()
    }
    
    # Initialize or append to course cache
    if course_key not in COURSE_CACHE:
        COURSE_CACHE[course_key] = []
    
    # Check if this specific section is already cached
    existing = [c for c in COURSE_CACHE[course_key] 
                if c['crn'] == course.crn and c['term_code'] == term_code]
    
    if not existing:
        COURSE_CACHE[course_key].append(course_data)
    
    # Update timestamp
    CACHE_TIMESTAMPS[course_key] = datetime.now()


def get_from_course_cache(course_number: str, term_code: Optional[str] = None) -> Optional[Dict[str, Any]]:
    """Get course from cache by course number (e.g., 'CS 6515')"""
    # Normalize course number (handle both "CS6515" and "CS 6515")
    match = re.match(r'^([A-Z]+)\s*(\d+)', course_number.upper())
    if not match:
        return None
    
    normalized_key = f"{match.group(1)} {match.group(2)}"
    
    # Check if cached and not expired
    if normalized_key not in COURSE_CACHE or is_cache_expired(normalized_key):
        return None
    
    courses = COURSE_CACHE[normalized_key]
    if not courses:
        return None
    
    # If term specified, find that specific term
    if term_code:
        for course_data in courses:
            if course_data['term_code'] == term_code:
                return course_data
    
    # Otherwise return the most recent term
    # Sort by term code (higher = more recent)
    sorted_courses = sorted(courses, key=lambda c: c['term_code'], reverse=True)
    return sorted_courses[0]


def create_mcp_response(id: str, result: Any) -> dict:
    """Create MCP response in the format expected by the protocol"""
    return {
        "jsonrpc": "2.0",
        "id": id,
        "result": result
    }


def create_mcp_error(id: str, code: int, message: str) -> dict:
    """Create MCP error response"""
    return {
        "jsonrpc": "2.0",
        "id": id,
        "error": {
            "code": code,
            "message": message
        }
    }


def handle_search(query: str) -> List[Dict[str, Any]]:
    """
    Handle search requests for both courses and research papers
    Returns results in ChatGPT-compatible format
    """
    results = []
    
    # Parse query to determine type
    is_course_search = any(keyword in query.lower() for keyword in [
        'course', 'class', 'credit', 'crn', 'cs', 'math', 'phys', 
        'schedule', 'semester', 'fall', 'spring', 'summer'
    ])
    
    is_research_search = any(keyword in query.lower() for keyword in [
        'research', 'paper', 'publication', 'study', 'thesis', 
        'dissertation', 'journal', 'conference'
    ])
    
    # If no specific type detected, search both
    if not is_course_search and not is_research_search:
        is_course_search = True
        is_research_search = True
    
    # Search courses
    if is_course_search:
        try:
            oscar_client = OscarClient(**CLIENT_CONFIG)
            with oscar_client:
                # Get available terms and search in recent ones
                semesters = oscar_client.get_available_semesters()
                if not semesters:
                    logger.warning("No semesters available")
                    return results
                
                # Filter out malformed semester codes (must be YYYYMM format)
                valid_semesters = []
                for sem in semesters:
                    if re.match(r'^\d{4}(02|05|08)$', sem.code):
                        valid_semesters.append(sem)
                    else:
                        logger.warning(f"Skipping malformed semester code: {sem.code} - {sem.name}")
                
                # Sort semesters by code (newer first) to ensure consistent ordering
                sorted_semesters = sorted(valid_semesters, key=lambda s: s.code, reverse=True)
                
                # Get current date to determine relative semesters
                from datetime import datetime
                current_date = datetime.now()
                current_year = current_date.year
                current_month = current_date.month
                
                # Determine current semester based on month
                # Spring: Jan-May (02), Summer: Jun-Jul (05), Fall: Aug-Dec (08)
                if current_month <= 5:
                    current_semester_suffix = '02'  # Spring
                elif current_month <= 7:
                    current_semester_suffix = '05'  # Summer
                else:
                    current_semester_suffix = '08'  # Fall
                
                current_semester_code = f"{current_year}{current_semester_suffix}"
                
                # Check if query mentions a specific semester
                semester_match = re.search(r'(fall|spring|summer)\s+(\d{4})', query.lower())
                if semester_match:
                    season, year = semester_match.groups()
                    suffix_map = {'spring': '02', 'summer': '05', 'fall': '08'}
                    requested_semester = f"{year}{suffix_map[season]}"
                    
                    # Add requested semester if it exists
                    requested_sem = next((s for s in sorted_semesters if s.code == requested_semester), None)
                    if requested_sem:
                        terms_to_search = [requested_sem]
                        logger.info(f"User requested specific semester: {requested_semester}")
                    else:
                        terms_to_search = []
                        logger.warning(f"Requested semester {requested_semester} not available")
                else:
                    # Find semesters relative to current time
                    terms_to_search = []
                    past_terms_found = 0
                    future_terms_found = 0
                    
                    for sem in sorted_semesters:
                        # Include past semesters (up to 6)
                        if sem.code < current_semester_code and past_terms_found < 6:
                            terms_to_search.append(sem)
                            past_terms_found += 1
                        # Include current and future semesters (up to 4)
                        elif sem.code >= current_semester_code and future_terms_found < 4:
                            terms_to_search.append(sem)
                            future_terms_found += 1
                        
                        # Stop if we have enough terms
                        if len(terms_to_search) >= 10:
                            break
                
                # Sort by code descending (most recent first)
                terms_to_search.sort(key=lambda s: s.code, reverse=True)
                
                logger.info(f"Searching in {len(terms_to_search)} terms for query: {query}")
                
                # Parse query to extract subject if present
                # Common semester terms to exclude from subject matching
                SEMESTER_TERMS = {'FALL', 'SPRING', 'SUMMER', 'WINTER'}
                
                # Only match valid subject codes (2-4 uppercase letters, optionally followed by numbers)
                # Common subjects: CS, ECE, MATH, PHYS, CHEM, BIOL, ME, AE, etc.
                subject_match = re.match(r'^([A-Z]{2,4})\s+(\d{4})\b', query.upper())
                if not subject_match:
                    # Try without space (e.g., "CS1301")
                    subject_match = re.match(r'^([A-Z]{2,4})(\d{4})\b', query.upper())
                
                # Don't treat semester terms as subject codes
                if subject_match and subject_match.group(1) in SEMESTER_TERMS:
                    subject_match = None
                
                all_course_results = []
                
                for term in terms_to_search:
                    current_term = term.code
                    
                    if subject_match:
                        # Subject code found (e.g., "CS" from "CS 1301")
                        subject = subject_match.group(1)
                        course_num = subject_match.group(2)
                        
                        # Get all courses for the subject first
                        logger.info(f"Getting courses for subject {subject} in term {current_term}")
                        try:
                            all_subject_courses = oscar_client.get_courses_by_subject(current_term, subject)
                            
                            if all_subject_courses:
                                logger.info(f"Found {len(all_subject_courses)} total courses for {subject}")
                                
                                # Filter by course number if provided
                                if course_num:
                                    filtered_courses = [c for c in all_subject_courses 
                                                      if c.course_number == course_num]
                                else:
                                    # If no course number, try to match by title/keywords
                                    query_lower = query.lower()
                                    # Split query into words for better matching
                                    query_words = query_lower.split()
                                    
                                    # Try exact phrase match first
                                    filtered_courses = [c for c in all_subject_courses 
                                                      if query_lower in c.title.lower()]
                                    
                                    # If no exact matches, try matching any word
                                    if not filtered_courses and query_words:
                                        filtered_courses = [c for c in all_subject_courses 
                                                          if any(word in c.title.lower() 
                                                                 for word in query_words 
                                                                 if len(word) > 2)]  # Skip short words
                                
                                # Always return some courses if we found any for this subject
                                if not filtered_courses and all_subject_courses:
                                    # If no matches at all, return first few courses
                                    filtered_courses = all_subject_courses[:5]
                                
                                all_course_results.extend([(course, current_term) for course in filtered_courses])
                                if len(all_course_results) >= 10:
                                    break
                            else:
                                logger.info(f"No courses found for subject {subject} in term {current_term}")
                        except Exception as e:
                            logger.error(f"Error getting courses for {subject}: {e}")
                    else:
                        # No subject code, search by title across all subjects
                        # Get all subjects first
                        subjects = oscar_client.get_subjects(current_term)
                        
                        # Search in the most common subjects
                        common_subjects = ['CS', 'MATH', 'PHYS', 'CHEM', 'BIOL', 'ECE', 'ME']
                        query_lower = query.lower()
                        query_words = query_lower.split()
                        
                        for subj_info in subjects:
                            if subj_info.code in common_subjects:
                                try:
                                    # Get all courses for the subject
                                    all_courses = oscar_client.get_courses_by_subject(current_term, subj_info.code)
                                    
                                    if all_courses:
                                        # Apply same filtering logic as above
                                        filtered = [c for c in all_courses 
                                                  if query_lower in c.title.lower()]
                                        
                                        # If no exact matches, try word matching
                                        if not filtered and query_words:
                                            filtered = [c for c in all_courses 
                                                      if any(word in c.title.lower() 
                                                             for word in query_words 
                                                             if len(word) > 2)]
                                        
                                        # If still no matches, take first few
                                        if not filtered:
                                            filtered = all_courses[:2]
                                        
                                        all_course_results.extend([(c, current_term) for c in filtered[:2]])
                                        if len(all_course_results) >= 10:
                                            break
                                except Exception as e:
                                    logger.error(f"Error searching in {subj_info.code}: {e}")
                                    continue
                        
                        if len(all_course_results) >= 10:
                            break
                    
                # If no courses found, add an explanatory note with examples
                if not all_course_results and is_course_search:
                    # Provide helpful guidance based on the query
                    suggestions = []
                    if any(word in query.lower() for word in ['fall', 'spring', 'summer']):
                        suggestions.append("Note: Course data for future semesters may not be available yet.")
                        suggestions.append("Try searching for specific course codes instead (e.g., 'CS 6515').")
                    elif len(query.split()) > 2:
                        suggestions.append("Try a simpler query with fewer words.")
                        suggestions.append("Course codes work best (e.g., 'CS 1301', 'MATH 1551').")
                    else:
                        suggestions.append("Try searching with course codes (e.g., 'CS 1301', 'CS 6515').")
                        suggestions.append("Or search by topic (e.g., 'algorithms', 'databases', 'AI').")
                    
                    # Create a special result explaining the empty results
                    result = {
                        "id": "note_empty_results",
                        "title": "No courses found - Try a different search",
                        "text": f"No courses found for '{query}'. {' '.join(suggestions)} Popular courses: CS 1301 (Intro to Computing), CS 6515 (Graduate Algorithms), CS 7641 (Machine Learning).",
                        "url": ""
                    }
                    results.append(result)
                
                # Process all found courses
                for course, term_code in all_course_results[:10]:  # Limit to 10 results
                    result_id = f"course_{term_code}_{course.crn}"
                    
                    # Build description
                    desc_parts = []
                    if hasattr(course, 'prerequisites') and course.prerequisites:
                        desc_parts.append(f"Prerequisites: {course.prerequisites}")
                    if hasattr(course, 'meeting_times') and course.meeting_times:
                        times = [f"{mt.days} {mt.time}" for mt in course.meeting_times[:2]]
                        desc_parts.append(f"Schedule: {', '.join(times)}")
                    
                    # Add term info
                    term_info = next((t for t in semesters if t.code == term_code), None)
                    if term_info:
                        desc_parts.append(f"Term: {term_info.name}")
                    
                    description = " | ".join(desc_parts) if desc_parts else "No additional details"
                    
                    result = {
                        "id": result_id,
                        "title": f"{course.subject} {course.course_number}: {course.title}",
                        "text": f"{course.title} | {description}",
                        "url": f"https://oscar.gatech.edu/course/{term_code}/{course.crn}"
                    }
                    
                    # Cache full course data for fetch (legacy)
                    SEARCH_CACHE[result_id] = {
                        "course": course,
                        "term_code": term_code,
                        "type": "course"
                    }
                    
                    # Also add to intelligent course cache
                    add_to_course_cache(course, term_code)
                    
                    results.append(result)
                    
        except Exception as e:
            logger.error(f"Error searching courses: {e}")
    
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
                    
                    results.append(result)
                
        except Exception as e:
            logger.error(f"Error searching research: {e}")
    
    # Add metadata if we have results
    if results or (is_course_search or is_research_search):
        metadata = {
            "query": query,
            "search_type": [],
            "tips": []
        }
        
        if is_course_search:
            metadata["search_type"].append("courses")
        if is_research_search:
            metadata["search_type"].append("research")
            
        # Add contextual tips
        if not results:
            metadata["tips"].append("Try using course codes like 'CS 1301' or 'CS 6515'")
            metadata["tips"].append("Use the 'help' tool for more examples")
        elif len(results) < 5:
            metadata["tips"].append("Try broader search terms for more results")
        else:
            metadata["tips"].append("Use 'fetch' with result IDs for full details")
            
        # Return results with metadata
        return {
            "results": results,
            "metadata": metadata,
            "result_count": len(results)
        }
    
    return results


def handle_help(topic: Optional[str] = None) -> Dict[str, Any]:
    """
    Handle help requests
    Returns guidance on how to use the MCP server
    """
    if not topic:
        # General help
        return {
            "title": "Georgia Tech MCP Server Help",
            "sections": {
                "overview": "Search and fetch Georgia Tech courses across multiple semesters. Also searches research papers.",
                "quick_start": [
                    "Search: Use natural language queries",
                    "Fetch: Requires course number AND semester",
                    "Available semesters: Fall 2024, Spring 2025, Fall 2025, etc."
                ],
                "search_examples": {
                    "by_course_code": [
                        "'CS 6515' - Find all sections of Graduate Algorithms",
                        "'CS 1301' - Intro to Computing sections",
                        "'MATH 1551' - Differential Calculus"
                    ],
                    "by_semester": [
                        "'Fall 2025 CS courses' - All CS courses in Fall 2025",
                        "'Spring 2025 algorithms' - Algorithm courses in Spring",
                        "'Fall 2024 machine learning' - ML courses this fall"
                    ],
                    "by_program": [
                        "'OMSCS algorithms' - Online MS algorithm courses",
                        "'online CS 6300' - Online sections of Software Dev",
                        "'OMSCS Fall 2025' - All online MS courses for Fall"
                    ],
                    "by_availability": [
                        "'CS 7641 waitlist' - Check ML course waitlist",
                        "'CS 6515 seats available' - Check open seats",
                        "'waitlist Fall 2025' - Courses with waitlists"
                    ],
                    "research": [
                        "'machine learning research' - ML research papers",
                        "'robotics papers' - Robotics publications",
                        "'neural networks research 2024' - Recent NN papers"
                    ]
                },
                "fetch_examples": [
                    "{\"course_number\": \"CS 6515\", \"semester\": \"Fall 2025\"}",
                    "{\"course_number\": \"CS 7641\", \"semester\": \"Spring 2025\"}",
                    "{\"course_number\": \"CS 6300\", \"semester\": \"Fall 2024\", \"filters\": {\"campus\": \"online\"}}"
                ],
                "tips": [
                    "Semesters: Fall=08, Spring=02, Summer=05 (e.g., Fall 2025 = 202508)",
                    "Online sections typically start with 'O' (O01, O02, etc.)",
                    "Search returns max 10 results - be specific for better matches",
                    "Some future semesters may not have course data yet"
                ],
                "popular_omscs_courses": {
                    "CS 6515": "Graduate Algorithms - Core requirement",
                    "CS 7641": "Machine Learning - Very popular, fills quickly",
                    "CS 6300": "Software Development Process - Good starter course",
                    "CS 6601": "Artificial Intelligence - Classic AI course",
                    "CS 6200": "Graduate Operating Systems - Systems track",
                    "CS 7646": "Machine Learning for Trading - Unique offering"
                }
            }
        }
    
    # Topic-specific help
    topics = {
        "search": {
            "title": "Search Tool - Detailed Guide",
            "description": "Search finds courses across all available semesters and research papers.",
            "query_formats": {
                "course_code": {
                    "format": "[SUBJECT] [NUMBER]",
                    "examples": ["CS 6515", "MATH 1551", "ECE 6100"],
                    "tip": "Most reliable way to find specific courses"
                },
                "semester_search": {
                    "format": "[SEASON] [YEAR] [SUBJECT/TOPIC]",
                    "examples": [
                        "Fall 2025 CS",
                        "Spring 2025 algorithms",
                        "Fall 2024 machine learning"
                    ],
                    "tip": "Searches only in the specified semester"
                },
                "topic_search": {
                    "format": "[TOPIC] [MODIFIERS]",
                    "examples": [
                        "machine learning online",
                        "algorithms OMSCS",
                        "databases graduate"
                    ],
                    "tip": "Good for exploring course options"
                },
                "availability_search": {
                    "format": "[COURSE] waitlist|seats|available",
                    "examples": [
                        "CS 7641 waitlist",
                        "CS 6515 seats available",
                        "OMSCS waitlist Fall 2025"
                    ],
                    "tip": "Check course capacity and waitlists"
                }
            },
            "advanced_tips": [
                "Quotes force exact matches: \"machine learning\"",
                "Combine terms: 'Fall 2025 CS graduate algorithms'",
                "OMSCS courses: Add 'OMSCS' or 'online' to queries",
                "Research papers: Add 'research' or 'papers' to query"
            ]
        },
        "fetch": {
            "title": "Fetch Tool - Complete Guide",
            "description": "Fetch gets detailed information for a specific course in a specific semester.",
            "required_parameters": {
                "course_number": "Course code like 'CS 6515' or 'MATH 1551'",
                "semester": "Semester like 'Fall 2025' or 'Spring 2025'"
            },
            "basic_examples": [
                {
                    "request": "{\"course_number\": \"CS 6515\", \"semester\": \"Fall 2025\"}",
                    "description": "Get all sections of Graduate Algorithms for Fall 2025"
                },
                {
                    "request": "{\"course_number\": \"CS 7641\", \"semester\": \"Spring 2025\"}",
                    "description": "Get all sections of Machine Learning for Spring 2025"
                }
            ],
            "filtered_examples": [
                {
                    "request": "{\"course_number\": \"CS 6300\", \"semester\": \"Fall 2025\", \"filters\": {\"campus\": \"online\"}}",
                    "description": "Get only online/OMSCS sections"
                },
                {
                    "request": "{\"course_number\": \"CS 1301\", \"semester\": \"Fall 2024\", \"filters\": {\"section\": \"A\"}}",
                    "description": "Get only section A"
                },
                {
                    "request": "{\"course_number\": \"CS 6515\", \"semester\": \"Fall 2025\", \"filters\": {\"campus\": \"online\", \"section\": \"O01\"}}",
                    "description": "Get specific online section O01"
                }
            ],
            "filter_reference": {
                "section": {
                    "description": "Filter by section code",
                    "examples": ["A", "B", "C", "O01", "O02", "O3"],
                    "note": "Online sections start with 'O'"
                },
                "campus": {
                    "description": "Filter by delivery mode",
                    "values": ["online", "omscs", "atlanta", "campus"],
                    "note": "'online' and 'omscs' find online sections"
                },
                "instructor": {
                    "description": "Filter by instructor name",
                    "examples": ["Smith", "Johnson"],
                    "note": "Partial matching supported"
                }
            },
            "semester_formats": [
                "'Fall 2025' - Natural language",
                "'Spring 2025' - Natural language",
                "'202508' - Term code (YYYYMM where 08=Fall, 02=Spring, 05=Summer)"
            ],
            "common_errors": [
                "Missing semester - Both parameters are required",
                "Wrong semester format - Use 'Season YYYY' or term code",
                "Course not offered - Some courses aren't offered every semester"
            ]
        },
        "semesters": {
            "title": "Semester Codes",
            "description": "Georgia Tech uses YYYYMM format for semesters",
            "format": {
                "YYYY02": "Spring semester",
                "YYYY05": "Summer semester", 
                "YYYY08": "Fall semester"
            },
            "examples": {
                "202502": "Spring 2025",
                "202408": "Fall 2024",
                "202405": "Summer 2024"
            }
        }
    }
    
    if topic and topic.lower() in topics:
        return topics[topic.lower()]
    else:
        return {
            "title": f"No specific help for '{topic}'",
            "available_topics": list(topics.keys()),
            "suggestion": "Try 'help' without a topic for general help"
        }


def get_term_name(term_code: str) -> str:
    """Convert term code to human-readable name"""
    try:
        year = term_code[:4]
        suffix = term_code[4:6]
        season = {"02": "Spring", "05": "Summer", "08": "Fall"}.get(suffix, "Unknown")
        return f"{season} {year}"
    except:
        return term_code


def format_course_result(course: Any, term_code: str, from_cache: bool = False) -> Dict[str, Any]:
    """Format a course into the standard result structure"""
    section_info = getattr(course, 'section', 'N/A')
    
    # Detect if this is an online section
    is_online = section_info.startswith('O') if section_info != 'N/A' else False
    campus = "Online/OMSCS" if is_online else "Atlanta Campus"
    
    return {
        "id": f"course_{term_code}_{course.crn}",
        "title": f"{course.subject} {course.course_number}: {course.title}",
        "text": f"""Course: {course.subject} {course.course_number} - {course.title}
Section: {section_info} ({campus})
CRN: {course.crn}
Term: {get_term_name(term_code)}
Instructor: {getattr(course, 'instructor', 'TBA')}
Schedule: {course.meeting_times[0].days + ' ' + course.meeting_times[0].time if hasattr(course, 'meeting_times') and course.meeting_times else 'TBA'}
Prerequisites: {getattr(course, 'prerequisites', 'None listed') or 'None listed'}
Seats: {getattr(course, 'seats_available', 'N/A')} available / {getattr(course, 'seats_total', 'N/A')} total
""",
        "url": f"https://oscar.gatech.edu/course/{term_code}/{course.crn}",
        "metadata": {
            "course_number": f"{course.subject} {course.course_number}",
            "term": term_code,
            "term_name": get_term_name(term_code),
            "section": section_info,
            "campus": campus,
            "from_cache": from_cache
        }
    }


def convert_semester_to_term_code(semester: str) -> Optional[str]:
    """
    Convert semester string to term code
    Examples:
    - "Fall 2024" -> "202408"
    - "Spring 2025" -> "202502"
    - "202408" -> "202408" (already a code)
    """
    # Check if already a term code
    if re.match(r'^\d{6}$', semester):
        return semester
    
    # Parse semester string like "Fall 2024"
    match = re.match(r'(Fall|Spring|Summer)\s+(\d{4})', semester, re.IGNORECASE)
    if match:
        season, year = match.groups()
        season = season.lower()
        
        if season == 'spring':
            return f"{year}02"
        elif season == 'summer':
            return f"{year}05"
        elif season == 'fall':
            return f"{year}08"
    
    return None


def handle_fetch(course_number: str, semester: str, filters: Optional[Dict[str, str]] = None) -> Optional[Dict[str, Any]]:
    """
    Fetch full content for a course in a specific semester
    
    Args:
        course_number: Course number like "CS 6515" or "CS6515"
        semester: Semester like "Fall 2024", "Spring 2025", or "202408"
        filters: Optional filters for section, campus, instructor
    """
    # Parse filters if provided
    if not filters:
        filters = {}
    
    # Parse course number to normalize it (e.g., "CS 6515" or "CS6515")
    course_match = re.match(r'^([A-Z]+)\s*(\d+)$', course_number.upper())
    if not course_match:
        return None
    
    normalized_key = f"{course_match.group(1)} {course_match.group(2)}"
    
    # Convert semester to term code if needed
    term_code = convert_semester_to_term_code(semester)
    if not term_code:
        return None
    
    # Get all cached courses for this number
    all_matches = []
    if normalized_key in COURSE_CACHE and not is_cache_expired(normalized_key):
        all_matches = COURSE_CACHE[normalized_key]
    
    # If not in cache, do an auto-search
    if not all_matches:
        logger.info(f"Course {course_number} not in cache, searching...")
        search_results = handle_search(course_number)
        if isinstance(search_results, dict) and 'results' in search_results:
            search_results = search_results['results']
        
        # Now check cache again (search should have populated it)
        if normalized_key in COURSE_CACHE:
            all_matches = COURSE_CACHE[normalized_key]
        
        if not all_matches:
            return None
    
    # Filter by the requested term first
    filtered_matches = [m for m in all_matches if m['term_code'] == term_code]
    
    if not filtered_matches:
        # No courses found for this specific term
        return None
    
    # Filter by section
    if filters.get('section'):
        section_filter = filters['section'].upper()
        filtered_matches = [m for m in filtered_matches if 
                          hasattr(m['course'], 'section') and 
                          section_filter == m['course'].section]
    
    # Filter by campus/mode (look for "O" sections for online)
    if filters.get('campus') or filters.get('mode'):
        campus_filter = (filters.get('campus') or filters.get('mode')).lower()
        if 'online' in campus_filter or 'omscs' in campus_filter:
            # Online sections typically start with 'O'
            filtered_matches = [m for m in filtered_matches if 
                              hasattr(m['course'], 'section') and 
                              m['course'].section.startswith('O')]
        elif 'atlanta' in campus_filter or 'campus' in campus_filter:
            # On-campus sections typically don't start with 'O'
            filtered_matches = [m for m in filtered_matches if 
                              hasattr(m['course'], 'section') and 
                              not m['course'].section.startswith('O')]
    
    # Filter by instructor
    if filters.get('instructor'):
        instructor_filter = filters['instructor'].lower()
        filtered_matches = [m for m in filtered_matches if 
                          hasattr(m['course'], 'instructor') and 
                          instructor_filter in m['course'].instructor.lower()]
    
    # If we have exactly one match, return single result
    if len(filtered_matches) == 1:
        course_data = filtered_matches[0]
        course = course_data['course']
        term_code = course_data['term_code']
        
        return format_course_result(course, term_code, from_cache=True)
    
    # If we have multiple matches, return a special multi-result
    elif len(filtered_matches) > 1:
        return {
            "id": f"multiple_{normalized_key}",
            "title": f"Multiple sections found for {normalized_key}",
            "text": f"Found {len(filtered_matches)} sections of {normalized_key}. Here are the options:",
            "multiple_results": True,
            "results": [format_course_result(m['course'], m['term_code'], from_cache=True) 
                       for m in filtered_matches],
            "metadata": {
                "course_number": normalized_key,
                "match_count": len(filtered_matches),
                "tip": "Use filters to narrow down: section, campus (online/atlanta), instructor"
            }
        }
    
    # No matches after filtering
    else:
        return {
            "id": "no_matches",
            "title": f"No matching sections for {normalized_key} in {get_term_name(term_code)}",
            "text": f"No sections of {normalized_key} match your filters in {get_term_name(term_code)}: {filters}",
            "metadata": {
                "course_number": normalized_key,
                "semester": semester,
                "term_code": term_code,
                "filters_applied": filters,
                "available_count": len(all_matches),
                "tip": "Try different filters or remove some filters"
            }
        }


def handle_mcp_request(request: dict) -> dict:
    """Handle incoming MCP request for ChatGPT"""
    method = request.get('method')
    params = request.get('params', {})
    request_id = request.get('id')
    
    try:
        if method == 'initialize':
            # Handle MCP initialization handshake
            return create_mcp_response(request_id, {
                "protocolVersion": "2025-06-18",
                "serverInfo": {
                    "name": "Georgia Tech MCP Server",
                    "version": "3.0.0"
                },
                "capabilities": {
                    "tools": {
                        "search": {
                            "description": "Search Georgia Tech courses and research papers. Multiple examples below:",
                            "inputSchema": {
                                "type": "object",
                                "properties": {
                                    "query": {
                                        "type": "string",
                                        "description": "Search query - see examples below",
                                        "examples": [
                                            "CS 6515",
                                            "Fall 2025 CS courses",
                                            "Spring 2025 machine learning",
                                            "OMSCS algorithms",
                                            "CS 7641 Fall 2024",
                                            "waitlist CS 6300",
                                            "online CS courses",
                                            "robotics research papers"
                                        ]
                                    }
                                },
                                "required": ["query"]
                            }
                        },
                        "fetch": {
                            "description": "Fetch detailed information for a specific course in a specific semester. Use additional filters to get specific sections when multiple exist.",
                            "inputSchema": {
                                "type": "object",
                                "properties": {
                                    "course_number": {
                                        "type": "string",
                                        "description": "Course number (e.g., 'CS 6515', 'MATH 1551')"
                                    },
                                    "semester": {
                                        "type": "string",
                                        "description": "Semester (e.g., 'Fall 2024', 'Spring 2025', '202408')"
                                    },
                                    "filters": {
                                        "type": "object",
                                        "description": "Optional filters to narrow down results when multiple sections exist",
                                        "properties": {
                                            "section": {
                                                "type": "string",
                                                "description": "Filter by section (e.g., 'A', 'B', 'O01' for online)"
                                            },
                                            "campus": {
                                                "type": "string",
                                                "description": "Filter by campus/mode (e.g., 'online', 'omscs', 'atlanta', 'campus')"
                                            },
                                            "instructor": {
                                                "type": "string",
                                                "description": "Filter by instructor name (partial match)"
                                            }
                                        }
                                    }
                                },
                                "required": ["course_number", "semester"]
                            }
                        },
                        "help": {
                            "description": "Get help on how to use this MCP server effectively",
                            "inputSchema": {
                                "type": "object",
                                "properties": {
                                    "topic": {
                                        "type": "string",
                                        "description": "Optional: specific help topic (search, fetch, semesters)",
                                        "enum": ["search", "fetch", "semesters"]
                                    }
                                }
                            }
                        }
                    }
                }
            })
            
        elif method == 'tools/list':
            # List available tools
            return create_mcp_response(request_id, {
                "tools": [
                    {
                        "name": "search",
                        "description": "Search Georgia Tech courses and research papers. Returns up to 10 results from recent/upcoming semesters.",
                        "inputSchema": {
                            "type": "object",
                            "properties": {
                                "query": {
                                    "type": "string", 
                                    "description": "Search query - can be course codes, topics, semesters, or combinations"
                                }
                            },
                            "required": ["query"],
                            "examples": [
                                {"query": "CS 6515", "description": "Find Graduate Algorithms course"},
                                {"query": "Fall 2025 CS courses", "description": "CS courses in Fall 2025"},
                                {"query": "Spring 2025 machine learning", "description": "ML courses in Spring 2025"},
                                {"query": "OMSCS algorithms", "description": "Online MS algorithm courses"},
                                {"query": "CS 7641 waitlist", "description": "Check ML course waitlist status"},
                                {"query": "online CS 6300", "description": "Online sections of Software Dev Process"},
                                {"query": "robotics research papers", "description": "Search research papers"}
                            ]
                        }
                    },
                    {
                        "name": "fetch",
                        "description": "Fetch detailed information for a specific course in a specific semester. Use additional filters to get specific sections when multiple exist.",
                        "inputSchema": {
                            "type": "object",
                            "properties": {
                                "course_number": {
                                    "type": "string", 
                                    "description": "Course number (e.g., 'CS 6515', 'MATH 1551')"
                                },
                                "semester": {
                                    "type": "string",
                                    "description": "Semester (e.g., 'Fall 2024', 'Spring 2025', '202408')"
                                },
                                "filters": {
                                    "type": "object",
                                    "description": "Optional filters to narrow down results when multiple sections exist",
                                    "properties": {
                                        "section": {
                                            "type": "string",
                                            "description": "Filter by section (e.g., 'A', 'B', 'O01' for online)"
                                        },
                                        "campus": {
                                            "type": "string",
                                            "description": "Filter by campus/mode (e.g., 'online', 'omscs', 'atlanta', 'campus')"
                                        },
                                        "instructor": {
                                            "type": "string",
                                            "description": "Filter by instructor name (partial match)"
                                        }
                                    }
                                }
                            },
                            "required": ["course_number", "semester"],
                            "examples": [
                                {"course_number": "CS 6515", "semester": "Fall 2024"},
                                {"course_number": "CS 1301", "semester": "Spring 2025"},
                                {"course_number": "CS 6515", "semester": "Fall 2024", "filters": {"campus": "online"}},
                                {"course_number": "MATH 1551", "semester": "Fall 2024", "filters": {"section": "A"}}
                            ]
                        }
                    },
                    {
                        "name": "help",
                        "description": "Get help on how to use this MCP server effectively",
                        "inputSchema": {
                            "type": "object",
                            "properties": {
                                "topic": {
                                    "type": "string",
                                    "description": "Optional: specific help topic (search, fetch, semesters)",
                                    "enum": ["search", "fetch", "semesters"]
                                }
                            },
                            "examples": [
                                {},
                                {"topic": "search"},
                                {"topic": "semesters"}
                            ]
                        }
                    }
                ]
            })
            
        elif method == 'tools/call':
            # Handle tool calls
            tool_name = params.get('name')
            tool_args = params.get('arguments', {})
            
            if tool_name == 'search':
                query = tool_args.get('query', '')
                results = handle_search(query)
                # Always wrap results in a dict for ChatGPT
                if isinstance(results, list):
                    # Wrap list results in a dict with "results" key
                    wrapped_results = {
                        "results": results,
                        "count": len(results)
                    }
                    return create_mcp_response(request_id, {
                        "content": [{"type": "text", "text": json.dumps(wrapped_results)}]
                    })
                elif isinstance(results, dict) and 'results' in results:
                    # Already in correct format
                    return create_mcp_response(request_id, {
                        "content": [{"type": "text", "text": json.dumps(results)}]
                    })
                else:
                    # Unknown format - wrap it anyway
                    wrapped_results = {
                        "results": results if isinstance(results, list) else [results],
                        "count": len(results) if isinstance(results, list) else 1
                    }
                    return create_mcp_response(request_id, {
                        "content": [{"type": "text", "text": json.dumps(wrapped_results)}]
                    })
                
            elif tool_name == 'fetch':
                course_number = tool_args.get('course_number', '')
                semester = tool_args.get('semester', '')
                
                if not course_number or not semester:
                    return create_mcp_error(request_id, -32602, "Both 'course_number' and 'semester' are required parameters")
                
                # Extract filters from arguments
                filters = {}
                if 'filters' in tool_args and isinstance(tool_args['filters'], dict):
                    filters = tool_args['filters']
                
                result = handle_fetch(course_number, semester, filters)
                if result:
                    return create_mcp_response(request_id, {
                        "content": [{"type": "text", "text": json.dumps(result)}]
                    })
                else:
                    return create_mcp_error(request_id, -32602, f"Course {course_number} not found for {semester}. Try a different semester or verify the course number.")
                    
            elif tool_name == 'help':
                topic = tool_args.get('topic', None)
                result = handle_help(topic)
                return create_mcp_response(request_id, {
                    "content": [{"type": "text", "text": json.dumps(result)}]
                })
                    
            else:
                return create_mcp_error(request_id, -32601, f"Unknown tool: {tool_name}. Available tools: search, fetch, help")
                
        # Legacy support for direct method calls
        elif method == 'search':
            query = params.get('query', '')
            results = handle_search(query)
            # Handle both new dict format and legacy list format
            if isinstance(results, dict) and 'results' in results:
                # Return just the results array for backwards compatibility
                return create_mcp_response(request_id, results['results'])
            else:
                return create_mcp_response(request_id, results)
            
        elif method == 'fetch':
            course_number = params.get('course_number', '')
            semester = params.get('semester', '')
            
            if not course_number or not semester:
                return create_mcp_error(request_id, -32602, "Both 'course_number' and 'semester' are required parameters")
            
            # Extract filters from params - support nested format
            filters = {}
            if 'filters' in params and isinstance(params['filters'], dict):
                filters = params['filters']
            
            result = handle_fetch(course_number, semester, filters)
            if result:
                return create_mcp_response(request_id, result)
            else:
                return create_mcp_error(request_id, -32602, f"Course {course_number} not found for {semester}. Try a different semester or verify the course number.")
                
        elif method == 'help':
            topic = params.get('topic', None)
            result = handle_help(topic)
            return create_mcp_response(request_id, result)
                
        else:
            return create_mcp_error(request_id, -32601, f"Method not found: {method}. Available methods: initialize, tools/list, tools/call, search, fetch, help")
            
    except Exception as e:
        logger.error(f"Error handling request: {e}")
        error_msg = str(e)
        if "query" in error_msg.lower():
            error_msg += ". Try a simpler query like 'CS 1301' or 'machine learning'."
        return create_mcp_error(request_id, -32603, error_msg)


async def sse_generator(request_body: dict):
    """Generate Server-Sent Events for MCP"""
    response = handle_mcp_request(request_body)
    
    # Send response as SSE
    yield f"data: {json.dumps(response)}\n\n"


@app.post("/sse/")
async def mcp_sse_endpoint(request: Request):
    """SSE endpoint for MCP requests"""
    try:
        body = await request.json()
        logger.info(f"Received MCP request: {json.dumps(body, indent=2)}")
        
        # Handle both direct tool calls and JSON-RPC format
        if 'method' in body:
            # Standard JSON-RPC format
            pass
        elif 'tool' in body:
            # Direct tool call format - convert to JSON-RPC
            tool = body.get('tool')
            args = body.get('args', {})
            
            # Convert to standard format
            body = {
                "jsonrpc": "2.0",
                "id": body.get('id', "1"),
                "method": tool,
                "params": args
            }
            logger.info(f"Converted request to: {json.dumps(body, indent=2)}")
        
        return StreamingResponse(
            sse_generator(body),
            media_type="text/event-stream",
            headers={
                "Cache-Control": "no-cache",
                "Connection": "keep-alive",
                "X-Accel-Buffering": "no",  # Disable nginx buffering
            }
        )
    except Exception as e:
        logger.error(f"Error in SSE endpoint: {e}", exc_info=True)
        return Response(
            content=json.dumps({"error": str(e)}),
            status_code=500,
            media_type="application/json"
        )


@app.get("/")
async def root():
    """Root endpoint with server info for MCP discovery"""
    return {
        "mcp": {
            "version": "3.0.0",
            "name": "Georgia Tech MCP Server",
            "description": "Search Georgia Tech courses and research papers",
            "tools": {
                "search": {
                    "description": "Search Georgia Tech courses and research papers. Try: 'CS 6515', 'Fall 2025 algorithms', 'Spring 2025 OMSCS', 'machine learning online', 'CS 7641 waitlist'. Searches recent & upcoming semesters.",
                    "inputSchema": {
                        "type": "object",
                        "properties": {
                            "query": {
                                "type": "string",
                                "description": "Search query. Examples: 'CS 1301', 'CS 6515', 'machine learning', 'OMSCS', 'robotics research'"
                            }
                        },
                        "required": ["query"]
                    }
                },
                "fetch": {
                    "description": "Fetch detailed information for a specific course in a specific semester. Use additional filters to get specific sections when multiple exist.",
                    "inputSchema": {
                        "type": "object",
                        "properties": {
                            "course_number": {
                                "type": "string",
                                "description": "Course number (e.g., 'CS 6515', 'MATH 1551')"
                            },
                            "semester": {
                                "type": "string",
                                "description": "Semester (e.g., 'Fall 2024', 'Spring 2025', '202408')"
                            },
                            "filters": {
                                "type": "object",
                                "description": "Optional filters to narrow down results when multiple sections exist",
                                "properties": {
                                    "section": {
                                        "type": "string",
                                        "description": "Filter by section (e.g., 'A', 'B', 'O01' for online)"
                                    },
                                    "campus": {
                                        "type": "string",
                                        "description": "Filter by campus/mode (e.g., 'online', 'omscs', 'atlanta', 'campus')"
                                    },
                                    "instructor": {
                                        "type": "string",
                                        "description": "Filter by instructor name (partial match)"
                                    }
                                }
                            }
                        },
                        "required": ["course_number", "semester"]
                    }
                },
                "help": {
                    "description": "Get help on how to use this MCP server effectively",
                    "inputSchema": {
                        "type": "object",
                        "properties": {
                            "topic": {
                                "type": "string",
                                "description": "Optional: specific help topic (search, fetch, semesters)",
                                "enum": ["search", "fetch", "semesters"]
                            }
                        }
                    }
                }
            }
        }
    }


@app.get("/health")
async def health():
    """Health check endpoint"""
    return {
        "status": "healthy",
        "timestamp": datetime.utcnow().isoformat(),
        "services": {
            "oscar": "healthy",
            "smartech": "healthy"
        }
    }


@app.get("/mcp/tools")
async def list_tools():
    """List available MCP tools for ChatGPT"""
    return {
        "tools": [
            {
                "name": "search",
                "description": "Search for Georgia Tech courses and research papers",
                "input_schema": {
                    "type": "object",
                    "properties": {
                        "query": {
                            "type": "string",
                            "description": "Search query for courses or research papers"
                        }
                    },
                    "required": ["query"]
                }
            },
            {
                "name": "fetch",
                "description": "Fetch detailed information for a specific course or research paper",
                "input_schema": {
                    "type": "object",
                    "properties": {
                        "id": {
                            "type": "string",
                            "description": "Unique identifier for the document to fetch"
                        }
                    },
                    "required": ["id"]
                }
            }
        ]
    }


def main():
    """Main entry point"""
    # Get configuration from environment or defaults
    host = os.getenv('MCP_HOST', '0.0.0.0')
    port = int(os.getenv('MCP_PORT', '8080'))
    
    # SSL configuration
    ssl_cert = os.getenv('SSL_CERT', '/etc/letsencrypt/live/wmjump1.henkelman.net/fullchain.pem')
    ssl_key = os.getenv('SSL_KEY', '/etc/letsencrypt/live/wmjump1.henkelman.net/privkey.pem')
    
    # Check if SSL files exist
    use_ssl = os.path.exists(ssl_cert) and os.path.exists(ssl_key)
    
    if use_ssl:
        logger.info(f"Starting MCP server with SSL on https://{host}:{port}")
        uvicorn.run(
            app,
            host=host,
            port=port,
            ssl_certfile=ssl_cert,
            ssl_keyfile=ssl_key,
            log_level="info"
        )
    else:
        logger.info(f"Starting MCP server without SSL on http://{host}:{port}")
        uvicorn.run(
            app,
            host=host,
            port=port,
            log_level="info"
        )


if __name__ == "__main__":
    main()