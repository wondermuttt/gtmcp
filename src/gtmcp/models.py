"""Data models for Georgia Tech course information."""

from typing import List, Optional
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