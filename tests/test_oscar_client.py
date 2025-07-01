"""Tests for the OSCAR client functionality."""

import pytest
from unittest.mock import Mock, patch, MagicMock
import requests
from bs4 import BeautifulSoup

from gtmcp.clients.oscar_client import OscarClient
from gtmcp.clients.base_client import NetworkError, DataParsingError, ValidationError
from gtmcp.models import Semester, Subject, CourseInfo, CourseDetails, RegistrationInfo


class TestOscarClientInit:
    """Test OscarClient initialization."""
    
    def test_init_with_defaults(self):
        """Test initialization with default values."""
        client = OscarClient()
        
        assert client.base_url == "https://oscar.gatech.edu"
        assert client.semester_url == "https://oscar.gatech.edu/pls/bprod/bwckschd.p_disp_dyn_sched"
        assert client.term_submit_url == "https://oscar.gatech.edu/bprod/bwckgens.p_proc_term_date"
        assert client.course_search_url == "https://oscar.gatech.edu/bprod/bwckschd.p_get_crse_unsec"
        assert client.course_detail_url_template == "https://oscar.gatech.edu/bprod/bwckschd.p_disp_detail_sched"


class TestOscarClientConnection:
    """Test OSCAR client connection functionality."""
    
    @patch('gtmcp.clients.oscar_client.OscarClient._make_request')
    def test_connection_success(self, mock_request):
        """Test successful connection to OSCAR."""
        mock_response = Mock()
        mock_response.text = "Schedule of Classes"
        mock_request.return_value = mock_response
        
        client = OscarClient()
        
        with client:
            result = client.test_connection()
        
        assert result is True
        mock_request.assert_called_once_with('GET', client.semester_url)
    
    @patch('gtmcp.clients.oscar_client.OscarClient._make_request')
    def test_connection_failure(self, mock_request):
        """Test failed connection to OSCAR."""
        mock_request.side_effect = Exception("Connection failed")
        
        client = OscarClient()
        
        with client:
            result = client.test_connection()
        
        assert result is False
    
    @pytest.mark.asyncio
    async def test_async_connection_success(self):
        """Test successful async connection to OSCAR."""
        client = OscarClient()
        
        mock_response = Mock()
        mock_response.text.return_value = "bwckschd"
        
        with patch.object(client, '_async_session') as mock_session:
            mock_session.get.return_value.__aenter__.return_value = mock_response
            
            async with client:
                result = await client.atest_connection()
        
        assert result is True


class TestOscarClientSemesters:
    """Test semester retrieval functionality."""
    
    @patch('gtmcp.clients.oscar_client.OscarClient._make_request')
    def test_get_available_semesters_success(self, mock_request):
        """Test successful semester retrieval."""
        html_content = """
        <html>
            <select name="p_term">
                <option value="202502">Spring 2025</option>
                <option value="202408">Fall 2024</option>
                <option value="202205">Spring 2022 (View Only)</option>
            </select>
        </html>
        """
        
        mock_response = Mock()
        mock_response.content = html_content
        mock_request.return_value = mock_response
        
        client = OscarClient()
        
        with client:
            semesters = client.get_available_semesters()
        
        assert len(semesters) == 3
        assert semesters[0].code == "202502"
        assert semesters[0].name == "Spring 2025"
        assert semesters[0].view_only is False
        assert semesters[2].view_only is True
    
    @patch('gtmcp.clients.oscar_client.OscarClient._make_request')
    def test_get_available_semesters_no_dropdown(self, mock_request):
        """Test semester retrieval when dropdown not found."""
        html_content = "<html><body>No dropdown here</body></html>"
        
        mock_response = Mock()
        mock_response.content = html_content
        mock_request.return_value = mock_response
        
        client = OscarClient()
        
        with client:
            with pytest.raises(NetworkError, match="Could not find semester dropdown"):
                client.get_available_semesters()
    
    @patch('gtmcp.clients.oscar_client.OscarClient._make_request')
    def test_get_available_semesters_request_failure(self, mock_request):
        """Test semester retrieval when request fails."""
        mock_request.side_effect = Exception("Request failed")
        
        client = OscarClient()
        
        with client:
            with pytest.raises(NetworkError, match="Failed to fetch available semesters"):
                client.get_available_semesters()


class TestOscarClientSubjects:
    """Test subject retrieval functionality."""
    
    @patch('gtmcp.clients.oscar_client.OscarClient._make_request')
    def test_get_subjects_success(self, mock_request):
        """Test successful subject retrieval."""
        html_content = """
        <html>
            <select name="sel_subj">
                <option value="CS">Computer Science</option>
                <option value="MATH">Mathematics</option>
                <option value="EE">Electrical Engineering</option>
            </select>
        </html>
        """
        
        mock_response = Mock()
        mock_response.content = html_content
        mock_request.return_value = mock_response
        
        client = OscarClient()
        
        with client:
            subjects = client.get_subjects("202502")
        
        assert len(subjects) == 3
        assert subjects[0].code == "CS"
        assert subjects[0].name == "Computer Science"
        assert subjects[1].code == "MATH"
        assert subjects[1].name == "Mathematics"
    
    def test_get_subjects_empty_term_code(self):
        """Test subject retrieval with empty term code."""
        client = OscarClient()
        
        with pytest.raises(ValidationError, match="term_code is required"):
            with client:
                client.get_subjects("")
    
    def test_get_subjects_none_term_code(self):
        """Test subject retrieval with None term code."""
        client = OscarClient()
        
        with pytest.raises(ValidationError, match="term_code is required"):
            with client:
                client.get_subjects(None)


class TestOscarClientCourseSearch:
    """Test course search functionality."""
    
    @patch('gtmcp.clients.oscar_client.OscarClient._make_request')
    def test_get_courses_by_subject_success(self, mock_request):
        """Test successful get_courses_by_subject method."""
        # Mock the term submission response
        term_response = Mock()
        term_response.content = "<html></html>"
        
        # Mock the course listing response
        course_html = """
        <html>
            <table class="datadisplaytable">
                <caption class="captiontext">
                    Intro to Programming - CS 1301 - 12345 - A
                </caption>
            </table>
            <table class="datadisplaytable">
                <caption class="captiontext">
                    Data Structures - CS 1332 - 12346 - B
                </caption>
            </table>
            <table class="datadisplaytable">
                <caption class="captiontext">
                    Machine Learning - CS 7641 - 12347 - C
                </caption>
            </table>
        </html>
        """
        course_response = Mock()
        course_response.content = course_html
        
        mock_request.side_effect = [term_response, course_response]
        
        client = OscarClient()
        
        with client:
            courses = client.get_courses_by_subject("202502", "CS")
        
        assert len(courses) == 3
        assert courses[0].title == "Intro to Programming"
        assert courses[0].subject == "CS"
        assert courses[0].course_number == "1301"
        assert courses[0].crn == "12345"
        assert courses[0].section == "A"
        
        assert courses[1].title == "Data Structures"
        assert courses[1].subject == "CS"
        assert courses[1].course_number == "1332"
        assert courses[1].crn == "12346"
        assert courses[1].section == "B"
        
        assert courses[2].title == "Machine Learning"
        assert courses[2].subject == "CS"
        assert courses[2].course_number == "7641"
        assert courses[2].crn == "12347"
        assert courses[2].section == "C"
    
    @patch.object(OscarClient, 'get_courses_by_subject')
    def test_search_courses_success(self, mock_get_courses):
        """Test successful course search using improved method."""
        # Mock get_courses_by_subject to return all courses
        mock_courses = [
            CourseInfo(
                title="Intro to Programming",
                subject="CS",
                course_number="1301",
                crn="12345",
                section="A"
            ),
            CourseInfo(
                title="Data Structures",
                subject="CS", 
                course_number="1332",
                crn="12346",
                section="B"
            ),
            CourseInfo(
                title="Advanced Programming",
                subject="CS",
                course_number="1331",
                crn="12348",
                section="A"
            )
        ]
        mock_get_courses.return_value = mock_courses
        
        client = OscarClient()
        
        with client:
            # Test basic search (no filters)
            courses = client.search_courses("202502", "CS")
        
        assert len(courses) == 3
        mock_get_courses.assert_called_once_with("202502", "CS")
    
    @patch.object(OscarClient, 'get_courses_by_subject')
    def test_search_courses_with_course_number_filter(self, mock_get_courses):
        """Test course search with course number filter."""
        mock_courses = [
            CourseInfo(title="Intro to Programming", subject="CS", course_number="1301", crn="12345", section="A"),
            CourseInfo(title="Advanced Programming", subject="CS", course_number="1331", crn="12348", section="A"),
            CourseInfo(title="Data Structures", subject="CS", course_number="1332", crn="12346", section="B")
        ]
        mock_get_courses.return_value = mock_courses
        
        client = OscarClient()
        
        with client:
            # Search for courses containing "1301"
            filtered_courses = client.search_courses("202502", "CS", course_num="1301")
        
        assert len(filtered_courses) == 1
        assert filtered_courses[0].course_number == "1301"
        assert filtered_courses[0].title == "Intro to Programming"
    
    @patch.object(OscarClient, 'get_courses_by_subject')
    def test_search_courses_with_title_filter(self, mock_get_courses):
        """Test course search with title filter."""
        mock_courses = [
            CourseInfo(title="Intro to Programming", subject="CS", course_number="1301", crn="12345", section="A"),
            CourseInfo(title="Advanced Programming", subject="CS", course_number="1331", crn="12348", section="A"),
            CourseInfo(title="Data Structures", subject="CS", course_number="1332", crn="12346", section="B")
        ]
        mock_get_courses.return_value = mock_courses
        
        client = OscarClient()
        
        with client:
            # Search for courses with "Programming" in title
            filtered_courses = client.search_courses("202502", "CS", title="Programming")
        
        assert len(filtered_courses) == 2
        assert all("Programming" in course.title for course in filtered_courses)
    
    @patch.object(OscarClient, 'get_courses_by_subject')
    def test_search_courses_with_multiple_filters(self, mock_get_courses):
        """Test course search with multiple filters."""
        mock_courses = [
            CourseInfo(title="Intro to Programming", subject="CS", course_number="1301", crn="12345", section="A"),
            CourseInfo(title="Advanced Programming", subject="CS", course_number="1331", crn="12348", section="A"),
            CourseInfo(title="Intro to Data Structures", subject="CS", course_number="1302", crn="12346", section="B")
        ]
        mock_get_courses.return_value = mock_courses
        
        client = OscarClient()
        
        with client:
            # Search for courses with "130" in course number AND "Intro" in title
            filtered_courses = client.search_courses("202502", "CS", course_num="130", title="Intro")
        
        assert len(filtered_courses) == 2
        assert all("130" in course.course_number for course in filtered_courses)
        assert all("Intro" in course.title for course in filtered_courses)
    
    def test_get_courses_by_subject_missing_required_args(self):
        """Test get_courses_by_subject with missing required arguments."""
        client = OscarClient()
        
        with pytest.raises(ValidationError, match="term_code is required"):
            with client:
                client.get_courses_by_subject("", "CS")
        
        with pytest.raises(ValidationError, match="subject is required"):
            with client:
                client.get_courses_by_subject("202502", "")
    
    def test_search_courses_missing_required_args(self):
        """Test course search with missing required arguments."""
        client = OscarClient()
        
        with pytest.raises(ValidationError, match="term_code is required"):
            with client:
                client.search_courses("", "CS")
        
        with pytest.raises(ValidationError, match="subject is required"):
            with client:
                client.search_courses("202502", "")
    
    @patch('gtmcp.clients.oscar_client.OscarClient._make_request')
    def test_search_courses_with_filters(self, mock_request):
        """Test course search with optional filters."""
        term_response = Mock()
        term_response.content = "<html></html>"
        
        search_response = Mock()
        search_response.content = "<html></html>"
        
        mock_request.side_effect = [term_response, search_response]
        
        client = OscarClient()
        
        with client:
            client.search_courses("202502", "CS", course_num="1301", title="Programming")
        
        # Verify the search request was made with filters
        assert mock_request.call_count == 2
        search_call = mock_request.call_args_list[1]
        assert 'data' in search_call[1]


class TestOscarClientCourseDetails:
    """Test course details functionality."""
    
    @patch('gtmcp.clients.oscar_client.OscarClient._make_request')
    def test_get_course_details_success(self, mock_request):
        """Test successful course details retrieval."""
        details_html = """
        <html>
            <table class="datadisplaytable">
                <caption class="captiontext">
                    Intro to Programming - CS 1301 - 12345 - A
                </caption>
                <tr>
                    <th>Credits</th>
                    <td>3.0</td>
                </tr>
                <tr>
                    <th>Schedule Type</th>
                    <td>Lecture</td>
                </tr>
                <tr>
                    <th>Campus</th>
                    <td>Georgia Tech-Atlanta</td>
                </tr>
                <tr>
                    <th>Levels</th>
                    <td>Undergraduate</td>
                </tr>
                <tr>
                    <th>Associated Term</th>
                    <td>Spring 2025</td>
                </tr>
            </table>
            <table class="datadisplaytable">
                <caption>Registration Availability</caption>
                <tr>
                    <th>Seats</th>
                    <td>50</td>
                    <td>30</td>
                    <td>20</td>
                </tr>
                <tr>
                    <th>Waitlist</th>
                    <td>10</td>
                    <td>5</td>
                    <td>5</td>
                </tr>
            </table>
        </html>
        """
        
        mock_response = Mock()
        mock_response.content = details_html
        mock_request.return_value = mock_response
        
        client = OscarClient()
        
        with client:
            details = client.get_course_details("202502", "12345")
        
        assert details.title == "Intro to Programming"
        assert details.subject == "CS"
        assert details.course_number == "1301"
        assert details.crn == "12345"
        assert details.section == "A"
        assert details.credits == 3.0
        assert details.schedule_type == "Lecture"
        assert details.campus == "Georgia Tech-Atlanta"
        assert "Undergraduate" in details.levels
        assert details.term == "Spring 2025"
        assert details.registration.seats_capacity == 50
        assert details.registration.seats_actual == 30
        assert details.registration.seats_remaining == 20
        assert details.registration.waitlist_capacity == 10
        assert details.registration.waitlist_actual == 5
        assert details.registration.waitlist_remaining == 5
    
    def test_get_course_details_missing_required_args(self):
        """Test course details with missing required arguments."""
        client = OscarClient()
        
        with pytest.raises(ValidationError, match="term_code is required"):
            with client:
                client.get_course_details("", "12345")
        
        with pytest.raises(ValidationError, match="crn is required"):
            with client:
                client.get_course_details("202502", "")
    
    @patch('gtmcp.clients.oscar_client.OscarClient._make_request')
    def test_get_course_details_no_table(self, mock_request):
        """Test course details when main table not found."""
        mock_response = Mock()
        mock_response.content = "<html><body>No tables here</body></html>"
        mock_request.return_value = mock_response
        
        client = OscarClient()
        
        with client:
            with pytest.raises(NetworkError, match="Could not find course details table"):
                client.get_course_details("202502", "12345")


class TestOscarClientRegistrationInfo:
    """Test registration info extraction."""
    
    def test_extract_registration_info_complete(self):
        """Test extraction of complete registration information."""
        html_content = """
        <table class="datadisplaytable">
            <caption>Registration Availability</caption>
            <tr>
                <th>Seats</th>
                <td>50</td>
                <td>30</td>
                <td>20</td>
            </tr>
            <tr>
                <th>Waitlist</th>
                <td>10</td>
                <td>5</td>
                <td>5</td>
            </tr>
        </table>
        """
        
        soup = BeautifulSoup(html_content, 'html.parser')
        client = OscarClient()
        
        with client:
            reg_info = client._extract_registration_info(soup)
        
        assert reg_info.seats_capacity == 50
        assert reg_info.seats_actual == 30
        assert reg_info.seats_remaining == 20
        assert reg_info.waitlist_capacity == 10
        assert reg_info.waitlist_actual == 5
        assert reg_info.waitlist_remaining == 5
    
    def test_extract_registration_info_missing(self):
        """Test extraction when registration info is missing."""
        html_content = "<html><body>No registration info</body></html>"
        
        soup = BeautifulSoup(html_content, 'html.parser')
        client = OscarClient()
        
        with client:
            reg_info = client._extract_registration_info(soup)
        
        # Should return default values
        assert reg_info.seats_capacity == 0
        assert reg_info.seats_actual == 0
        assert reg_info.seats_remaining == 0
        assert reg_info.waitlist_capacity == 0
        assert reg_info.waitlist_actual == 0
        assert reg_info.waitlist_remaining == 0


class TestOscarClientRestrictions:
    """Test restrictions extraction."""
    
    def test_extract_restrictions_with_data(self):
        """Test extraction of restrictions when present."""
        html_content = """
        <table class="datadisplaytable">
            <caption>Restrictions</caption>
            <tr>
                <td>Must be enrolled in one of the following Levels: Undergraduate</td>
            </tr>
            <tr>
                <td>Must be enrolled in one of the following Majors: Computer Science</td>
            </tr>
        </table>
        """
        
        soup = BeautifulSoup(html_content, 'html.parser')
        client = OscarClient()
        
        with client:
            restrictions = client._extract_restrictions(soup)
        
        assert len(restrictions) >= 1
        assert any("Undergraduate" in r for r in restrictions)
    
    def test_extract_restrictions_empty(self):
        """Test extraction when no restrictions present."""
        html_content = "<html><body>No restrictions</body></html>"
        
        soup = BeautifulSoup(html_content, 'html.parser')
        client = OscarClient()
        
        with client:
            restrictions = client._extract_restrictions(soup)
        
        assert restrictions == []