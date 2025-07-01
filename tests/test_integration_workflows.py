"""Integration tests for cross-system workflows and end-to-end functionality."""

import pytest
import asyncio
import time
from unittest.mock import Mock, patch, AsyncMock
from datetime import datetime, timedelta

from gtmcp import server_expanded
from gtmcp.models import (
    Semester, Subject, CourseInfo, CourseDetails, RegistrationInfo,
    ResearchPaper, FacultyResearchProfile, CampusLocation, RouteOptimization
)
from gtmcp.clients.base_client import NetworkError, DataParsingError


class TestCrossSystemWorkflows:
    """Test cross-system workflows and real-world usage scenarios."""
    
    @pytest.fixture
    def server(self):
        """Get server instance for testing."""
        return server_expanded.server
    
    @pytest.fixture
    def mock_ai_courses(self):
        """Mock AI-related courses."""
        return [
            CourseInfo(
                title="Machine Learning",
                subject="CS",
                course_number="7641",
                crn="12345",
                section="A"
            ),
            CourseInfo(
                title="Computer Vision",
                subject="CS", 
                course_number="7643",
                crn="12346",
                section="B"
            ),
            CourseInfo(
                title="Artificial Intelligence",
                subject="CS",
                course_number="3600",
                crn="12347",
                section="C"
            )
        ]
    
    @pytest.fixture
    def mock_ai_research(self):
        """Mock AI-related research papers."""
        return [
            ResearchPaper(
                oai_identifier="oai:repo:ai1",
                title="Advanced Machine Learning for Robotics Applications",
                authors=["Dr. Smith, John", "Dr. Johnson, Alice"],
                abstract="This paper explores cutting-edge ML techniques for autonomous robotics systems.",
                publication_date=datetime(2023, 6, 15),
                subject_areas=["Computer Science", "Machine Learning", "Robotics", "AI"],
                citation_count=45,
                related_courses=["CS 7641", "CS 7642"]
            ),
            ResearchPaper(
                oai_identifier="oai:repo:ai2",
                title="Deep Learning in Computer Vision: Recent Advances",
                authors=["Dr. Brown, Bob", "Dr. Davis, Carol"],
                abstract="A comprehensive survey of recent advances in deep learning for computer vision applications.",
                publication_date=datetime(2023, 8, 20),
                subject_areas=["Computer Science", "Deep Learning", "Computer Vision"],
                citation_count=78,
                related_courses=["CS 7643", "CS 7644"]
            ),
            ResearchPaper(
                oai_identifier="oai:repo:ai3",
                title="Ethical AI: Frameworks and Implementation",
                authors=["Dr. White, Sarah", "Dr. Black, Michael"],
                abstract="Exploring ethical frameworks for AI development and deployment in real-world scenarios.",
                publication_date=datetime(2023, 10, 5),
                subject_areas=["Computer Science", "AI Ethics", "Philosophy"],
                citation_count=32,
                related_courses=["CS 3600", "PHIL 3050"]
            )
        ]
    
    @pytest.fixture
    def mock_accessible_buildings(self):
        """Mock accessible buildings with CS facilities."""
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
                amenities=["Computer Labs", "Study Rooms", "Food Court", "WiFi"],
                departments=["Computer Science", "Computational Science and Engineering"],
                hours={"monday": "7:00 AM - 11:00 PM", "weekend": "9:00 AM - 9:00 PM"}
            ),
            CampusLocation(
                name="College of Computing Building",
                building_code="COC",
                address="801 Atlantic Dr NW, Atlanta, GA 30332",
                latitude=33.777,
                longitude=-84.397,
                wheelchair_accessible=True,
                elevator_access=True,
                accessible_parking=True,
                accessible_restrooms=True,
                braille_signage=True,
                amenities=["Lecture Halls", "Research Labs", "Student Lounge"],
                departments=["Computer Science", "Interactive Computing"],
                hours={"monday": "6:00 AM - 12:00 AM", "weekend": "8:00 AM - 10:00 PM"}
            )
        ]
    
    @pytest.fixture
    def mock_faculty_profiles(self):
        """Mock faculty research profiles."""
        return [
            FacultyResearchProfile(
                name="Dr. Smith, John",
                research_interests=["Machine Learning", "Robotics", "AI", "Computer Vision"],
                recent_publications=[
                    "Advanced Machine Learning for Robotics Applications",
                    "Neural Networks in Autonomous Systems"
                ],
                collaboration_score=92,
                total_publications=78,
                citation_count=2150,
                active_projects=[
                    "NSF Grant: ML-2023-Advanced Robotics",
                    "DARPA: Autonomous Systems Initiative",
                    "Industry Collaboration: Tesla AI Research"
                ]
            ),
            FacultyResearchProfile(
                name="Dr. Brown, Bob",
                research_interests=["Deep Learning", "Computer Vision", "Image Processing"],
                recent_publications=[
                    "Deep Learning in Computer Vision: Recent Advances",
                    "Convolutional Neural Networks for Medical Imaging"
                ],
                collaboration_score=89,
                total_publications=65,
                citation_count=1890,
                active_projects=[
                    "NIH Grant: Medical Image Analysis",
                    "Google Research: Computer Vision Applications"
                ]
            )
        ]
    
    @pytest.mark.asyncio
    @patch('gtmcp.server_expanded.oscar_client')
    @patch('gtmcp.server_expanded.smartech_client')
    @patch('gtmcp.server_expanded.places_client')
    async def test_ai_research_course_discovery_workflow(self, mock_places, mock_smartech, mock_oscar, server, 
                                                        mock_ai_courses, mock_ai_research, mock_accessible_buildings):
        """Test complete workflow: Find AI courses related to research interests."""
        # Mock research paper search
        mock_smartech.search_records.return_value = {
            'papers': mock_ai_research,
            'count': 3
        }
        
        # Mock course methods
        mock_oscar.get_courses_by_subject.return_value = mock_ai_courses
        mock_oscar.search_courses.return_value = mock_ai_courses
        
        # Mock building search for accessibility
        mock_places.search_buildings.return_value = mock_accessible_buildings
        
        # Step 1: Find courses for AI research
        research_courses = await server.call_tool("find_courses_for_research", {
            "research_topic": "artificial intelligence",
            "term_code": "202502"
        })
        
        # Step 2: Find accessible buildings
        accessible_buildings = await server.call_tool("find_accessible_buildings", {
            "wheelchair_access": True
        })
        
        # Step 3: Search campus locations
        campus_locations = await server.call_tool("search_campus_locations", {
            "query": "computing"
        })
        
        # Validate workflow results
        assert 'related_courses' in research_courses
        assert 'research_papers' in research_courses
        assert len(research_courses['related_courses']) >= 1
        assert len(research_courses['research_papers']) >= 1
        
        assert len(accessible_buildings) >= 1
        assert all(building['wheelchair_accessible'] for building in accessible_buildings)
        
        assert len(campus_locations) >= 1
        assert any("Klaus" in location['name'] for location in campus_locations)
    
    @pytest.mark.asyncio
    @patch('gtmcp.server_expanded.oscar_client')
    @patch('gtmcp.server_expanded.places_client')
    async def test_accessibility_aware_course_planning(self, mock_places, mock_oscar, server,
                                                      mock_ai_courses, mock_accessible_buildings):
        """Test finding courses with accessibility considerations."""
        # Mock course methods
        mock_oscar.get_courses_by_subject.return_value = mock_ai_courses
        mock_oscar.search_courses.return_value = mock_ai_courses
        
        # Mock accessible building details
        mock_places.get_building_details.return_value = mock_accessible_buildings[0]
        mock_places.find_accessible_buildings.return_value = mock_accessible_buildings
        
        # Step 1: Search for CS courses
        courses = await server.call_tool("search_courses", {
            "term_code": "202502",
            "subject": "CS"
        })
        
        # Step 2: Find accessible buildings
        accessible_buildings = await server.call_tool("find_accessible_buildings", {
            "wheelchair_access": True,
            "elevator_access": True
        })
        
        # Step 3: Get building details for CS facilities
        building_details = await server.call_tool("get_building_details", {
            "building_id": "KLAUS"
        })
        
        # Validate accessibility integration
        assert len(courses) >= 1
        assert len(accessible_buildings) >= 1
        assert building_details['wheelchair_accessible'] is True
        assert building_details['elevator_access'] is True
        assert "Computer Science" in building_details['departments']
    
    @pytest.mark.asyncio
    @patch('gtmcp.server_expanded.smartech_client')
    async def test_research_collaboration_discovery(self, mock_smartech, server, mock_faculty_profiles, mock_ai_research):
        """Test finding research collaboration opportunities."""
        # Mock faculty research
        mock_smartech.find_faculty_research.return_value = mock_faculty_profiles
        
        # Mock research trends
        mock_trends = {
            'trends_by_year': {
                '2023': 25,
                '2022': 18,
                '2021': 12
            },
            'total_papers': 55,
            'trend_direction': 'increasing',
            'peak_year': '2023',
            'average_per_year': 18.3
        }
        mock_smartech.analyze_research_trends.return_value = mock_trends
        
        # Step 1: Find faculty research in AI
        faculty_research = await server.call_tool("find_faculty_research", {
            "research_area": "artificial intelligence"
        })
        
        # Step 2: Get collaboration suggestions
        collaboration_suggestions = await server.call_tool("get_research_collaboration_suggestions", {
            "research_interests": ["machine learning", "computer vision", "robotics"]
        })
        
        # Step 3: Analyze research trends
        research_trends = await server.call_tool("analyze_research_trends", {
            "keywords": ["artificial intelligence", "machine learning"],
            "years": 3
        })
        
        # Validate collaboration workflow
        assert len(faculty_research) >= 1
        assert any("Machine Learning" in profile['research_interests'] for profile in faculty_research)
        
        assert 'faculty_matches' in collaboration_suggestions
        assert 'collaboration_opportunities' in collaboration_suggestions
        
        assert research_trends['trend_direction'] == 'increasing'
        assert research_trends['total_papers'] == 55
    
    @pytest.mark.asyncio
    @patch('gtmcp.server_expanded.oscar_client')
    @patch('gtmcp.server_expanded.smartech_client')
    @patch('gtmcp.server_expanded.places_client')
    async def test_multi_semester_planning_workflow(self, mock_places, mock_smartech, mock_oscar, server):
        """Test planning across multiple semesters."""
        # Mock multiple semesters
        mock_semesters = [
            Semester("202502", "Spring 2025", False),
            Semester("202408", "Fall 2024", False),
            Semester("202501", "Spring 2024", True)  # View only
        ]
        mock_oscar.get_available_semesters.return_value = mock_semesters
        
        # Mock subjects for each semester
        mock_subjects = [
            Subject("CS", "Computer Science"),
            Subject("MATH", "Mathematics"),
            Subject("PHYS", "Physics")
        ]
        mock_oscar.get_subjects.return_value = mock_subjects
        
        # Mock route optimization
        mock_route = RouteOptimization(
            waypoints=["KLAUS", "COC", "STUC"],
            total_distance_miles=0.6,
            estimated_time_minutes=8,
            accessibility_rating="fully_accessible",
            step_by_step_directions=[
                "Start at Klaus Advanced Computing Building",
                "Walk north on Ferst Drive for 0.2 miles",
                "Arrive at College of Computing",
                "Continue east for 0.3 miles",
                "Arrive at Student Center"
            ]
        )
        mock_places.optimize_route.return_value = mock_route
        
        # Step 1: Get available semesters
        semesters = await server.call_tool("get_available_semesters", {})
        
        # Step 2: Get subjects for planning
        subjects_spring = await server.call_tool("get_subjects", {"term_code": "202502"})
        subjects_fall = await server.call_tool("get_subjects", {"term_code": "202408"})
        
        # Step 3: Optimize route between buildings
        route = await server.call_tool("optimize_campus_route", {
            "locations": ["KLAUS", "COC", "STUC"]
        })
        
        # Validate multi-semester planning
        assert len(semesters) == 3
        assert any(not sem['view_only'] for sem in semesters)  # Has active semesters
        
        assert len(subjects_spring) >= 1
        assert len(subjects_fall) >= 1
        assert any(subj['code'] == "CS" for subj in subjects_spring)
        
        assert route['total_distance_miles'] == 0.6
        assert route['accessibility_rating'] == "fully_accessible"
        assert len(route['step_by_step_directions']) >= 3
    
    @pytest.mark.asyncio
    @patch('gtmcp.server_expanded.oscar_client')
    @patch('gtmcp.server_expanded.smartech_client')
    @patch('gtmcp.server_expanded.places_client')
    async def test_real_world_student_scenario(self, mock_places, mock_smartech, mock_oscar, server,
                                             mock_ai_courses, mock_ai_research, mock_accessible_buildings):
        """Test complete real-world student workflow scenario."""
        # Mock all necessary data
        mock_smartech.search_records.return_value = {'papers': mock_ai_research, 'count': 3}
        mock_oscar.search_courses.return_value = mock_ai_courses
        mock_places.search_buildings.return_value = mock_accessible_buildings
        mock_places.get_building_details.return_value = mock_accessible_buildings[0]
        
        # Student workflow: "I'm interested in AI research, find related courses with accessible buildings"
        
        # Step 1: Find AI courses
        ai_courses = await server.call_tool("find_courses_for_research", {
            "research_topic": "artificial intelligence",
            "term_code": "202502"
        })
        
        # Step 2: Find accessible buildings for CS
        accessible_buildings = await server.call_tool("search_campus_locations", {
            "query": "computing",
            "accessible": True
        })
        
        # Step 3: Get detailed accessibility info
        accessibility_info = await server.call_tool("get_building_details", {
            "building_id": "KLAUS"
        })
        
        # Step 4: Get comprehensive context for a specific course
        if ai_courses['related_courses']:
            course_context = await server.call_tool("get_comprehensive_course_context", {
                "term_code": "202502",
                "crn": ai_courses['related_courses'][0]['crn']
            })
            
            # Validate comprehensive workflow
            assert 'course_details' in course_context
            assert 'related_research' in course_context
            assert 'building_info' in course_context
        
        # Validate complete student scenario
        assert len(ai_courses['related_courses']) >= 1
        assert len(ai_courses['research_papers']) >= 1
        assert ai_courses['correlation_strength'] > 0
        
        assert len(accessible_buildings) >= 1
        assert accessibility_info['wheelchair_accessible'] is True
        assert "Computer Science" in accessibility_info['departments']


class TestWorkflowPerformanceMetrics:
    """Test performance and scalability of workflows."""
    
    @pytest.fixture
    def server(self):
        """Get server instance for testing."""
        return server_expanded.server
    
    @pytest.mark.asyncio
    @patch('gtmcp.server_expanded.smartech_client')
    async def test_large_dataset_workflow_performance(self, mock_smartech, server):
        """Test workflow performance with large datasets."""
        # Create large dataset (200+ papers)
        large_paper_set = []
        for i in range(250):
            paper = ResearchPaper(
                oai_identifier=f"oai:repo:large_{i}",
                title=f"AI Research Paper {i}: Advanced Topics",
                authors=[f"Dr. Author{i}", f"Dr. Coauthor{i}"],
                abstract=f"This paper {i} explores advanced AI topics including machine learning, deep learning, and neural networks.",
                publication_date=datetime.now() - timedelta(days=i),
                subject_areas=["Computer Science", "Artificial Intelligence", "Machine Learning"],
                citation_count=max(1, 100 - i),  # Decreasing citation count
                related_courses=[f"CS {7000 + (i % 100)}"]
            )
            large_paper_set.append(paper)
        
        mock_smartech.search_records.return_value = {
            'papers': large_paper_set,
            'count': 250
        }
        
        # Time the workflow
        start_time = time.time()
        
        result = await server.call_tool("search_research_papers", {
            "keywords": ["artificial intelligence", "machine learning"],
            "max_records": 250
        })
        
        end_time = time.time()
        execution_time = end_time - start_time
        
        # Performance assertions
        assert result['count'] == 250
        assert len(result['papers']) == 250
        assert execution_time < 5.0  # Should complete within 5 seconds
        
        # Memory efficiency check - ensure large datasets are handled properly
        assert all('title' in paper for paper in result['papers'])
        assert all('authors' in paper for paper in result['papers'])
    
    @pytest.mark.asyncio
    @patch('gtmcp.server_expanded.oscar_client')
    @patch('gtmcp.server_expanded.smartech_client')
    @patch('gtmcp.server_expanded.places_client')
    async def test_concurrent_workflow_execution(self, mock_places, mock_smartech, mock_oscar, server):
        """Test concurrent execution of multiple workflows."""
        # Mock data for concurrent workflows
        mock_oscar.get_available_semesters.return_value = [Semester("202502", "Spring 2025", False)]
        mock_smartech.search_records.return_value = {'papers': [], 'count': 0}
        mock_places.search_buildings.return_value = []
        
        # Define multiple concurrent workflows
        workflows = [
            server.call_tool("get_available_semesters", {}),
            server.call_tool("search_research_papers", {"keywords": ["AI"]}),
            server.call_tool("search_campus_locations", {"query": "library"}),
            server.call_tool("find_accessible_buildings", {"wheelchair_access": True}),
            server.call_tool("get_system_health_status", {})
        ]
        
        # Execute workflows concurrently
        start_time = time.time()
        results = await asyncio.gather(*workflows, return_exceptions=True)
        end_time = time.time()
        
        # Performance and correctness assertions
        assert len(results) == 5
        assert all(not isinstance(result, Exception) for result in results)
        
        # Concurrent execution should be faster than sequential
        execution_time = end_time - start_time
        assert execution_time < 3.0  # Should complete within 3 seconds concurrently
    
    @pytest.mark.asyncio
    @patch('gtmcp.server_expanded.smartech_client')
    async def test_workflow_memory_efficiency(self, mock_smartech, server):
        """Test memory efficiency with large result sets."""
        # Create large dataset with varying sizes
        large_papers = []
        for i in range(100):
            # Vary the size of abstracts to test memory handling
            abstract_size = 1000 if i % 10 == 0 else 100  # Some large abstracts
            paper = ResearchPaper(
                oai_identifier=f"oai:repo:mem_{i}",
                title=f"Memory Test Paper {i}",
                authors=[f"Author{j}" for j in range(i % 5 + 1)],  # Varying author counts
                abstract="A" * abstract_size,  # Varying abstract sizes
                publication_date=datetime.now(),
                subject_areas=["Computer Science"] * (i % 3 + 1),  # Varying subject counts
                citation_count=i,
                related_courses=[f"CS {i}"]
            )
            large_papers.append(paper)
        
        mock_smartech.search_records.return_value = {
            'papers': large_papers,
            'count': 100
        }
        
        # Execute and measure memory usage patterns
        result = await server.call_tool("search_research_papers", {
            "keywords": ["memory test"]
        })
        
        # Memory efficiency checks
        assert result['count'] == 100
        assert len(result['papers']) == 100
        
        # Ensure large abstracts are handled properly
        large_abstract_papers = [p for p in result['papers'] if len(p['abstract']) > 500]
        assert len(large_abstract_papers) >= 5  # Should have some large abstracts
    
    @pytest.mark.asyncio
    @patch('gtmcp.server_expanded.oscar_client')
    @patch('gtmcp.server_expanded.smartech_client')
    async def test_workflow_with_system_degradation(self, mock_smartech, mock_oscar, server):
        """Test workflow behavior when some systems are degraded."""
        # Simulate OSCAR working but SMARTech having issues
        mock_oscar.get_available_semesters.return_value = [Semester("202502", "Spring 2025", False)]
        mock_oscar.search_courses.return_value = [
            CourseInfo("Test Course", "CS", "1000", "12345", "A")
        ]
        
        # Simulate SMARTech being slow/degraded
        async def slow_search(*args, **kwargs):
            await asyncio.sleep(0.1)  # Simulate slow response
            return {'papers': [], 'count': 0}
        
        mock_smartech.search_records.side_effect = slow_search
        
        # Test workflow resilience
        start_time = time.time()
        
        try:
            # This workflow combines both systems
            result = await asyncio.wait_for(
                server.call_tool("find_courses_for_research", {
                    "research_topic": "test",
                    "term_code": "202502"
                }),
                timeout=2.0  # 2 second timeout
            )
            
            # Should still work despite SMARTech being slow
            assert 'related_courses' in result
            assert 'research_papers' in result
            
        except asyncio.TimeoutError:
            pytest.fail("Workflow should handle degraded system performance")
        
        end_time = time.time()
        assert end_time - start_time < 2.0


class TestWorkflowSecurityValidation:
    """Test security aspects of workflows."""
    
    @pytest.fixture
    def server(self):
        """Get server instance for testing."""
        return server_expanded.server
    
    @pytest.mark.asyncio
    @patch('gtmcp.server_expanded.smartech_client')
    async def test_input_sanitization_workflow(self, mock_smartech, server):
        """Test that workflows properly sanitize user inputs."""
        mock_smartech.search_records.return_value = {'papers': [], 'count': 0}
        
        # Test potentially malicious inputs
        malicious_inputs = [
            "<script>alert('xss')</script>",
            "'; DROP TABLE papers; --",
            "../../etc/passwd",
            "javascript:alert('xss')",
            "%3Cscript%3Ealert('xss')%3C/script%3E"
        ]
        
        for malicious_input in malicious_inputs:
            try:
                # Should not raise security exceptions or break
                result = await server.call_tool("search_research_papers", {
                    "keywords": [malicious_input]
                })
                
                # Should return empty results but not fail
                assert 'papers' in result
                assert 'count' in result
                
            except Exception as e:
                # Should not expose sensitive information in errors
                error_message = str(e).lower()
                assert 'password' not in error_message
                assert 'database' not in error_message
                assert 'internal' not in error_message
    
    @pytest.mark.asyncio
    @patch('gtmcp.server_expanded.oscar_client')
    async def test_error_information_disclosure(self, mock_oscar, server):
        """Test that error messages don't disclose sensitive information."""
        # Simulate internal error
        mock_oscar.search_courses.side_effect = Exception("Database connection failed: user=admin, password=secret123, host=internal.db.server")
        
        try:
            await server.call_tool("search_courses", {
                "term_code": "202502",
                "subject": "CS"
            })
        except Exception as e:
            error_message = str(e).lower()
            
            # Should not expose sensitive information
            assert 'password' not in error_message
            assert 'admin' not in error_message
            assert 'secret' not in error_message
            assert 'internal.db.server' not in error_message
    
    @pytest.mark.asyncio
    @patch('gtmcp.server_expanded.smartech_client')
    @patch('gtmcp.server_expanded.oscar_client')
    @patch('gtmcp.server_expanded.places_client')
    async def test_system_health_information_security(self, mock_places, mock_smartech, mock_oscar, server):
        """Test that system health doesn't expose internal details."""
        # Mock health status with some internal information
        mock_oscar.get_health_status.return_value = {
            'service': 'OSCAR',
            'status': 'healthy',
            'internal_db_host': 'oscar-db-internal.gatech.edu',
            'api_key': 'secret-key-123',
            'timestamp': datetime.now().isoformat()
        }
        
        mock_smartech.get_health_status.return_value = {
            'service': 'SMARTech',
            'status': 'error',
            'error': 'Connection failed to internal server 192.168.1.100',
            'timestamp': datetime.now().isoformat()
        }
        
        mock_places.get_health_status.return_value = {
            'service': 'Places',
            'status': 'healthy',
            'timestamp': datetime.now().isoformat()
        }
        
        result = await server.call_tool("get_system_health_status", {})
        
        # Should not expose internal details in health status
        result_str = str(result).lower()
        assert 'internal' not in result_str or 'internal_db_host' not in result_str
        assert 'api_key' not in result_str
        assert 'secret' not in result_str
        assert '192.168.1.100' not in result_str
        
        # Should still provide useful health information
        assert 'oscar_health' in result
        assert 'smartech_health' in result
        assert 'places_health' in result
        assert 'overall_status' in result


class TestWorkflowDataValidation:
    """Test data quality and validation in workflows."""
    
    @pytest.fixture
    def server(self):
        """Get server instance for testing."""
        return server_expanded.server
    
    @pytest.mark.asyncio
    @patch('gtmcp.server_expanded.smartech_client')
    @patch('gtmcp.server_expanded.oscar_client')
    async def test_cross_system_data_validation(self, mock_oscar, mock_smartech, server):
        """Test that data is consistent across systems."""
        # Mock research papers with course references
        mock_papers = [
            ResearchPaper(
                oai_identifier="oai:repo:1",
                title="ML Research",
                authors=["Dr. Smith"],
                abstract="ML research",
                publication_date=datetime.now(),
                subject_areas=["Computer Science"],
                citation_count=25,
                related_courses=["CS 7641", "CS 7642"]  # These should exist in OSCAR
            )
        ]
        mock_smartech.search_records.return_value = {'papers': mock_papers, 'count': 1}
        
        # Mock corresponding courses in OSCAR
        mock_courses = [
            CourseInfo("Machine Learning", "CS", "7641", "12345", "A"),
            CourseInfo("Reinforcement Learning", "CS", "7642", "12346", "B")
        ]
        mock_oscar.search_courses.return_value = mock_courses
        
        result = await server.call_tool("find_courses_for_research", {
            "research_topic": "machine learning",
            "term_code": "202502"
        })
        
        # Validate cross-system consistency
        assert 'related_courses' in result
        assert 'research_papers' in result
        
        # Check that referenced courses actually exist
        related_course_numbers = [course['course_number'] for course in result['related_courses']]
        paper_course_references = mock_papers[0].related_courses
        
        # At least some courses should match between systems
        matching_courses = set(related_course_numbers) & set([ref.split()[1] for ref in paper_course_references])
        assert len(matching_courses) > 0
    
    @pytest.mark.asyncio
    @patch('gtmcp.server_expanded.smartech_client')
    async def test_workflow_data_freshness(self, mock_smartech, server):
        """Test that workflows return recent/fresh data."""
        # Mock papers with varying dates
        recent_date = datetime.now() - timedelta(days=30)
        old_date = datetime.now() - timedelta(days=365*2)  # 2 years old
        
        mock_papers = [
            ResearchPaper(
                oai_identifier="oai:repo:recent",
                title="Recent AI Research",
                authors=["Dr. Smith"],
                abstract="Recent research",
                publication_date=recent_date,
                subject_areas=["AI"],
                citation_count=10,
                related_courses=[]
            ),
            ResearchPaper(
                oai_identifier="oai:repo:old",
                title="Old AI Research",
                authors=["Dr. Johnson"],
                abstract="Older research",
                publication_date=old_date,
                subject_areas=["AI"],
                citation_count=50,
                related_courses=[]
            )
        ]
        mock_smartech.search_records.return_value = {'papers': mock_papers, 'count': 2}
        
        result = await server.call_tool("search_research_papers", {
            "keywords": ["artificial intelligence"],
            "date_from": (datetime.now() - timedelta(days=365)).strftime("%Y-%m-%d")
        })
        
        # Should prioritize recent papers when date filter is applied
        assert result['count'] >= 1
        
        # Check that results include recent papers
        publication_dates = [datetime.fromisoformat(paper['publication_date'].replace('Z', '+00:00')) 
                           for paper in result['papers']]
        recent_papers = [date for date in publication_dates if date > datetime.now() - timedelta(days=365)]
        assert len(recent_papers) >= 1
    
    @pytest.mark.asyncio
    @patch('gtmcp.server_expanded.oscar_client')
    @patch('gtmcp.server_expanded.smartech_client')
    @patch('gtmcp.server_expanded.places_client')
    async def test_workflow_completeness_validation(self, mock_places, mock_smartech, mock_oscar, server):
        """Test that workflows return complete data sets."""
        # Mock complete course details
        complete_course = CourseDetails(
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
            prerequisites=["CS 3600", "MATH 2550"],
            restrictions=["Must be enrolled in Graduate program"],
            attributes=["Honors Program"],
            meeting_times=["MWF 10:00-11:00"],
            instructors=["Dr. Smith, John"]
        )
        mock_oscar.get_course_details.return_value = complete_course
        
        # Mock complete research paper
        complete_paper = ResearchPaper(
            oai_identifier="oai:repo:complete",
            title="Complete ML Research",
            authors=["Dr. Smith, John", "Dr. Johnson, Alice"],
            abstract="Complete research with all fields",
            publication_date=datetime.now(),
            subject_areas=["Computer Science", "Machine Learning"],
            citation_count=100,
            related_courses=["CS 7641"]
        )
        mock_smartech.search_records.return_value = {'papers': [complete_paper], 'count': 1}
        
        # Mock complete building info
        complete_building = CampusLocation(
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
            amenities=["Computer Labs", "Study Rooms"],
            departments=["Computer Science"],
            hours={"monday": "7:00 AM - 11:00 PM"}
        )
        mock_places.get_building_details.return_value = complete_building
        
        result = await server.call_tool("get_comprehensive_course_context", {
            "term_code": "202502",
            "crn": "12345"
        })
        
        # Validate completeness of integrated data
        assert 'course_details' in result
        assert 'related_research' in result
        assert 'building_info' in result
        assert 'comprehensive_context' in result
        
        # Check course details completeness
        course_details = result['course_details']
        required_course_fields = ['title', 'subject', 'course_number', 'crn', 'credits', 
                                'prerequisites', 'instructors', 'registration']
        for field in required_course_fields:
            assert field in course_details, f"Missing required course field: {field}"
        
        # Check research data completeness
        research_data = result['related_research']
        if research_data['papers']:  # If papers exist
            paper = research_data['papers'][0]
            required_paper_fields = ['title', 'authors', 'abstract', 'subject_areas', 'citation_count']
            for field in required_paper_fields:
                assert field in paper, f"Missing required paper field: {field}"
        
        # Check building info completeness
        building_info = result['building_info']
        required_building_fields = ['name', 'building_code', 'wheelchair_accessible', 
                                  'amenities', 'departments']
        for field in required_building_fields:
            assert field in building_info, f"Missing required building field: {field}"