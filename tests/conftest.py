"""Pytest configuration and fixtures."""

import pytest
from unittest.mock import Mock, MagicMock
import responses
from bs4 import BeautifulSoup

from gtmcp.config import Config
from gtmcp.scraper import GTOscarScraper
from gtmcp.models import Semester, Subject, CourseInfo, CourseDetails, RegistrationInfo


@pytest.fixture
def config():
    """Test configuration."""
    return Config()


@pytest.fixture
def scraper():
    """Test scraper instance."""
    return GTOscarScraper(delay=0.0)  # No delay for tests


@pytest.fixture
def mock_semester_response():
    """Mock HTML response for semester selection page."""
    return """
    <!DOCTYPE HTML>
    <html>
    <head><title>Select Term or Date Range</title></head>
    <body>
        <form action="/bprod/bwckgens.p_proc_term_date" method="post">
            <select name="p_term">
                <option value="">None</option>
                <option value="202502">Spring 2025</option>
                <option value="202505">Summer 2025</option>
                <option value="202508">Fall 2025</option>
                <option value="202402">Spring 2024 (View only)</option>
            </select>
        </form>
    </body>
    </html>
    """


@pytest.fixture
def mock_subjects_response():
    """Mock HTML response for course search form with subjects."""
    return """
    <!DOCTYPE HTML>
    <html>
    <head><title>Class Schedule Search</title></head>
    <body>
        <form action="/bprod/bwckschd.p_get_crse_unsec" method="post">
            <select name="sel_subj" size="10" multiple>
                <option value="CS">Computer Science</option>
                <option value="MATH">Mathematics</option>
                <option value="EE">Electrical Engineering</option>
                <option value="PHYS">Physics</option>
            </select>
        </form>
    </body>
    </html>
    """


@pytest.fixture
def mock_courses_response():
    """Mock HTML response for course search results."""
    return """
    <!DOCTYPE HTML>
    <html>
    <head><title>Class Schedule Listing</title></head>
    <body>
        <table class="datadisplaytable">
            <caption class="captiontext">Sections Found</caption>
            <tr>
                <th class="ddtitle">
                    <a href="/bprod/bwckschd.p_disp_detail_sched?term_in=202502&crn_in=12345">
                        Intro to Programming - 12345 - CS 1301 - A
                    </a>
                </th>
            </tr>
            <tr>
                <th class="ddtitle">
                    <a href="/bprod/bwckschd.p_disp_detail_sched?term_in=202502&crn_in=12346">
                        Data Structures - 12346 - CS 1332 - B
                    </a>
                </th>
            </tr>
        </table>
    </body>
    </html>
    """


@pytest.fixture
def mock_course_details_response():
    """Mock HTML response for course details."""
    return """
    <!DOCTYPE HTML>
    <html>
    <head><title>Detailed Class Information</title></head>
    <body>
        <table class="datadisplaytable">
            <tr>
                <th class="ddlabel">Intro to Programming - 12345 - CS 1301 - A</th>
            </tr>
            <tr>
                <td class="dddefault">
                    Associated Term: Spring 2025<br>
                    Levels: Undergraduate Semester<br>
                    Georgia Tech-Atlanta * Campus<br>
                    Lecture* Schedule Type<br>
                    3.000 Credits<br>
                    <a href="/bprod/bwckctlg.p_display_courses?term_in=202502&one_subj=CS&sel_crse_strt=1301&sel_crse_end=1301">View Catalog Entry</a>
                    
                    <table class="datadisplaytable">
                        <caption class="captiontext">Registration Availability</caption>
                        <tr>
                            <th class="ddlabel">Seats</th>
                            <td class="dddefault">50</td>
                            <td class="dddefault">30</td>
                            <td class="dddefault">20</td>
                        </tr>
                        <tr>
                            <th class="ddlabel">Waitlist Seats</th>
                            <td class="dddefault">10</td>
                            <td class="dddefault">5</td>
                            <td class="dddefault">5</td>
                        </tr>
                    </table>
                    
                    Restrictions:<br>
                    Must be enrolled in Computer Science major<br>
                    Must be enrolled in Georgia Tech-Atlanta campus<br>
                </td>
            </tr>
        </table>
    </body>
    </html>
    """


@pytest.fixture
def sample_semester():
    """Sample semester model."""
    return Semester(code="202502", name="Spring 2025", view_only=False)


@pytest.fixture
def sample_subject():
    """Sample subject model."""
    return Subject(code="CS", name="Computer Science")


@pytest.fixture
def sample_course_info():
    """Sample course info model."""
    return CourseInfo(
        crn="12345",
        title="Intro to Programming",
        subject="CS",
        course_number="1301",
        section="A"
    )


@pytest.fixture
def sample_course_details():
    """Sample course details model."""
    return CourseDetails(
        crn="12345",
        title="Intro to Programming",
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
        restrictions=["Must be enrolled in Computer Science major"],
        catalog_url="https://oscar.gatech.edu/bprod/bwckctlg.p_display_courses?term_in=202502&one_subj=CS&sel_crse_strt=1301&sel_crse_end=1301"
    )