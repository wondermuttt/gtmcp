"""Comprehensive tests for the expanded MCP server functionality."""

import pytest
import asyncio
from unittest.mock import Mock, patch, AsyncMock, MagicMock
from datetime import datetime

from gtmcp.server_expanded import GTMCPServerExpanded
from gtmcp.models import (
    Semester, Subject, CourseInfo, CourseDetails, RegistrationInfo,
    ResearchPaper, FacultyResearchProfile, CampusLocation, RouteOptimization
)
from gtmcp.clients.base_client import NetworkError, DataParsingError, ValidationError


class TestExpandedServerListTools:
    """Test tool listing and schema validation."""
    
    @pytest.fixture
    def server(self):
        """Create server instance for testing."""
        return GTMCPServerExpanded()
    
    def test_list_tools_count(self, server):
        """Test that all 17 tools are listed."""
        tools = server.list_tools()
        assert len(tools) == 17
    
    def test_list_tools_categories(self, server):
        """Test that tools are properly categorized."""
        tools = server.list_tools()
        tool_names = [tool['name'] for tool in tools]
        
        # Course/Academic tools
        assert 'get_available_semesters' in tool_names
        assert 'get_subjects' in tool_names
        assert 'search_courses' in tool_names
        assert 'get_course_details' in tool_names
        
        # Research/Knowledge tools
        assert 'search_research_papers' in tool_names
        assert 'get_research_paper_details' in tool_names
        assert 'find_faculty_research' in tool_names
        assert 'analyze_research_trends' in tool_names
        
        # Campus/Location tools
        assert 'search_campus_locations' in tool_names
        assert 'get_building_details' in tool_names
        assert 'find_accessible_buildings' in tool_names
        assert 'optimize_campus_route' in tool_names
        
        # Cross-system integration tools
        assert 'find_courses_for_research' in tool_names
        assert 'get_research_collaboration_suggestions' in tool_names
        assert 'get_comprehensive_course_context' in tool_names
        assert 'get_system_health_status' in tool_names
        assert 'search_integrated_gt_resources' in tool_names
    
    def test_tool_schemas_valid(self, server):
        """Test that all tools have valid schemas."""
        tools = server.list_tools()
        
        for tool in tools:
            assert 'name' in tool
            assert 'description' in tool
            assert 'inputSchema' in tool
            assert 'type' in tool['inputSchema']
            assert tool['inputSchema']['type'] == 'object'


class TestExpandedServerCallTool:
    """Test tool call functionality and error handling."""
    
    @pytest.fixture
    def server(self):
        """Create server instance for testing."""
        return GTMCPServerExpanded()
    
    @pytest.mark.asyncio
    async def test_call_nonexistent_tool(self, server):
        """Test calling a tool that doesn't exist."""
        with pytest.raises(ValueError, match="Unknown tool"):
            await server.call_tool("nonexistent_tool", {})
    
    @pytest.mark.asyncio
    async def test_call_tool_with_invalid_args(self, server):
        """Test calling a tool with invalid arguments."""
        with pytest.raises(ValueError, match="Missing required argument"):
            await server.call_tool("get_subjects", {})


class TestCourseAcademicTools:
    """Test all course/academic tools."""
    
    @pytest.fixture
    def server(self):
        """Create server instance for testing."""
        return GTMCPServerExpanded()
    
    @pytest.fixture
    def mock_semesters(self):
        """Mock semester data."""
        return [
            Semester(code="202502", name="Spring 2025", view_only=False),
            Semester(code="202408", name="Fall 2024", view_only=False)
        ]
    
    @pytest.fixture
    def mock_subjects(self):
        """Mock subject data."""
        return [
            Subject(code="CS", name="Computer Science"),
            Subject(code="MATH", name="Mathematics")
        ]
    
    @pytest.fixture
    def mock_courses(self):
        """Mock course data."""
        return [
            CourseInfo(
                title="Machine Learning",
                subject="CS",
                course_number="7641",
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
    
    @pytest.fixture
    def mock_course_details(self):
        """Mock course details data."""
        return CourseDetails(
            title="Machine Learning",
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
                seats_actual=30,
                seats_remaining=20,
                waitlist_capacity=10,
                waitlist_actual=5,
                waitlist_remaining=5
            ),
            prerequisites=[],
            restrictions=[],
            attributes=[],
            meeting_times=[],
            instructors=[]
        )
    
    @pytest.mark.asyncio
    @patch('gtmcp.server_expanded.GTMCPServerExpanded.oscar_client')
    async def test_get_available_semesters(self, mock_oscar, server, mock_semesters):
        """Test getting available semesters."""
        mock_oscar.get_available_semesters.return_value = mock_semesters
        
        result = await server.call_tool("get_available_semesters", {})
        
        assert len(result) == 2
        assert result[0]['code'] == "202502"
        assert result[0]['name'] == "Spring 2025"
        assert result[0]['view_only'] is False
    
    @pytest.mark.asyncio
    @patch('gtmcp.server_expanded.GTMCPServerExpanded.oscar_client')
    async def test_get_subjects(self, mock_oscar, server, mock_subjects):
        """Test getting subjects for a term."""
        mock_oscar.get_subjects.return_value = mock_subjects
        
        result = await server.call_tool("get_subjects", {"term_code": "202502"})
        
        assert len(result) == 2
        assert result[0]['code'] == "CS"
        assert result[0]['name'] == "Computer Science"
        mock_oscar.get_subjects.assert_called_once_with("202502")
    
    @pytest.mark.asyncio
    @patch('gtmcp.server_expanded.GTMCPServerExpanded.oscar_client')
    async def test_search_courses(self, mock_oscar, server, mock_courses):
        """Test searching courses."""
        mock_oscar.search_courses.return_value = mock_courses
        
        result = await server.call_tool("search_courses", {
            "term_code": "202502",
            "subject": "CS"
        })
        
        assert len(result) == 2
        assert result[0]['title'] == "Machine Learning"
        assert result[0]['crn'] == "12345"
        mock_oscar.search_courses.assert_called_once_with("202502", "CS", None, None)
    
    @pytest.mark.asyncio
    @patch('gtmcp.server_expanded.GTMCPServerExpanded.oscar_client')
    async def test_get_course_details(self, mock_oscar, server, mock_course_details):
        """Test getting course details."""
        mock_oscar.get_course_details.return_value = mock_course_details
        
        result = await server.call_tool("get_course_details", {
            "term_code": "202502",
            "crn": "12345"
        })
        
        assert result['title'] == "Machine Learning"
        assert result['crn'] == "12345"
        assert result['credits'] == 3.0
        assert result['registration']['seats_remaining'] == 20
        mock_oscar.get_course_details.assert_called_once_with("202502", "12345")


class TestResearchKnowledgeTools:
    """Test all research/knowledge tools."""
    
    @pytest.fixture
    def server(self):
        """Create server instance for testing."""
        return GTMCPServerExpanded()
    
    @pytest.fixture
    def mock_research_papers(self):
        """Mock research paper data."""
        return [
            ResearchPaper(
                oai_identifier="oai:repo:1",
                title="Advanced Machine Learning Applications",
                authors=["Dr. Smith, John", "Dr. Johnson, Alice"],
                abstract="This paper explores advanced ML applications in robotics.",
                publication_date=datetime(2023, 6, 15),
                subject_areas=["Computer Science", "Machine Learning", "Robotics"],
                citation_count=25,
                related_courses=["CS 7641", "CS 7642"]
            ),
            ResearchPaper(
                oai_identifier="oai:repo:2", 
                title="Deep Learning for Computer Vision",
                authors=["Dr. Brown, Bob", "Dr. Davis, Carol"],
                abstract="Deep learning techniques for advanced computer vision tasks.",
                publication_date=datetime(2023, 8, 20),
                subject_areas=["Computer Science", "Deep Learning", "Computer Vision"],
                citation_count=40,
                related_courses=["CS 7643", "CS 7644"]
            )
        ]
    
    @pytest.fixture
    def mock_faculty_profiles(self):
        """Mock faculty profile data."""
        return [
            FacultyResearchProfile(
                name="Dr. Smith, John",
                research_interests=["Machine Learning", "Robotics", "AI"],
                recent_publications=["Advanced Machine Learning Applications"],
                collaboration_score=85,
                total_publications=45,
                citation_count=1250,
                active_projects=["NSF Grant ML-2023", "DARPA Robotics Initiative"]
            )
        ]
    
    @pytest.mark.asyncio
    @patch('gtmcp.server_expanded.GTMCPServerExpanded.smartech_client')
    async def test_search_research_papers(self, mock_smartech, server, mock_research_papers):
        """Test searching research papers."""
        mock_smartech.search_records.return_value = {
            'papers': mock_research_papers,
            'count': 2
        }
        
        result = await server.call_tool("search_research_papers", {
            "keywords": ["machine learning"]
        })
        
        assert len(result['papers']) == 2
        assert result['count'] == 2
        assert result['papers'][0]['title'] == "Advanced Machine Learning Applications"
        assert "Machine Learning" in result['papers'][0]['subject_areas']
        mock_smartech.search_records.assert_called_once()
    
    @pytest.mark.asyncio
    @patch('gtmcp.server_expanded.GTMCPServerExpanded.smartech_client')
    async def test_get_research_paper_details(self, mock_smartech, server, mock_research_papers):
        """Test getting research paper details."""
        paper = mock_research_papers[0]
        mock_smartech.get_record_by_identifier.return_value = paper
        
        result = await server.call_tool("get_research_paper_details", {
            "paper_id": "oai:repo:1"
        })
        
        assert result['title'] == "Advanced Machine Learning Applications"
        assert result['citation_count'] == 25
        assert len(result['authors']) == 2
        mock_smartech.get_record_by_identifier.assert_called_once_with("oai:repo:1")
    
    @pytest.mark.asyncio
    @patch('gtmcp.server_expanded.GTMCPServerExpanded.smartech_client')
    async def test_find_faculty_research(self, mock_smartech, server, mock_faculty_profiles):
        """Test finding faculty research."""
        mock_smartech.find_faculty_research.return_value = mock_faculty_profiles
        
        result = await server.call_tool("find_faculty_research", {
            "research_area": "machine learning"
        })
        
        assert len(result) == 1
        assert result[0]['name'] == "Dr. Smith, John"
        assert "Machine Learning" in result[0]['research_interests']
        assert result[0]['collaboration_score'] == 85
        mock_smartech.find_faculty_research.assert_called_once_with("machine learning")
    
    @pytest.mark.asyncio
    @patch('gtmcp.server_expanded.GTMCPServerExpanded.smartech_client')
    async def test_analyze_research_trends(self, mock_smartech, server):
        """Test analyzing research trends."""
        mock_trends = {
            'trends_by_year': {
                '2023': 15,
                '2022': 12,
                '2021': 8
            },
            'total_papers': 35,
            'trend_direction': 'increasing',
            'peak_year': '2023',
            'average_per_year': 11.7
        }
        mock_smartech.analyze_research_trends.return_value = mock_trends
        
        result = await server.call_tool("analyze_research_trends", {
            "keywords": ["artificial intelligence"],
            "years": 3
        })
        
        assert result['total_papers'] == 35
        assert result['trend_direction'] == 'increasing'
        assert result['peak_year'] == '2023'
        mock_smartech.analyze_research_trends.assert_called_once_with(["artificial intelligence"], 3)


class TestCampusLocationTools:
    """Test all campus/location tools."""
    
    @pytest.fixture
    def server(self):
        """Create server instance for testing."""
        return GTMCPServerExpanded()
    
    @pytest.fixture
    def mock_locations(self):
        """Mock campus location data."""
        return [
            CampusLocation(
                name="Klaus Advanced Computing Building",
                building_code="KLAUS",
                address="266 Ferst Dr NW, Atlanta, GA 30332",
                latitude=33.777,
                longitude=-84.396,
                wheelchair_accessible=True,
                elevator_access=True,
                accessible_parking=True,
                accessible_restrooms=True,
                braille_signage=True,
                amenities=["Computer Labs", "Study Rooms", "Food Court"],
                departments=["Computer Science", "Computational Science and Engineering"],
                hours={"monday": "7:00 AM - 11:00 PM", "weekend": "9:00 AM - 9:00 PM"}
            )
        ]
    
    @pytest.fixture
    def mock_route(self):
        """Mock route optimization data."""
        return RouteOptimization(
            waypoints=["KLAUS", "STUC", "LIBW"],
            total_distance_miles=0.8,
            estimated_time_minutes=12,
            accessibility_rating="fully_accessible",
            step_by_step_directions=[
                "Start at Klaus Advanced Computing Building",
                "Walk east on Ferst Drive for 0.3 miles",
                "Arrive at Student Center"
            ]
        )
    
    @pytest.mark.asyncio
    @patch('gtmcp.server_expanded.GTMCPServerExpanded.places_client')
    async def test_search_campus_locations(self, mock_places, server, mock_locations):
        """Test searching campus locations."""
        mock_places.search_buildings.return_value = mock_locations
        
        result = await server.call_tool("search_campus_locations", {
            "query": "Klaus"
        })
        
        assert len(result) == 1
        assert result[0]['name'] == "Klaus Advanced Computing Building"
        assert result[0]['building_code'] == "KLAUS"
        assert result[0]['wheelchair_accessible'] is True
        mock_places.search_buildings.assert_called_once_with("Klaus")
    
    @pytest.mark.asyncio
    @patch('gtmcp.server_expanded.GTMCPServerExpanded.places_client')
    async def test_get_building_details(self, mock_places, server, mock_locations):
        """Test getting building details."""
        building = mock_locations[0]
        mock_places.get_building_details.return_value = building
        
        result = await server.call_tool("get_building_details", {
            "building_id": "KLAUS"
        })
        
        assert result['name'] == "Klaus Advanced Computing Building"
        assert result['building_code'] == "KLAUS"
        assert "Computer Labs" in result['amenities']
        assert "Computer Science" in result['departments']
        mock_places.get_building_details.assert_called_once_with("KLAUS")
    
    @pytest.mark.asyncio
    @patch('gtmcp.server_expanded.GTMCPServerExpanded.places_client')
    async def test_find_accessible_buildings(self, mock_places, server, mock_locations):
        """Test finding accessible buildings."""
        mock_places.find_accessible_buildings.return_value = mock_locations
        
        result = await server.call_tool("find_accessible_buildings", {
            "wheelchair_access": True
        })
        
        assert len(result) == 1
        assert result[0]['wheelchair_accessible'] is True
        assert result[0]['elevator_access'] is True
        mock_places.find_accessible_buildings.assert_called_once()
    
    @pytest.mark.asyncio
    @patch('gtmcp.server_expanded.GTMCPServerExpanded.places_client')
    async def test_optimize_campus_route(self, mock_places, server, mock_route):
        """Test optimizing campus route."""
        mock_places.optimize_route.return_value = mock_route
        
        result = await server.call_tool("optimize_campus_route", {
            "locations": ["KLAUS", "STUC", "LIBW"]
        })
        
        assert result['waypoints'] == ["KLAUS", "STUC", "LIBW"]
        assert result['total_distance_miles'] == 0.8
        assert result['accessibility_rating'] == "fully_accessible"
        mock_places.optimize_route.assert_called_once_with(["KLAUS", "STUC", "LIBW"], None)


class TestCrossSystemIntegrationTools:
    """Test all cross-system integration tools."""
    
    @pytest.fixture
    def server(self):
        """Create server instance for testing."""
        return GTMCPServerExpanded()
    
    @pytest.mark.asyncio
    @patch('gtmcp.server_expanded.GTMCPServerExpanded.smartech_client')
    @patch('gtmcp.server_expanded.GTMCPServerExpanded.oscar_client')
    async def test_find_courses_for_research(self, mock_oscar, mock_smartech, server):
        """Test finding courses for research topic."""
        # Mock research papers
        mock_papers = [
            ResearchPaper(
                oai_identifier="oai:repo:1",
                title="Machine Learning Applications",
                authors=["Dr. Smith"],
                abstract="ML applications in robotics",
                publication_date=datetime.now(),
                subject_areas=["Computer Science", "Machine Learning"],
                citation_count=25,
                related_courses=["CS 7641"]
            )
        ]
        mock_smartech.search_records.return_value = {'papers': mock_papers}
        
        # Mock courses
        mock_courses = [
            CourseInfo(
                title="Machine Learning", 
                subject="CS",
                course_number="7641",
                crn="12345",
                section="A"
            )
        ]
        mock_oscar.search_courses.return_value = mock_courses
        
        result = await server.call_tool("find_courses_for_research", {
            "research_topic": "machine learning",
            "term_code": "202502"
        })
        
        assert 'related_courses' in result
        assert 'research_papers' in result
        assert 'correlation_strength' in result
        assert len(result['related_courses']) > 0
        assert len(result['research_papers']) > 0
    
    @pytest.mark.asyncio
    @patch('gtmcp.server_expanded.GTMCPServerExpanded.smartech_client')
    async def test_get_research_collaboration_suggestions(self, mock_smartech, server):
        """Test getting research collaboration suggestions."""
        mock_profiles = [
            FacultyResearchProfile(
                name="Dr. Smith, John",
                research_interests=["Machine Learning", "AI"],
                recent_publications=["ML Paper 1"],
                collaboration_score=90,
                total_publications=25,
                citation_count=500,
                active_projects=["NSF Grant"]
            )
        ]
        mock_smartech.find_faculty_research.return_value = mock_profiles
        
        result = await server.call_tool("get_research_collaboration_suggestions", {
            "research_interests": ["artificial intelligence", "robotics"]
        })
        
        assert 'faculty_matches' in result
        assert 'collaboration_opportunities' in result
        assert len(result['faculty_matches']) > 0
    
    @pytest.mark.asyncio
    @patch('gtmcp.server_expanded.GTMCPServerExpanded.oscar_client')
    @patch('gtmcp.server_expanded.GTMCPServerExpanded.smartech_client')
    @patch('gtmcp.server_expanded.GTMCPServerExpanded.places_client')
    async def test_get_comprehensive_course_context(self, mock_places, mock_smartech, mock_oscar, server):
        """Test getting comprehensive course context."""
        # Mock course details
        mock_course = CourseDetails(
            title="Machine Learning",
            subject="CS",
            course_number="7641",
            crn="12345",
            section="A",
            credits=3.0,
            schedule_type="Lecture",
            campus="Georgia Tech-Atlanta",
            levels=["Graduate"],
            term="Spring 2025",
            registration=RegistrationInfo(50, 30, 20, 10, 5, 5),
            prerequisites=[],
            restrictions=[],
            attributes=[],
            meeting_times=[],
            instructors=[]
        )
        mock_oscar.get_course_details.return_value = mock_course
        
        # Mock research papers
        mock_papers = [
            ResearchPaper(
                oai_identifier="oai:repo:1",
                title="ML Research",
                authors=["Dr. Smith"],
                abstract="ML research",
                publication_date=datetime.now(),
                subject_areas=["ML"],
                citation_count=25,
                related_courses=[]
            )
        ]
        mock_smartech.search_records.return_value = {'papers': mock_papers}
        
        # Mock building details
        mock_building = CampusLocation(
            name="Klaus Building",
            building_code="KLAUS",
            address="266 Ferst Dr",
            latitude=33.777,
            longitude=-84.396,
            wheelchair_accessible=True,
            elevator_access=True,
            accessible_parking=True,
            accessible_restrooms=True,
            braille_signage=True,
            amenities=["Labs"],
            departments=["CS"],
            hours={}
        )
        mock_places.get_building_details.return_value = mock_building
        
        result = await server.call_tool("get_comprehensive_course_context", {
            "term_code": "202502",
            "crn": "12345"
        })
        
        assert 'course_details' in result
        assert 'related_research' in result
        assert 'building_info' in result
        assert 'comprehensive_context' in result
    
    @pytest.mark.asyncio
    @patch('gtmcp.server_expanded.GTMCPServerExpanded.oscar_client')
    @patch('gtmcp.server_expanded.GTMCPServerExpanded.smartech_client')
    @patch('gtmcp.server_expanded.GTMCPServerExpanded.places_client')
    async def test_get_system_health_status(self, mock_places, mock_smartech, mock_oscar, server):
        """Test getting system health status."""
        # Mock health status for all systems
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
        
        result = await server.call_tool("get_system_health_status", {})
        
        assert 'oscar_health' in result
        assert 'smartech_health' in result
        assert 'places_health' in result
        assert 'overall_status' in result
        assert result['overall_status'] == 'healthy'


class TestExpandedServerIntegration:
    """Integration tests across systems."""
    
    @pytest.fixture
    def server(self):
        """Create server instance for testing."""
        return GTMCPServerExpanded()
    
    @pytest.mark.asyncio
    async def test_server_initialization(self, server):
        """Test server initializes all clients properly."""
        assert hasattr(server, 'oscar_client')
        assert hasattr(server, 'smartech_client')
        assert hasattr(server, 'places_client')
    
    @pytest.mark.asyncio
    async def test_concurrent_tool_calls(self, server):
        """Test concurrent execution of multiple tools."""
        with patch.object(server.oscar_client, 'get_available_semesters') as mock_oscar, \
             patch.object(server.smartech_client, 'search_records') as mock_smartech:
            
            mock_oscar.return_value = [Semester("202502", "Spring 2025", False)]
            mock_smartech.return_value = {'papers': [], 'count': 0}
            
            # Run multiple tools concurrently
            tasks = [
                server.call_tool("get_available_semesters", {}),
                server.call_tool("search_research_papers", {"keywords": ["test"]})
            ]
            
            results = await asyncio.gather(*tasks)
            
            assert len(results) == 2
            assert len(results[0]) == 1  # Semesters
            assert results[1]['count'] == 0  # Research papers


class TestExpandedServerEdgeCases:
    """Test edge cases and boundary conditions."""
    
    @pytest.fixture
    def server(self):
        """Create server instance for testing."""
        return GTMCPServerExpanded()
    
    @pytest.mark.asyncio
    @patch('gtmcp.server_expanded.GTMCPServerExpanded.oscar_client')
    async def test_network_error_handling(self, mock_oscar, server):
        """Test handling of network errors."""
        mock_oscar.get_available_semesters.side_effect = NetworkError("Network unavailable")
        
        with pytest.raises(Exception):
            await server.call_tool("get_available_semesters", {})
    
    @pytest.mark.asyncio
    @patch('gtmcp.server_expanded.GTMCPServerExpanded.smartech_client')
    async def test_large_result_handling(self, mock_smartech, server):
        """Test handling of large result sets."""
        # Create large number of mock papers
        large_paper_set = []
        for i in range(200):
            paper = ResearchPaper(
                oai_identifier=f"oai:repo:{i}",
                title=f"Research Paper {i}",
                authors=[f"Author {i}"],
                abstract=f"Abstract for paper {i}",
                publication_date=datetime.now(),
                subject_areas=["Computer Science"],
                citation_count=i,
                related_courses=[]
            )
            large_paper_set.append(paper)
        
        mock_smartech.search_records.return_value = {
            'papers': large_paper_set,
            'count': 200
        }
        
        result = await server.call_tool("search_research_papers", {
            "keywords": ["computer science"]
        })
        
        # Should handle large result set without issues
        assert result['count'] == 200
        assert len(result['papers']) == 200
    
    @pytest.mark.asyncio
    @patch('gtmcp.server_expanded.GTMCPServerExpanded.oscar_client')
    async def test_empty_results_handling(self, mock_oscar, server):
        """Test handling of empty results."""
        mock_oscar.search_courses.return_value = []
        
        result = await server.call_tool("search_courses", {
            "term_code": "202502",
            "subject": "NONEXISTENT"
        })
        
        assert result == []
    
    @pytest.mark.asyncio
    async def test_special_characters_in_input(self, server):
        """Test handling of special characters in input."""
        with patch.object(server.smartech_client, 'search_records') as mock_smartech:
            mock_smartech.return_value = {'papers': [], 'count': 0}
            
            # Test with special characters
            result = await server.call_tool("search_research_papers", {
                "keywords": ["test & special <chars> \"quotes\""]
            })
            
            assert result['count'] == 0
            # Should not raise exception with special characters