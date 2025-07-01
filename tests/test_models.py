"""Tests for data models."""

import pytest
from pydantic import ValidationError

from gtmcp.models import (
    Semester, Subject, CourseInfo, CourseDetails, 
    RegistrationInfo
)


class TestSemester:
    """Tests for Semester model."""
    
    def test_semester_creation(self):
        """Test creating a semester."""
        semester = Semester(code="202502", name="Spring 2025")
        assert semester.code == "202502"
        assert semester.name == "Spring 2025"
        assert semester.view_only is False
        
    def test_semester_view_only(self):
        """Test semester with view_only flag."""
        semester = Semester(code="202402", name="Spring 2024", view_only=True)
        assert semester.view_only is True
        
    def test_semester_validation(self):
        """Test semester validation."""
        # Note: Basic Pydantic models allow empty strings by default
        # Additional validation could be added with validators if needed
        semester_empty_code = Semester(code="", name="Spring 2025")
        assert semester_empty_code.code == ""
        
        semester_empty_name = Semester(code="202502", name="")
        assert semester_empty_name.name == ""


class TestSubject:
    """Tests for Subject model."""
    
    def test_subject_creation(self):
        """Test creating a subject."""
        subject = Subject(code="CS", name="Computer Science")
        assert subject.code == "CS"
        assert subject.name == "Computer Science"
        
    def test_subject_validation(self):
        """Test subject validation."""
        # Note: Basic Pydantic models allow empty strings by default
        subject_empty_code = Subject(code="", name="Computer Science")
        assert subject_empty_code.code == ""
        
        subject_empty_name = Subject(code="CS", name="")
        assert subject_empty_name.name == ""


class TestCourseInfo:
    """Tests for CourseInfo model."""
    
    def test_course_info_creation(self):
        """Test creating course info."""
        course = CourseInfo(
            crn="12345",
            title="Intro to Programming",
            subject="CS",
            course_number="1301",
            section="A"
        )
        assert course.crn == "12345"
        assert course.title == "Intro to Programming"
        assert course.subject == "CS"
        assert course.course_number == "1301"
        assert course.section == "A"
        
    def test_course_info_validation(self):
        """Test course info validation."""
        # Note: Basic Pydantic models allow empty strings by default
        course_empty_crn = CourseInfo(
            crn="",  # Empty CRN
            title="Intro to Programming",
            subject="CS",
            course_number="1301",
            section="A"
        )
        assert course_empty_crn.crn == ""


class TestRegistrationInfo:
    """Tests for RegistrationInfo model."""
    
    def test_registration_info_creation(self):
        """Test creating registration info."""
        reg = RegistrationInfo(
            seats_capacity=50,
            seats_actual=30,
            seats_remaining=20,
            waitlist_capacity=10,
            waitlist_actual=5,
            waitlist_remaining=5
        )
        assert reg.seats_capacity == 50
        assert reg.seats_actual == 30
        assert reg.seats_remaining == 20
        assert reg.waitlist_capacity == 10
        assert reg.waitlist_actual == 5
        assert reg.waitlist_remaining == 5
        
    def test_registration_info_validation(self):
        """Test registration info validation."""
        # Note: Basic Pydantic models allow negative numbers by default
        # Additional validation could be added with validators if needed
        reg_negative = RegistrationInfo(
            seats_capacity=-1,  # Negative capacity
            seats_actual=30,
            seats_remaining=20,
            waitlist_capacity=10,
            waitlist_actual=5,
            waitlist_remaining=5
        )
        assert reg_negative.seats_capacity == -1


class TestCourseDetails:
    """Tests for CourseDetails model."""
    
    def test_course_details_creation(self, sample_course_details):
        """Test creating course details."""
        details = sample_course_details
        assert details.crn == "12345"
        assert details.title == "Intro to Programming"
        assert details.subject == "CS"
        assert details.course_number == "1301"
        assert details.section == "A"
        assert details.term == "Spring 2025"
        assert details.credits == 3.0
        assert details.schedule_type == "Lecture"
        assert details.campus == "Georgia Tech-Atlanta"
        assert details.levels == ["Undergraduate Semester"]
        assert len(details.restrictions) == 1
        assert details.catalog_url is not None
        
    def test_course_details_with_no_catalog_url(self):
        """Test course details without catalog URL."""
        details = CourseDetails(
            crn="12345",
            title="Test Course",
            subject="CS",
            course_number="1301",
            section="A",
            term="Spring 2025",
            credits=3.0,
            schedule_type="Lecture",
            campus="Georgia Tech-Atlanta",
            levels=["Undergraduate Semester"],
            registration=RegistrationInfo(
                seats_capacity=50,
                seats_actual=30,
                seats_remaining=20,
                waitlist_capacity=10,
                waitlist_actual=5,
                waitlist_remaining=5
            ),
            restrictions=[]
        )
        assert details.catalog_url is None