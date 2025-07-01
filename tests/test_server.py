"""Tests for the MCP server implementation."""

import pytest
import asyncio
from unittest.mock import Mock, AsyncMock, patch, MagicMock
from gtmcp.server import (
    list_tools, call_tool, _get_available_semesters, 
    _get_subjects, _search_courses, _get_course_details
)
from gtmcp.models import Semester, Subject, CourseInfo, CourseDetails, RegistrationInfo
from mcp.types import ListToolsResult, CallToolResult, TextContent, Tool


class TestListTools:
    """Tests for tool listing functionality."""
    
    @pytest.mark.asyncio
    async def test_list_tools_returns_all_tools(self):
        """Test that all expected tools are listed."""
        result = await list_tools()
        
        assert isinstance(result, ListToolsResult)
        assert len(result.tools) == 4
        
        tool_names = [tool.name for tool in result.tools]
        expected_tools = [
            "get_available_semesters",
            "get_subjects", 
            "search_courses",
            "get_course_details"
        ]
        
        for expected_tool in expected_tools:
            assert expected_tool in tool_names
            
    @pytest.mark.asyncio
    async def test_tool_schemas_are_valid(self):
        """Test that all tool schemas are properly defined."""
        result = await list_tools()
        
        for tool in result.tools:
            assert tool.name
            assert tool.description
            assert tool.inputSchema
            assert "type" in tool.inputSchema
            assert tool.inputSchema["type"] == "object"
            assert "properties" in tool.inputSchema
            assert "required" in tool.inputSchema


class TestCallTool:
    """Tests for tool call functionality."""
    
    @pytest.mark.asyncio
    async def test_call_unknown_tool(self):
        """Test calling an unknown tool."""
        result = await call_tool("unknown_tool", {})
        
        assert isinstance(result, CallToolResult)
        assert result.isError is True
        assert len(result.content) == 1
        assert "Unknown tool" in result.content[0].text
        
    @pytest.mark.asyncio
    async def test_call_tool_with_exception(self):
        """Test tool call that raises an exception."""
        with patch('gtmcp.server.scraper') as mock_scraper:
            mock_scraper.get_available_semesters.side_effect = Exception("Test error")
            
            result = await call_tool("get_available_semesters", {})
            
            assert isinstance(result, CallToolResult)
            assert result.isError is True
            assert "Error: Test error" in result.content[0].text


class TestGetAvailableSemesters:
    """Tests for get_available_semesters tool."""
    
    @pytest.mark.asyncio
    async def test_get_available_semesters_success(self):
        """Test successful semester retrieval."""
        mock_semesters = [
            Semester(code="202502", name="Spring 2025", view_only=False),
            Semester(code="202402", name="Spring 2024", view_only=True)
        ]
        
        with patch('gtmcp.server.scraper') as mock_scraper:
            mock_scraper.get_available_semesters.return_value = mock_semesters
            
            result = await _get_available_semesters()
            
            assert isinstance(result, CallToolResult)
            assert result.isError is None or result.isError is False
            assert len(result.content) == 1
            
            # Parse the result content
            content = result.content[0].text
            assert "202502" in content
            assert "Spring 2025" in content
            assert "202402" in content
            assert "Spring 2024" in content
            
    @pytest.mark.asyncio
    async def test_get_available_semesters_empty_result(self):
        """Test when no semesters are found."""
        with patch('gtmcp.server.scraper') as mock_scraper:
            mock_scraper.get_available_semesters.return_value = []
            
            result = await _get_available_semesters()
            
            assert isinstance(result, CallToolResult)
            assert result.isError is None or result.isError is False
            content = result.content[0].text
            assert "semesters" in content.lower()


class TestGetSubjects:
    """Tests for get_subjects tool."""
    
    @pytest.mark.asyncio
    async def test_get_subjects_success(self):
        """Test successful subject retrieval."""
        mock_subjects = [
            Subject(code="CS", name="Computer Science"),
            Subject(code="MATH", name="Mathematics")
        ]
        
        with patch('gtmcp.server.scraper') as mock_scraper:
            mock_scraper.get_subjects.return_value = mock_subjects
            
            arguments = {"term_code": "202502"}
            result = await _get_subjects(arguments)
            
            assert isinstance(result, CallToolResult)
            assert result.isError is None or result.isError is False
            
            content = result.content[0].text
            assert "202502" in content
            assert "CS" in content
            assert "Computer Science" in content
            assert "MATH" in content
            assert "Mathematics" in content
            
    @pytest.mark.asyncio
    async def test_get_subjects_missing_term_code(self):
        """Test when term_code is missing."""
        arguments = {}
        
        # Mock the scraper
        with patch('gtmcp.server.scraper', Mock()) as mock_scraper:
            result = await call_tool("get_subjects", arguments)
            assert result.isError is True
            assert "Arguments are required" in result.content[0].text
        
    @pytest.mark.asyncio
    async def test_get_subjects_empty_term_code(self):
        """Test when term_code is empty."""
        arguments = {"term_code": ""}
        
        # Mock the scraper
        with patch('gtmcp.server.scraper', Mock()) as mock_scraper:
            result = await call_tool("get_subjects", arguments)
            assert result.isError is True
            assert "term_code is required and cannot be empty" in result.content[0].text


class TestSearchCourses:
    """Tests for search_courses tool."""
    
    @pytest.mark.asyncio
    async def test_search_courses_success(self):
        """Test successful course search."""
        mock_courses = [
            CourseInfo(
                crn="12345",
                title="Intro to Programming", 
                subject="CS",
                course_number="1301",
                section="A"
            ),
            CourseInfo(
                crn="12346",
                title="Data Structures",
                subject="CS", 
                course_number="1332",
                section="B"
            )
        ]
        
        with patch('gtmcp.server.scraper') as mock_scraper:
            mock_scraper.search_courses.return_value = mock_courses
            
            arguments = {
                "term_code": "202502",
                "subject": "CS"
            }
            result = await _search_courses(arguments)
            
            assert isinstance(result, CallToolResult)
            assert result.isError is None or result.isError is False
            
            content = result.content[0].text
            assert "202502" in content
            assert "CS" in content
            assert "12345" in content
            assert "Intro to Programming" in content
            assert "12346" in content
            assert "Data Structures" in content
            
    @pytest.mark.asyncio
    async def test_search_courses_with_filters(self):
        """Test course search with optional filters."""
        mock_courses = []
        
        with patch('gtmcp.server.scraper') as mock_scraper:
            mock_scraper.search_courses.return_value = mock_courses
            
            arguments = {
                "term_code": "202502",
                "subject": "CS",
                "course_num": "1301",
                "title": "Programming"
            }
            result = await _search_courses(arguments)
            
            # Verify scraper was called with all arguments
            mock_scraper.search_courses.assert_called_once_with(
                "202502", "CS", "1301", "Programming"
            )
            
            assert isinstance(result, CallToolResult)
            
    @pytest.mark.asyncio
    async def test_search_courses_missing_required_args(self):
        """Test when required arguments are missing."""
        # Missing term_code
        arguments = {"subject": "CS"}
        with pytest.raises(ValueError) as exc_info:
            await _search_courses(arguments)
        assert "term_code and subject are required" in str(exc_info.value)
        
        # Missing subject
        arguments = {"term_code": "202502"}
        with pytest.raises(ValueError) as exc_info:
            await _search_courses(arguments)
        assert "term_code and subject are required" in str(exc_info.value)
        
    @pytest.mark.asyncio
    async def test_search_courses_empty_results(self):
        """Test when no courses are found."""
        with patch('gtmcp.server.scraper') as mock_scraper:
            mock_scraper.search_courses.return_value = []
            
            arguments = {
                "term_code": "202502",
                "subject": "CS"
            }
            result = await _search_courses(arguments)
            
            assert isinstance(result, CallToolResult)
            content = result.content[0].text
            assert "courses" in content.lower()


class TestGetCourseDetails:
    """Tests for get_course_details tool."""
    
    @pytest.mark.asyncio
    async def test_get_course_details_success(self, sample_course_details):
        """Test successful course details retrieval."""
        with patch('gtmcp.server.scraper') as mock_scraper:
            mock_scraper.get_course_details.return_value = sample_course_details
            
            arguments = {
                "term_code": "202502",
                "crn": "12345"
            }
            result = await _get_course_details(arguments)
            
            assert isinstance(result, CallToolResult)
            assert result.isError is None or result.isError is False
            
            content = result.content[0].text
            assert "12345" in content  # CRN
            assert "Intro to Programming" in content  # Title
            assert "CS" in content  # Subject
            assert "1301" in content  # Course number
            assert "Spring 2025" in content  # Term
            assert "3.0" in content  # Credits
            assert "50" in content  # Seats capacity
            assert "30" in content  # Seats actual
            assert "20" in content  # Seats remaining
            
    @pytest.mark.asyncio
    async def test_get_course_details_missing_args(self):
        """Test when required arguments are missing."""
        # Missing term_code
        arguments = {"crn": "12345"}
        with pytest.raises(ValueError) as exc_info:
            await _get_course_details(arguments)
        assert "term_code and crn are required" in str(exc_info.value)
        
        # Missing crn
        arguments = {"term_code": "202502"}
        with pytest.raises(ValueError) as exc_info:
            await _get_course_details(arguments)
        assert "term_code and crn are required" in str(exc_info.value)
        
    @pytest.mark.asyncio
    async def test_get_course_details_empty_args(self):
        """Test when arguments are empty."""
        arguments = {"term_code": "", "crn": ""}
        
        with pytest.raises(ValueError) as exc_info:
            await _get_course_details(arguments)
        assert "term_code and crn are required" in str(exc_info.value)


class TestServerIntegration:
    """Integration tests for the server."""
    
    @pytest.mark.asyncio
    async def test_full_workflow(self):
        """Test a complete workflow through the server."""
        # Mock data
        mock_semesters = [Semester(code="202502", name="Spring 2025")]
        mock_subjects = [Subject(code="CS", name="Computer Science")]
        mock_courses = [CourseInfo(
            crn="12345", title="Test Course", subject="CS", 
            course_number="1301", section="A"
        )]
        mock_details = CourseDetails(
            crn="12345", title="Test Course", subject="CS",
            course_number="1301", section="A", term="Spring 2025",
            credits=3.0, schedule_type="Lecture", campus="Georgia Tech-Atlanta",
            levels=["Undergraduate"], 
            registration=RegistrationInfo(
                seats_capacity=50, seats_actual=30, seats_remaining=20,
                waitlist_capacity=10, waitlist_actual=5, waitlist_remaining=5
            ),
            restrictions=[], catalog_url=None
        )
        
        with patch('gtmcp.server.scraper') as mock_scraper:
            mock_scraper.get_available_semesters.return_value = mock_semesters
            mock_scraper.get_subjects.return_value = mock_subjects
            mock_scraper.search_courses.return_value = mock_courses
            mock_scraper.get_course_details.return_value = mock_details
            
            # Test each tool in sequence
            semesters_result = await call_tool("get_available_semesters", {})
            assert not semesters_result.isError
            
            subjects_result = await call_tool("get_subjects", {"term_code": "202502"})
            assert not subjects_result.isError
            
            courses_result = await call_tool("search_courses", {
                "term_code": "202502", 
                "subject": "CS"
            })
            assert not courses_result.isError
            
            details_result = await call_tool("get_course_details", {
                "term_code": "202502",
                "crn": "12345"
            })
            assert not details_result.isError