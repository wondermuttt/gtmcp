"""Data models for Georgia Tech course information and research data."""

from typing import List, Optional, Dict, Any, Tuple
from datetime import datetime
from pydantic import BaseModel


class Semester(BaseModel):
    """Represents an available semester."""
    code: str
    name: str
    view_only: bool = False


class CourseInfo(BaseModel):
    """Basic course information from search results."""
    crn: str
    title: str
    subject: str
    course_number: str
    section: str
    

class RegistrationInfo(BaseModel):
    """Registration availability information."""
    seats_capacity: int
    seats_actual: int
    seats_remaining: int
    waitlist_capacity: int
    waitlist_actual: int
    waitlist_remaining: int


class CourseDetails(BaseModel):
    """Detailed course information."""
    crn: str
    title: str
    subject: str
    course_number: str
    section: str
    term: str
    credits: float
    schedule_type: str
    campus: str
    levels: List[str]
    registration: RegistrationInfo
    restrictions: List[str]
    catalog_url: Optional[str] = None


class Subject(BaseModel):
    """Course subject/department."""
    code: str
    name: str


# New models for expanded functionality

class ResearchPaper(BaseModel):
    """Research paper from SMARTech repository."""
    oai_identifier: str
    title: str
    authors: List[str]
    abstract: str
    publication_date: datetime
    subject_areas: List[str]
    citation_count: Optional[int] = None
    related_courses: List[str] = []


class FacultyResearchProfile(BaseModel):
    """Faculty research profile."""
    name: str
    department: str
    research_interests: List[str]
    recent_publications: List[ResearchPaper]
    active_projects: List[str]
    collaboration_opportunities: List[str]


class CampusLocation(BaseModel):
    """Campus building or location."""
    building_id: str
    building_name: str
    address: str
    gps_coordinates: Optional[Tuple[float, float]] = None
    accessibility_features: List[str] = []
    available_services: List[str] = []
    operating_hours: Dict[str, str] = {}
    capacity_info: Optional[Dict[str, int]] = None


class RouteStep(BaseModel):
    """A step in a campus route."""
    location: CampusLocation
    instruction: str
    distance_meters: int
    time_minutes: int


class RouteOptimization(BaseModel):
    """Optimized route between campus locations."""
    start_location: CampusLocation
    destinations: List[CampusLocation]
    optimal_path: List[RouteStep]
    total_time_minutes: int
    total_distance_meters: int
    accessibility_compliant: bool
    alternative_routes: List["RouteOptimization"] = []


class ResearchEquipment(BaseModel):
    """Research equipment and resources."""
    equipment_id: str
    name: str
    description: str
    location: CampusLocation
    availability_schedule: Dict[str, List[str]] = {}
    technical_specifications: Dict[str, Any] = {}
    usage_requirements: List[str] = []
    related_research_areas: List[str] = []
    booking_policies: List[str] = []


class TimeSlot(BaseModel):
    """Time slot for scheduling."""
    start_time: datetime
    end_time: datetime
    available: bool
    notes: Optional[str] = None


class SemesterPlan(BaseModel):
    """Academic plan for a semester."""
    semester: Semester
    courses: List[CourseInfo]
    credits: int
    research_opportunities: List[str] = []
    equipment_needs: List[str] = []


class DegreePathPlan(BaseModel):
    """Multi-semester degree planning."""
    semesters: List[SemesterPlan]
    total_credits: int
    graduation_date: datetime
    prerequisite_violations: List[str] = []
    optimization_suggestions: List[str] = []


class FacultyMatch(BaseModel):
    """Faculty member matched to course or research area."""
    name: str
    department: str
    match_score: float
    research_overlap: List[str]
    contact_info: Optional[str] = None


class EnhancedCourseDetails(CourseDetails):
    """Enhanced course details with research connections."""
    prerequisites: List[str] = []
    corequisites: List[str] = []
    related_research_areas: List[str] = []
    faculty_research_match: List[FacultyMatch] = []
    career_pathway_relevance: List[str] = []