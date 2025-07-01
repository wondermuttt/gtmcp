"""Tests for the SMARTech client functionality."""

import pytest
import xml.etree.ElementTree as ET
from unittest.mock import Mock, patch, MagicMock
from datetime import datetime

from gtmcp.clients.smartech_client import SMARTechClient
from gtmcp.clients.base_client import NetworkError, DataParsingError, ValidationError
from gtmcp.models import ResearchPaper, FacultyResearchProfile


class TestSMARTechClientInit:
    """Test SMARTechClient initialization."""
    
    def test_init_with_defaults(self):
        """Test initialization with default values."""
        client = SMARTechClient()
        
        assert client.base_url == "https://repository.gatech.edu/server/oai"
        assert client.request_url == "https://repository.gatech.edu/server/oai/request"


class TestSMARTechClientConnection:
    """Test SMARTech client connection functionality."""
    
    @patch('gtmcp.clients.smartech_client.SMARTechClient._make_request')
    def test_connection_success(self, mock_request):
        """Test successful connection to SMARTech."""
        mock_response = Mock()
        mock_response.text = "Georgia Tech Digital Repository"
        mock_request.return_value = mock_response
        
        client = SMARTechClient()
        
        with client:
            result = client.test_connection()
        
        assert result is True
    
    @patch('gtmcp.clients.smartech_client.SMARTechClient._make_request')
    def test_connection_failure(self, mock_request):
        """Test failed connection to SMARTech."""
        mock_request.side_effect = Exception("Connection failed")
        
        client = SMARTechClient()
        
        with client:
            result = client.test_connection()
        
        assert result is False


class TestSMARTechClientRepositoryInfo:
    """Test repository information retrieval."""
    
    @patch('gtmcp.clients.smartech_client.SMARTechClient._make_request')
    def test_get_repository_info_success(self, mock_request):
        """Test successful repository info retrieval."""
        xml_content = """<?xml version="1.0" encoding="UTF-8"?>
        <OAI-PMH xmlns="http://www.openarchives.org/OAI/2.0/">
            <Identify>
                <repositoryName>Georgia Tech Digital Repository</repositoryName>
                <baseURL>https://repository.gatech.edu/server/oai/request</baseURL>
                <protocolVersion>2.0</protocolVersion>
                <adminEmail>repository@library.gatech.edu</adminEmail>
                <earliestDatestamp>2004-07-21T19:26:51Z</earliestDatestamp>
            </Identify>
        </OAI-PMH>"""
        
        mock_response = Mock()
        mock_response.content = xml_content.encode('utf-8')
        mock_request.return_value = mock_response
        
        client = SMARTechClient()
        
        with client:
            info = client.get_repository_info()
        
        assert info['repositoryName'] == "Georgia Tech Digital Repository"
        assert info['baseURL'] == "https://repository.gatech.edu/server/oai/request"
        assert info['protocolVersion'] == "2.0"
        assert info['adminEmail'] == "repository@library.gatech.edu"
        assert info['earliestDatestamp'] == "2004-07-21T19:26:51Z"
    
    @patch('gtmcp.clients.smartech_client.SMARTechClient._make_request')
    def test_get_repository_info_invalid_xml(self, mock_request):
        """Test repository info with invalid XML."""
        mock_response = Mock()
        mock_response.content = b"Invalid XML content"
        mock_request.return_value = mock_response
        
        client = SMARTechClient()
        
        with client:
            with pytest.raises(DataParsingError):
                client.get_repository_info()
    
    @patch('gtmcp.clients.smartech_client.SMARTechClient._make_request')
    def test_get_repository_info_missing_identify(self, mock_request):
        """Test repository info with missing Identify element."""
        xml_content = """<?xml version="1.0" encoding="UTF-8"?>
        <OAI-PMH xmlns="http://www.openarchives.org/OAI/2.0/">
            <responseDate>2023-01-01T00:00:00Z</responseDate>
        </OAI-PMH>"""
        
        mock_response = Mock()
        mock_response.content = xml_content.encode('utf-8')
        mock_request.return_value = mock_response
        
        client = SMARTechClient()
        
        with client:
            with pytest.raises(DataParsingError, match="Could not find Identify element"):
                client.get_repository_info()


class TestSMARTechClientSets:
    """Test sets (collections) listing functionality."""
    
    @patch('gtmcp.clients.smartech_client.SMARTechClient._make_request')
    def test_list_sets_success(self, mock_request):
        """Test successful sets listing."""
        xml_content = """<?xml version="1.0" encoding="UTF-8"?>
        <OAI-PMH xmlns="http://www.openarchives.org/OAI/2.0/">
            <ListSets>
                <set>
                    <setSpec>com_1853_67546</setSpec>
                    <setName>Institute Research and Scholarship</setName>
                </set>
                <set>
                    <setSpec>com_1853_67399</setSpec>
                    <setName>Special Collections</setName>
                </set>
                <resumptionToken completeListSize="306" cursor="0">////100</resumptionToken>
            </ListSets>
        </OAI-PMH>"""
        
        mock_response = Mock()
        mock_response.content = xml_content.encode('utf-8')
        mock_request.return_value = mock_response
        
        client = SMARTechClient()
        
        with client:
            result = client.list_sets()
        
        assert len(result['sets']) == 2
        assert result['sets'][0]['setSpec'] == 'com_1853_67546'
        assert result['sets'][0]['setName'] == 'Institute Research and Scholarship'
        assert result['sets'][1]['setSpec'] == 'com_1853_67399'
        assert result['sets'][1]['setName'] == 'Special Collections'
        assert result['resumptionToken'] == '////100'
        assert result['completeListSize'] == '306'
    
    @patch('gtmcp.clients.smartech_client.SMARTechClient._make_request')
    def test_list_sets_with_resumption_token(self, mock_request):
        """Test sets listing with resumption token."""
        xml_content = """<?xml version="1.0" encoding="UTF-8"?>
        <OAI-PMH xmlns="http://www.openarchives.org/OAI/2.0/">
            <ListSets>
                <set>
                    <setSpec>com_1853_67547</setSpec>
                    <setName>More Research</setName>
                </set>
            </ListSets>
        </OAI-PMH>"""
        
        mock_response = Mock()
        mock_response.content = xml_content.encode('utf-8')
        mock_request.return_value = mock_response
        
        client = SMARTechClient()
        
        with client:
            result = client.list_sets(resumption_token="////100")
        
        assert len(result['sets']) == 1
        assert result['sets'][0]['setSpec'] == 'com_1853_67547'
        assert result['resumptionToken'] is None


class TestSMARTechClientRecords:
    """Test record search and retrieval functionality."""
    
    @patch('gtmcp.clients.smartech_client.SMARTechClient._make_request')
    def test_search_records_success(self, mock_request):
        """Test successful record search."""
        xml_content = """<?xml version="1.0" encoding="UTF-8"?>
        <OAI-PMH xmlns="http://www.openarchives.org/OAI/2.0/" 
                 xmlns:oai_dc="http://www.openarchives.org/OAI/2.0/oai_dc/"
                 xmlns:dc="http://purl.org/dc/elements/1.1/">
            <ListRecords>
                <record>
                    <header>
                        <identifier>oai:repository.gatech.edu:1853/1234</identifier>
                        <datestamp>2023-01-01T00:00:00Z</datestamp>
                    </header>
                    <metadata>
                        <oai_dc:dc>
                            <dc:title>Machine Learning Applications</dc:title>
                            <dc:creator>Smith, John</dc:creator>
                            <dc:creator>Doe, Jane</dc:creator>
                            <dc:description>This paper discusses machine learning applications.</dc:description>
                            <dc:subject>Computer Science</dc:subject>
                            <dc:subject>Machine Learning</dc:subject>
                            <dc:date>2023-01-01</dc:date>
                        </oai_dc:dc>
                    </metadata>
                </record>
            </ListRecords>
        </OAI-PMH>"""
        
        mock_response = Mock()
        mock_response.content = xml_content.encode('utf-8')
        mock_request.return_value = mock_response
        
        client = SMARTechClient()
        
        with client:
            result = client.search_records(keywords=['machine learning'])
        
        assert len(result['papers']) == 1
        paper = result['papers'][0]
        assert paper.oai_identifier == "oai:repository.gatech.edu:1853/1234"
        assert paper.title == "Machine Learning Applications"
        assert len(paper.authors) == 2
        assert "Smith, John" in paper.authors
        assert "Doe, Jane" in paper.authors
        assert paper.abstract == "This paper discusses machine learning applications."
        assert "Computer Science" in paper.subject_areas
        assert "Machine Learning" in paper.subject_areas
    
    @patch('gtmcp.clients.smartech_client.SMARTechClient._make_request')
    def test_search_records_with_filters(self, mock_request):
        """Test record search with date and subject filters."""
        xml_content = """<?xml version="1.0" encoding="UTF-8"?>
        <OAI-PMH xmlns="http://www.openarchives.org/OAI/2.0/">
            <ListRecords>
            </ListRecords>
        </OAI-PMH>"""
        
        mock_response = Mock()
        mock_response.content = xml_content.encode('utf-8')
        mock_request.return_value = mock_response
        
        client = SMARTechClient()
        
        with client:
            result = client.search_records(
                keywords=['AI'],
                subject_areas=['Computer Science'],
                date_from='2020-01-01',
                date_until='2023-12-31',
                max_records=10
            )
        
        assert result['papers'] == []
        assert result['count'] == 0
    
    @patch('gtmcp.clients.smartech_client.SMARTechClient._make_request')
    def test_get_record_by_identifier_success(self, mock_request):
        """Test successful retrieval of specific record."""
        xml_content = """<?xml version="1.0" encoding="UTF-8"?>
        <OAI-PMH xmlns="http://www.openarchives.org/OAI/2.0/" 
                 xmlns:oai_dc="http://www.openarchives.org/OAI/2.0/oai_dc/"
                 xmlns:dc="http://purl.org/dc/elements/1.1/">
            <GetRecord>
                <record>
                    <header>
                        <identifier>oai:repository.gatech.edu:1853/5678</identifier>
                        <datestamp>2023-02-01T00:00:00Z</datestamp>
                    </header>
                    <metadata>
                        <oai_dc:dc>
                            <dc:title>Robotics Research</dc:title>
                            <dc:creator>Johnson, Bob</dc:creator>
                            <dc:description>Advanced robotics research.</dc:description>
                            <dc:subject>Robotics</dc:subject>
                            <dc:date>2023-02-01</dc:date>
                        </oai_dc:dc>
                    </metadata>
                </record>
            </GetRecord>
        </OAI-PMH>"""
        
        mock_response = Mock()
        mock_response.content = xml_content.encode('utf-8')
        mock_request.return_value = mock_response
        
        client = SMARTechClient()
        
        with client:
            paper = client.get_record_by_identifier("oai:repository.gatech.edu:1853/5678")
        
        assert paper.oai_identifier == "oai:repository.gatech.edu:1853/5678"
        assert paper.title == "Robotics Research"
        assert "Johnson, Bob" in paper.authors
        assert paper.abstract == "Advanced robotics research."
        assert "Robotics" in paper.subject_areas
    
    @patch('gtmcp.clients.smartech_client.SMARTechClient._make_request')
    def test_get_record_by_identifier_not_found(self, mock_request):
        """Test record retrieval when record not found."""
        xml_content = """<?xml version="1.0" encoding="UTF-8"?>
        <OAI-PMH xmlns="http://www.openarchives.org/OAI/2.0/">
            <error code="idDoesNotExist">No matching identifier</error>
        </OAI-PMH>"""
        
        mock_response = Mock()
        mock_response.content = xml_content.encode('utf-8')
        mock_request.return_value = mock_response
        
        client = SMARTechClient()
        
        with client:
            with pytest.raises(DataParsingError, match="Could not find record"):
                client.get_record_by_identifier("invalid_id")


class TestSMARTechClientFacultyResearch:
    """Test faculty research functionality."""
    
    @patch('gtmcp.clients.smartech_client.SMARTechClient.search_records')
    def test_find_faculty_research_success(self, mock_search):
        """Test successful faculty research finding."""
        # Mock papers for faculty research
        mock_papers = [
            ResearchPaper(
                oai_identifier="oai:repo:1",
                title="AI Research Paper 1",
                authors=["Dr. Smith, John", "Dr. Johnson, Alice"],
                abstract="AI research abstract",
                publication_date=datetime(2023, 1, 1),
                subject_areas=["Artificial Intelligence", "Computer Science"],
                citation_count=None,
                related_courses=[]
            ),
            ResearchPaper(
                oai_identifier="oai:repo:2",
                title="AI Research Paper 2",
                authors=["Dr. Smith, John", "Dr. Brown, Bob"],
                abstract="More AI research",
                publication_date=datetime(2023, 2, 1),
                subject_areas=["Machine Learning", "AI"],
                citation_count=None,
                related_courses=[]
            )
        ]
        
        mock_search.return_value = {'papers': mock_papers}
        
        client = SMARTechClient()
        
        with client:
            profiles = client.find_faculty_research("artificial intelligence")
        
        assert len(profiles) >= 1
        
        # Find Dr. Smith's profile
        smith_profile = next((p for p in profiles if "Smith" in p.name), None)
        assert smith_profile is not None
        assert smith_profile.name == "Dr. Smith, John"
        assert len(smith_profile.recent_publications) == 2
        assert "Artificial Intelligence" in smith_profile.research_interests
    
    @patch('gtmcp.clients.smartech_client.SMARTechClient.search_records')
    def test_find_faculty_research_no_results(self, mock_search):
        """Test faculty research finding with no results."""
        mock_search.return_value = {'papers': []}
        
        client = SMARTechClient()
        
        with client:
            profiles = client.find_faculty_research("nonexistent field")
        
        assert profiles == []


class TestSMARTechClientTrendAnalysis:
    """Test research trend analysis functionality."""
    
    @patch('gtmcp.clients.smartech_client.SMARTechClient.search_records')
    def test_analyze_research_trends_success(self, mock_search):
        """Test successful research trend analysis."""
        # Mock search results for different years
        def mock_search_side_effect(keywords=None, date_from=None, date_until=None, max_records=1000):
            if "2023" in date_from:
                return {'papers': [Mock(), Mock()], 'count': 2}  # 2 papers in 2023
            elif "2022" in date_from:
                return {'papers': [Mock()], 'count': 1}  # 1 paper in 2022
            else:
                return {'papers': [], 'count': 0}  # 0 papers in other years
        
        mock_search.side_effect = mock_search_side_effect
        
        client = SMARTechClient()
        
        with client:
            trends = client.analyze_research_trends(['machine learning'], years=3)
        
        assert 'trends_by_year' in trends
        assert 'total_papers' in trends
        assert 'trend_direction' in trends
        assert 'peak_year' in trends
        assert 'average_per_year' in trends
        
        # Should have data for 3 years (current year - 2 to current year)
        current_year = datetime.now().year
        assert str(current_year) in trends['trends_by_year']
        assert str(current_year - 1) in trends['trends_by_year']
        assert str(current_year - 2) in trends['trends_by_year']


class TestSMARTechClientUtilities:
    """Test utility methods."""
    
    def test_clean_author_name(self):
        """Test author name cleaning."""
        client = SMARTechClient()
        
        with client:
            # Test removing parenthetical info
            cleaned = client._clean_author_name("Smith, John (Georgia Tech)")
            assert cleaned == "Smith, John"
            
            # Test removing GT affiliation
            cleaned = client._clean_author_name("Doe, Jane, Georgia Institute of Technology")
            assert cleaned == "Doe, Jane"
            
            # Test name that doesn't need cleaning
            cleaned = client._clean_author_name("Johnson, Bob")
            assert cleaned == "Johnson, Bob"
    
    def test_format_date(self):
        """Test date formatting for OAI-PMH."""
        client = SMARTechClient()
        
        with client:
            # Test string date
            formatted = client._format_date("2023-01-15")
            assert formatted == "2023-01-15"
            
            # Test datetime string
            formatted = client._format_date("January 15, 2023")
            assert "2023-01-15" in formatted
            
            # Test invalid date (should return original)
            formatted = client._format_date("invalid-date")
            assert formatted == "invalid-date"
    
    def test_matches_criteria(self):
        """Test criteria matching for papers."""
        client = SMARTechClient()
        
        paper = ResearchPaper(
            oai_identifier="test",
            title="Machine Learning Applications",
            authors=["Smith, John"],
            abstract="This paper discusses AI and machine learning",
            publication_date=datetime.now(),
            subject_areas=["Computer Science", "AI"],
            citation_count=None,
            related_courses=[]
        )
        
        with client:
            # Test keyword matching
            assert client._matches_criteria(paper, ["machine learning"], None)
            assert client._matches_criteria(paper, ["robotics"], None) is False
            
            # Test subject area matching
            assert client._matches_criteria(paper, None, ["Computer Science"])
            assert client._matches_criteria(paper, None, ["Biology"]) is False
            
            # Test combined matching
            assert client._matches_criteria(paper, ["AI"], ["Computer Science"])
            assert client._matches_criteria(paper, ["robotics"], ["Biology"]) is False
            
            # Test no criteria (should match)
            assert client._matches_criteria(paper, None, None)