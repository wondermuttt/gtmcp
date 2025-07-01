"""Basic functionality tests for the expanded MCP server."""

import pytest
from unittest.mock import Mock, patch, AsyncMock
from datetime import datetime

from gtmcp import server_expanded
from gtmcp.models import (
    Semester, Subject, CourseInfo, CourseDetails, RegistrationInfo,
    ResearchPaper, FacultyResearchProfile, CampusLocation
)
from gtmcp.clients.base_client import NetworkError, DataParsingError


class TestServerBasicFunctionality:
    """Test basic server functionality."""
    
    def test_server_exists(self):
        """Test that server object exists and is configured."""
        assert server_expanded.server is not None
        assert hasattr(server_expanded.server, 'call_tool')
    
    @pytest.mark.asyncio
    async def test_list_tools(self):
        """Test that tools are listed correctly."""
        tools_result = await server_expanded.list_tools()
        assert hasattr(tools_result, 'tools')
        assert len(tools_result.tools) > 0
        
        # Check that key tools exist
        tool_names = [tool.name for tool in tools_result.tools]
        expected_tools = [
            'get_available_semesters',
            'search_courses', 
            'get_course_details',
            'search_research_papers'
        ]
        
        for expected_tool in expected_tools:
            assert expected_tool in tool_names
    
    @pytest.mark.asyncio
    @patch('gtmcp.server_expanded.oscar_client')
    async def test_get_available_semesters_tool(self, mock_oscar):
        """Test get_available_semesters tool call."""
        # Mock client response
        mock_semesters = [
            Semester("202502", "Spring 2025", False),
            Semester("202408", "Fall 2024", True)
        ]
        mock_oscar.get_available_semesters.return_value = mock_semesters
        
        # Call the tool
        result = await server_expanded.call_tool("get_available_semesters", {})
        
        # Verify result
        assert result is not None
        assert hasattr(result, 'content')
        assert len(result.content) > 0
        
        # Check that semester data is in response
        response_text = result.content[0].text
        assert "Spring 2025" in response_text
        assert "Fall 2024" in response_text
    
    @pytest.mark.asyncio
    @patch('gtmcp.server_expanded.oscar_client')
    async def test_search_courses_tool(self, mock_oscar):
        """Test search_courses tool call."""
        # Mock client response
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
            )
        ]
        mock_oscar.search_courses.return_value = mock_courses
        
        # Call the tool
        result = await server_expanded.call_tool("search_courses", {
            "term_code": "202502",
            "subject": "CS"
        })
        
        # Verify result
        assert result is not None
        response_text = result.content[0].text
        assert "Intro to Programming" in response_text
        assert "Data Structures" in response_text
        assert "CS 1301" in response_text
    
    @pytest.mark.asyncio
    @patch('gtmcp.server_expanded.smartech_client')
    async def test_search_research_papers_tool(self, mock_smartech):
        """Test search_research_papers tool call."""
        # Mock client response
        mock_papers = [
            ResearchPaper(
                oai_identifier="oai:test:1",
                title="Machine Learning Research",
                authors=["Dr. Smith", "Dr. Johnson"],
                abstract="Advanced ML techniques",
                publication_date=datetime(2023, 1, 1),
                subject_areas=["Computer Science"],
                citation_count=25,
                related_courses=["CS 7641"]
            )
        ]
        mock_smartech.search_records.return_value = {
            'papers': mock_papers,
            'count': 1
        }
        
        # Call the tool
        result = await server_expanded.call_tool("search_research_papers", {
            "keywords": ["machine learning"]
        })
        
        # Verify result
        assert result is not None
        response_text = result.content[0].text
        assert "Machine Learning Research" in response_text
        assert "Dr. Smith" in response_text
    
    @pytest.mark.asyncio
    async def test_invalid_tool_call(self):
        """Test error handling for invalid tool calls."""
        with pytest.raises(Exception):  # Should raise ToolError
            await server_expanded.call_tool("nonexistent_tool", {})
    
    @pytest.mark.asyncio
    async def test_tool_call_missing_arguments(self):
        """Test error handling for missing required arguments."""
        with pytest.raises(Exception):  # Should raise ToolError
            await server_expanded.call_tool("search_courses", {})  # Missing required args


class TestServerHealthAndConnectivity:
    """Test server health and connectivity features."""
    
    @pytest.mark.asyncio
    @patch('gtmcp.server_expanded.oscar_client')
    @patch('gtmcp.server_expanded.smartech_client')
    @patch('gtmcp.server_expanded.places_client')
    async def test_get_system_health_status(self, mock_places, mock_smartech, mock_oscar):
        """Test system health status tool."""
        # Mock health responses
        mock_oscar.get_health_status.return_value = {
            'service': 'OSCAR',
            'status': 'healthy',
            'timestamp': datetime.now().isoformat()
        }
        mock_smartech.get_health_status.return_value = {
            'service': 'SMARTech',
            'status': 'healthy', 
            'timestamp': datetime.now().isoformat()
        }
        mock_places.get_health_status.return_value = {
            'service': 'Places',
            'status': 'healthy',
            'timestamp': datetime.now().isoformat()
        }
        
        # Call the tool
        result = await server_expanded.call_tool("get_system_health_status", {})
        
        # Verify result
        assert result is not None
        response_text = result.content[0].text
        assert "OSCAR" in response_text
        assert "SMARTech" in response_text
        assert "Places" in response_text
        assert "healthy" in response_text
    
    @pytest.mark.asyncio
    @patch('gtmcp.server_expanded.oscar_client')
    async def test_error_handling_in_tool(self, mock_oscar):
        """Test error handling within tool calls."""
        # Mock client to raise an exception
        mock_oscar.get_available_semesters.side_effect = NetworkError("Connection failed")
        
        # Call the tool - should handle the error gracefully
        with pytest.raises(Exception):  # Should raise ToolError
            await server_expanded.call_tool("get_available_semesters", {})


class TestServerDataValidation:
    """Test server data validation and processing."""
    
    @pytest.mark.asyncio
    @patch('gtmcp.server_expanded.oscar_client')
    async def test_data_serialization(self, mock_oscar):
        """Test that complex data structures are properly serialized."""
        # Mock complex course details
        mock_course = CourseDetails(
            title="Advanced Data Structures",
            subject="CS",
            course_number="7641",
            crn="12345",
            section="A",
            credits=3.0,
            schedule_type="Lecture",
            campus="Georgia Tech-Atlanta",
            levels=["Graduate"],
            term="Spring 2025",
            registration=RegistrationInfo(
                seats_capacity=50,
                seats_actual=45,
                seats_remaining=5,
                waitlist_capacity=10,
                waitlist_actual=2,
                waitlist_remaining=8
            ),
            prerequisites=["CS 3600"],
            restrictions=["Graduate Standing"],
            attributes=["Honors"],
            meeting_times=["MWF 10:00-11:00"],
            instructors=["Dr. Smith"]
        )
        mock_oscar.get_course_details.return_value = mock_course
        
        # Call the tool
        result = await server_expanded.call_tool("get_course_details", {
            "term_code": "202502",
            "crn": "12345"
        })
        
        # Verify result contains expected data
        assert result is not None
        response_text = result.content[0].text
        assert "Advanced Data Structures" in response_text
        assert "CS 7641" in response_text
        assert "50" in response_text  # Seats capacity
        assert "Dr. Smith" in response_text
    
    @pytest.mark.asyncio
    async def test_input_validation(self):
        """Test input validation for tool calls."""
        # Test empty tool name
        with pytest.raises(Exception):
            await server_expanded.call_tool("", {})
        
        # Test None tool name
        with pytest.raises(Exception):
            await server_expanded.call_tool(None, {})