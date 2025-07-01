"""Tests for the GT OSCAR scraper."""

import pytest
import responses
from unittest.mock import Mock, patch
import requests

from gtmcp.scraper import GTOscarScraper
from gtmcp.models import Semester, Subject, CourseInfo, CourseDetails


class TestGTOscarScraperInit:
    """Tests for scraper initialization."""
    
    def test_default_initialization(self):
        """Test scraper with default parameters."""
        scraper = GTOscarScraper()
        assert scraper.delay == 1.0
        assert scraper.timeout == 30
        assert scraper.max_retries == 3
        assert scraper.session is not None
        
    def test_custom_initialization(self):
        """Test scraper with custom parameters."""
        scraper = GTOscarScraper(delay=0.5, timeout=60, max_retries=5)
        assert scraper.delay == 0.5
        assert scraper.timeout == 60
        assert scraper.max_retries == 5


class TestScraperRequests:
    """Tests for request handling."""
    
    def test_make_request_success(self, scraper):
        """Test successful request."""
        with responses.RequestsMock() as rsps:
            rsps.add(responses.GET, "https://example.com", body="success", status=200)
            
            response = scraper._make_request("GET", "https://example.com")
            assert response.text == "success"
            assert response.status_code == 200
            
    def test_make_request_with_timeout(self, scraper):
        """Test request with timeout parameter."""
        with responses.RequestsMock() as rsps:
            rsps.add(responses.GET, "https://example.com", body="success", status=200)
            
            response = scraper._make_request("GET", "https://example.com", timeout=10)
            assert response.text == "success"
            
    def test_make_request_failure(self, scraper):
        """Test request failure."""
        with responses.RequestsMock() as rsps:
            rsps.add(responses.GET, "https://example.com", status=500)
            
            with pytest.raises(Exception) as exc_info:
                scraper._make_request("GET", "https://example.com")
            assert "Request failed after" in str(exc_info.value)
            
    def test_make_request_retry_logic(self):
        """Test retry logic with exponential backoff."""
        scraper = GTOscarScraper(delay=0.01, max_retries=3)  # Fast for testing
        
        with responses.RequestsMock() as rsps:
            # First two attempts fail, third succeeds
            rsps.add(responses.GET, "https://example.com", status=500)
            rsps.add(responses.GET, "https://example.com", status=500)
            rsps.add(responses.GET, "https://example.com", body="success", status=200)
            
            response = scraper._make_request("GET", "https://example.com")
            assert response.text == "success"
            assert len(rsps.calls) == 3
            
    def test_make_request_max_retries_exceeded(self):
        """Test when max retries are exceeded."""
        scraper = GTOscarScraper(delay=0.01, max_retries=2)
        
        with responses.RequestsMock() as rsps:
            # All attempts fail
            rsps.add(responses.GET, "https://example.com", status=500)
            rsps.add(responses.GET, "https://example.com", status=500)
            
            with pytest.raises(Exception) as exc_info:
                scraper._make_request("GET", "https://example.com")
            assert "Request failed after 2 attempts" in str(exc_info.value)


class TestGetAvailableSemesters:
    """Tests for getting available semesters."""
    
    @responses.activate
    def test_get_available_semesters_success(self, scraper, mock_semester_response):
        """Test successful semester retrieval."""
        responses.add(
            responses.GET,
            scraper.SEMESTER_URL,
            body=mock_semester_response,
            status=200
        )
        
        semesters = scraper.get_available_semesters()
        
        assert len(semesters) == 4  # All non-None options
        assert semesters[0].code == "202502"
        assert semesters[0].name == "Spring 2025"
        assert semesters[0].view_only is False
        
        # Find the view-only semester
        view_only_semester = [s for s in semesters if s.view_only][0]
        assert view_only_semester.code == "202402"
        assert view_only_semester.name == "Spring 2024"  # "(View only)" removed
        assert view_only_semester.view_only is True
        
    @responses.activate
    def test_get_available_semesters_no_select(self, scraper):
        """Test when semester select dropdown is missing."""
        responses.add(
            responses.GET,
            scraper.SEMESTER_URL,
            body="<html><body>No select element</body></html>",
            status=200
        )
        
        with pytest.raises(Exception) as exc_info:
            scraper.get_available_semesters()
        assert "Could not find semester selection dropdown" in str(exc_info.value)
        
    @responses.activate
    def test_get_available_semesters_request_failure(self, scraper):
        """Test when request fails."""
        responses.add(
            responses.GET,
            scraper.SEMESTER_URL,
            status=500
        )
        
        with pytest.raises(Exception):
            scraper.get_available_semesters()


class TestGetSubjects:
    """Tests for getting available subjects."""
    
    @responses.activate
    def test_get_subjects_success(self, scraper, mock_subjects_response):
        """Test successful subject retrieval."""
        # First request for term submission
        responses.add(
            responses.POST,
            scraper.TERM_SUBMIT_URL,
            body=mock_subjects_response,
            status=200
        )
        
        subjects = scraper.get_subjects("202502")
        
        assert len(subjects) == 4
        assert subjects[0].code == "CS"
        assert subjects[0].name == "Computer Science"
        assert subjects[1].code == "MATH"
        assert subjects[1].name == "Mathematics"
        
    @responses.activate
    def test_get_subjects_no_select(self, scraper):
        """Test when subjects select dropdown is missing."""
        responses.add(
            responses.POST,
            scraper.TERM_SUBMIT_URL,
            body="<html><body>No subjects</body></html>",
            status=200
        )
        
        with pytest.raises(Exception) as exc_info:
            scraper.get_subjects("202502")
        assert "Could not find subject selection dropdown" in str(exc_info.value)
        
    @responses.activate  
    def test_get_subjects_empty_term_code(self, scraper):
        """Test with empty term code."""
        responses.add(
            responses.POST,
            scraper.TERM_SUBMIT_URL,
            body="<html><body>Error</body></html>",
            status=400
        )
        
        with pytest.raises(Exception):
            scraper.get_subjects("")


class TestSearchCourses:
    """Tests for course search functionality."""
    
    @responses.activate
    def test_search_courses_success(self, scraper, mock_courses_response):
        """Test successful course search."""
        responses.add(
            responses.POST,
            scraper.COURSE_SEARCH_URL,
            body=mock_courses_response,
            status=200
        )
        
        courses = scraper.search_courses("202502", "CS")
        
        assert len(courses) == 2
        assert courses[0].crn == "12345"
        assert courses[0].title == "Intro to Programming"
        assert courses[0].subject == "CS"
        assert courses[0].course_number == "1301"
        assert courses[0].section == "A"
        
        assert courses[1].crn == "12346"
        assert courses[1].title == "Data Structures"
        assert courses[1].subject == "CS"
        assert courses[1].course_number == "1332"
        assert courses[1].section == "B"
        
    @responses.activate
    def test_search_courses_with_filters(self, scraper, mock_courses_response):
        """Test course search with additional filters."""
        responses.add(
            responses.POST,
            scraper.COURSE_SEARCH_URL,
            body=mock_courses_response,
            status=200
        )
        
        courses = scraper.search_courses("202502", "CS", course_num="1301", title="Intro")
        assert len(courses) == 2  # Mock response has 2 courses
        
    @responses.activate
    def test_search_courses_no_results(self, scraper):
        """Test course search with no results."""
        no_courses_response = """
        <html>
        <body>
            <table class="datadisplaytable">
                <caption class="captiontext">Sections Found</caption>
                <!-- No course rows -->
            </table>
        </body>
        </html>
        """
        
        responses.add(
            responses.POST,
            scraper.COURSE_SEARCH_URL,
            body=no_courses_response,
            status=200
        )
        
        courses = scraper.search_courses("202502", "CS")
        assert len(courses) == 0
        
    @responses.activate
    def test_search_courses_malformed_response(self, scraper):
        """Test course search with malformed course data."""
        malformed_response = """
        <html>
        <body>
            <table class="datadisplaytable">
                <tr>
                    <th class="ddtitle">
                        <a href="/invalid_url">Malformed Course Data</a>
                    </th>
                </tr>
            </table>
        </body>
        </html>
        """
        
        responses.add(
            responses.POST,
            scraper.COURSE_SEARCH_URL,
            body=malformed_response,
            status=200
        )
        
        courses = scraper.search_courses("202502", "CS")
        assert len(courses) == 0  # Should skip malformed entries


class TestGetCourseDetails:
    """Tests for getting course details."""
    
    @responses.activate
    def test_get_course_details_success(self, scraper, mock_course_details_response):
        """Test successful course details retrieval."""
        responses.add(
            responses.GET,
            f"{scraper.COURSE_DETAIL_URL_TEMPLATE}?term_in=202502&crn_in=12345",
            body=mock_course_details_response,
            status=200
        )
        
        details = scraper.get_course_details("202502", "12345")
        
        assert details.crn == "12345"
        assert details.title == "Intro to Programming"
        assert details.subject == "CS"
        assert details.course_number == "1301"
        assert details.section == "A"
        assert details.term == "Spring 2025"
        assert details.credits == 3.0
        assert "Lecture" in details.schedule_type
        assert "Georgia Tech-Atlanta" in details.campus
        assert "Undergraduate Semester" in details.levels
        
        # Test registration info
        assert details.registration.seats_capacity == 50
        assert details.registration.seats_actual == 30
        assert details.registration.seats_remaining == 20
        assert details.registration.waitlist_capacity == 10
        assert details.registration.waitlist_actual == 5
        assert details.registration.waitlist_remaining == 5
        
        # Test restrictions
        assert len(details.restrictions) > 0
        assert "Computer Science major" in details.restrictions[0]
        
        # Test catalog URL
        assert details.catalog_url is not None
        assert "bwckctlg.p_display_courses" in details.catalog_url
        
    @responses.activate
    def test_get_course_details_no_title(self, scraper):
        """Test course details when title element is missing."""
        minimal_response = """
        <html>
        <body>
            <table class="datadisplaytable">
                <!-- No title element -->
            </table>
        </body>
        </html>
        """
        
        responses.add(
            responses.GET,
            f"{scraper.COURSE_DETAIL_URL_TEMPLATE}?term_in=202502&crn_in=12345",
            body=minimal_response,
            status=200
        )
        
        with pytest.raises(Exception) as exc_info:
            scraper.get_course_details("202502", "12345")
        assert "Could not find course title" in str(exc_info.value)
        
    @responses.activate
    def test_get_course_details_malformed_title(self, scraper):
        """Test course details with malformed title."""
        malformed_response = """
        <html>
        <body>
            <table class="datadisplaytable">
                <tr>
                    <th class="ddlabel">Malformed Title Format</th>
                </tr>
            </table>
        </body>
        </html>
        """
        
        responses.add(
            responses.GET,
            f"{scraper.COURSE_DETAIL_URL_TEMPLATE}?term_in=202502&crn_in=12345",
            body=malformed_response,
            status=200
        )
        
        with pytest.raises(Exception) as exc_info:
            scraper.get_course_details("202502", "12345")
        assert "Unexpected title format" in str(exc_info.value)


class TestParseRegistrationTable:
    """Tests for registration table parsing."""
    
    def test_parse_registration_table_success(self, scraper):
        """Test successful registration table parsing."""
        from bs4 import BeautifulSoup
        
        html = """
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
        """
        
        soup = BeautifulSoup(html, 'html.parser')
        table = soup.find('table')
        
        reg_info = scraper._parse_registration_table(table)
        
        assert reg_info.seats_capacity == 50
        assert reg_info.seats_actual == 30
        assert reg_info.seats_remaining == 20
        assert reg_info.waitlist_capacity == 10
        assert reg_info.waitlist_actual == 5
        assert reg_info.waitlist_remaining == 5
        
    def test_parse_registration_table_no_table(self, scraper):
        """Test parsing when table is None."""
        reg_info = scraper._parse_registration_table(None)
        
        assert reg_info.seats_capacity == 0
        assert reg_info.seats_actual == 0
        assert reg_info.seats_remaining == 0
        assert reg_info.waitlist_capacity == 0
        assert reg_info.waitlist_actual == 0
        assert reg_info.waitlist_remaining == 0
        
    def test_parse_registration_table_invalid_data(self, scraper):
        """Test parsing table with invalid numeric data."""
        from bs4 import BeautifulSoup
        
        html = """
        <table class="datadisplaytable">
            <tr>
                <th class="ddlabel">Seats</th>
                <td class="dddefault">invalid</td>
                <td class="dddefault">data</td>
                <td class="dddefault">here</td>
            </tr>
        </table>
        """
        
        soup = BeautifulSoup(html, 'html.parser')
        table = soup.find('table')
        
        reg_info = scraper._parse_registration_table(table)
        
        # Should return zeros when parsing fails
        assert reg_info.seats_capacity == 0
        assert reg_info.seats_actual == 0
        assert reg_info.seats_remaining == 0


class TestParseRestrictions:
    """Tests for restrictions parsing."""
    
    def test_parse_restrictions_success(self, scraper):
        """Test successful restrictions parsing."""
        content = """
        Associated Term: Spring 2025
        Levels: Undergraduate Semester
        
        Restrictions:
        Must be enrolled in Computer Science major
        Must be enrolled in Georgia Tech-Atlanta campus
        May not be enrolled in Graduate level
        """
        
        restrictions = scraper._parse_restrictions(content)
        
        assert len(restrictions) == 3
        assert "Computer Science major" in restrictions[0]
        assert "Georgia Tech-Atlanta campus" in restrictions[1]
        assert "Graduate level" in restrictions[2]
        
    def test_parse_restrictions_no_restrictions(self, scraper):
        """Test parsing when no restrictions section exists."""
        content = """
        Associated Term: Spring 2025
        Levels: Undergraduate Semester
        Credits: 3.0
        """
        
        restrictions = scraper._parse_restrictions(content)
        assert len(restrictions) == 0
        
    def test_parse_restrictions_empty_section(self, scraper):
        """Test parsing empty restrictions section."""
        content = """
        Associated Term: Spring 2025
        
        Restrictions:
        
        Credits: 3.0
        """
        
        restrictions = scraper._parse_restrictions(content)
        assert len(restrictions) == 0