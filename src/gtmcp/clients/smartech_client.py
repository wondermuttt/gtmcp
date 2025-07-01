"""SMARTech research repository client using OAI-PMH protocol."""

import logging
import re
import xml.etree.ElementTree as ET
from datetime import datetime
from typing import List, Optional, Dict, Any
from urllib.parse import urlencode

import xmltodict
from dateutil import parser as date_parser

from .base_client import BaseClient, DataParsingError, ValidationError
from ..models import ResearchPaper, FacultyResearchProfile

logger = logging.getLogger(__name__)


class SMARTechClient(BaseClient):
    """Client for Georgia Tech SMARTech research repository via OAI-PMH."""
    
    # OAI-PMH namespaces
    OAI_NS = {
        'oai': 'http://www.openarchives.org/OAI/2.0/',
        'dc': 'http://purl.org/dc/elements/1.1/',
        'oai_dc': 'http://www.openarchives.org/OAI/2.0/oai_dc/'
    }
    
    def __init__(self, **kwargs):
        """Initialize SMARTech client."""
        super().__init__(
            base_url="https://repository.gatech.edu/server/oai",
            **kwargs
        )
        self.request_url = f"{self.base_url}/request"
        
    def test_connection(self) -> bool:
        """Test connection to SMARTech OAI-PMH interface."""
        try:
            response = self._make_request('GET', f"{self.request_url}?verb=Identify")
            return "Georgia Tech Digital Repository" in response.text
        except Exception as e:
            logger.error(f"SMARTech connection test failed: {e}")
            return False
    
    async def atest_connection(self) -> bool:
        """Async test connection to SMARTech."""
        try:
            async with self._async_session.get(f"{self.request_url}?verb=Identify") as response:
                text = await response.text()
                return "Georgia Tech Digital Repository" in text
        except Exception as e:
            logger.error(f"SMARTech async connection test failed: {e}")
            return False
    
    def get_repository_info(self) -> Dict[str, Any]:
        """Get basic repository information."""
        try:
            logger.info("Fetching repository information")
            response = self._make_request('GET', f"{self.request_url}?verb=Identify")
            
            # Parse XML response
            root = ET.fromstring(response.content)
            identify = root.find('.//oai:Identify', self.OAI_NS)
            
            if identify is None:
                raise DataParsingError("Could not find Identify element in response")
            
            info = {}
            for child in identify:
                tag = child.tag.replace('{http://www.openarchives.org/OAI/2.0/}', '')
                info[tag] = child.text
                
            logger.info("Successfully retrieved repository information")
            return info
            
        except Exception as e:
            logger.error(f"Error fetching repository info: {e}")
            raise DataParsingError(f"Failed to fetch repository info: {e}")
    
    def list_sets(self, resumption_token: Optional[str] = None) -> Dict[str, Any]:
        """List available sets (collections) in the repository."""
        try:
            logger.info("Fetching repository sets")
            
            params = {'verb': 'ListSets'}
            if resumption_token:
                params['resumptionToken'] = resumption_token
                
            query_string = urlencode(params)
            response = self._make_request('GET', f"{self.request_url}?{query_string}")
            
            # Parse XML response
            root = ET.fromstring(response.content)
            list_sets = root.find('.//oai:ListSets', self.OAI_NS)
            
            if list_sets is None:
                raise DataParsingError("Could not find ListSets element in response")
            
            sets = []
            for set_elem in list_sets.findall('.//oai:set', self.OAI_NS):
                set_spec = set_elem.find('oai:setSpec', self.OAI_NS)
                set_name = set_elem.find('oai:setName', self.OAI_NS)
                
                if set_spec is not None and set_name is not None:
                    sets.append({
                        'setSpec': set_spec.text,
                        'setName': set_name.text
                    })
            
            # Check for resumption token
            resumption = list_sets.find('.//oai:resumptionToken', self.OAI_NS)
            next_token = resumption.text if resumption is not None else None
            
            result = {
                'sets': sets,
                'resumptionToken': next_token,
                'totalCount': len(sets)
            }
            
            if resumption is not None:
                result['completeListSize'] = resumption.get('completeListSize')
                result['cursor'] = resumption.get('cursor')
            
            logger.info(f"Found {len(sets)} sets")
            return result
            
        except Exception as e:
            logger.error(f"Error fetching sets: {e}")
            raise DataParsingError(f"Failed to fetch sets: {e}")
    
    def search_records(
        self,
        keywords: Optional[List[str]] = None,
        subject_areas: Optional[List[str]] = None,
        date_from: Optional[str] = None,
        date_until: Optional[str] = None,
        set_spec: Optional[str] = None,
        resumption_token: Optional[str] = None,
        max_records: int = 100
    ) -> Dict[str, Any]:
        """Search for research records using OAI-PMH ListRecords."""
        try:
            logger.info(f"Searching records with keywords: {keywords}, subjects: {subject_areas}")
            
            params = {
                'verb': 'ListRecords',
                'metadataPrefix': 'oai_dc'
            }
            
            if resumption_token:
                params['resumptionToken'] = resumption_token
            else:
                if date_from:
                    params['from'] = self._format_date(date_from)
                if date_until:
                    params['until'] = self._format_date(date_until)
                if set_spec:
                    params['set'] = set_spec
            
            query_string = urlencode(params)
            response = self._make_request('GET', f"{self.request_url}?{query_string}")
            
            # Parse XML response
            root = ET.fromstring(response.content)
            list_records = root.find('.//oai:ListRecords', self.OAI_NS)
            
            if list_records is None:
                raise DataParsingError("Could not find ListRecords element in response")
            
            papers = []
            for record in list_records.findall('.//oai:record', self.OAI_NS):
                try:
                    paper = self._parse_record(record)
                    
                    # Apply keyword filtering if specified
                    if self._matches_criteria(paper, keywords, subject_areas):
                        papers.append(paper)
                        
                    # Stop if we've reached max_records
                    if len(papers) >= max_records:
                        break
                        
                except Exception as e:
                    logger.warning(f"Error parsing record: {e}")
                    continue
            
            # Check for resumption token
            resumption = list_records.find('.//oai:resumptionToken', self.OAI_NS)
            next_token = resumption.text if resumption is not None else None
            
            result = {
                'papers': papers,
                'resumptionToken': next_token,
                'count': len(papers)
            }
            
            if resumption is not None:
                result['completeListSize'] = resumption.get('completeListSize')
                result['cursor'] = resumption.get('cursor')
            
            logger.info(f"Found {len(papers)} matching records")
            return result
            
        except Exception as e:
            logger.error(f"Error searching records: {e}")
            raise DataParsingError(f"Failed to search records: {e}")
    
    def get_record_by_identifier(self, identifier: str) -> ResearchPaper:
        """Get a specific record by its OAI identifier."""
        try:
            logger.info(f"Fetching record: {identifier}")
            
            params = {
                'verb': 'GetRecord',
                'identifier': identifier,
                'metadataPrefix': 'oai_dc'
            }
            
            query_string = urlencode(params)
            response = self._make_request('GET', f"{self.request_url}?{query_string}")
            
            # Parse XML response
            root = ET.fromstring(response.content)
            record = root.find('.//oai:record', self.OAI_NS)
            
            if record is None:
                raise DataParsingError(f"Could not find record with identifier: {identifier}")
            
            paper = self._parse_record(record)
            logger.info(f"Successfully retrieved record: {identifier}")
            return paper
            
        except Exception as e:
            logger.error(f"Error fetching record {identifier}: {e}")
            raise DataParsingError(f"Failed to fetch record {identifier}: {e}")
    
    def find_faculty_research(self, area: str) -> List[FacultyResearchProfile]:
        """Find faculty research profiles based on research area."""
        try:
            logger.info(f"Searching for faculty research in area: {area}")
            
            # Search for records and group by author
            search_results = self.search_records(
                keywords=[area],
                max_records=500
            )
            
            # Group papers by author to create faculty profiles
            faculty_papers = {}
            
            for paper in search_results['papers']:
                for author in paper.authors:
                    # Clean author name (remove affiliation info if present)
                    clean_author = self._clean_author_name(author)
                    
                    if clean_author not in faculty_papers:
                        faculty_papers[clean_author] = []
                    faculty_papers[clean_author].append(paper)
            
            # Create faculty profiles
            profiles = []
            for author, papers in faculty_papers.items():
                # Extract research interests from paper subjects
                research_interests = set()
                for paper in papers:
                    research_interests.update(paper.subject_areas)
                
                profile = FacultyResearchProfile(
                    name=author,
                    department="",  # Not available from OAI-PMH data
                    research_interests=list(research_interests),
                    recent_publications=papers[-10:],  # Most recent 10
                    active_projects=[],  # Not available from OAI-PMH data
                    collaboration_opportunities=[]  # To be determined by analysis
                )
                profiles.append(profile)
            
            # Sort by number of publications in the area
            profiles.sort(key=lambda p: len(p.recent_publications), reverse=True)
            
            logger.info(f"Found {len(profiles)} faculty with research in {area}")
            return profiles[:20]  # Return top 20
            
        except Exception as e:
            logger.error(f"Error finding faculty research: {e}")
            raise DataParsingError(f"Failed to find faculty research: {e}")
    
    def analyze_research_trends(
        self, 
        keywords: List[str], 
        years: int = 5
    ) -> Dict[str, Any]:
        """Analyze research trends over time for given keywords."""
        try:
            logger.info(f"Analyzing research trends for: {keywords}")
            
            current_year = datetime.now().year
            trends = {}
            
            for year in range(current_year - years, current_year + 1):
                date_from = f"{year}-01-01"
                date_until = f"{year}-12-31"
                
                search_results = self.search_records(
                    keywords=keywords,
                    date_from=date_from,
                    date_until=date_until,
                    max_records=1000
                )
                
                trends[str(year)] = {
                    'count': search_results['count'],
                    'papers': search_results['papers']
                }
            
            # Calculate trend statistics
            counts = [trends[str(year)]['count'] for year in range(current_year - years, current_year + 1)]
            trend_direction = 'increasing' if counts[-1] > counts[0] else 'decreasing'
            
            analysis = {
                'trends_by_year': trends,
                'total_papers': sum(counts),
                'trend_direction': trend_direction,
                'peak_year': str(current_year - years + counts.index(max(counts))),
                'average_per_year': sum(counts) / len(counts)
            }
            
            logger.info(f"Completed trend analysis for {keywords}")
            return analysis
            
        except Exception as e:
            logger.error(f"Error analyzing research trends: {e}")
            raise DataParsingError(f"Failed to analyze research trends: {e}")
    
    def _parse_record(self, record) -> ResearchPaper:
        """Parse an OAI-PMH record into a ResearchPaper object."""
        try:
            # Get header info
            header = record.find('oai:header', self.OAI_NS)
            identifier = header.find('oai:identifier', self.OAI_NS).text
            datestamp = header.find('oai:datestamp', self.OAI_NS).text
            
            # Get metadata
            metadata = record.find('.//oai_dc:dc', self.OAI_NS)
            
            if metadata is None:
                raise DataParsingError("Could not find Dublin Core metadata")
            
            # Extract Dublin Core elements
            title_elem = metadata.find('dc:title', self.OAI_NS)
            title = title_elem.text if title_elem is not None else ""
            
            authors = []
            for creator in metadata.findall('dc:creator', self.OAI_NS):
                if creator.text:
                    authors.append(creator.text.strip())
            
            description_elem = metadata.find('dc:description', self.OAI_NS)
            abstract = description_elem.text if description_elem is not None else ""
            
            subjects = []
            for subject in metadata.findall('dc:subject', self.OAI_NS):
                if subject.text:
                    subjects.append(subject.text.strip())
            
            # Parse publication date
            date_elem = metadata.find('dc:date', self.OAI_NS)
            publication_date = None
            if date_elem is not None and date_elem.text:
                try:
                    publication_date = date_parser.parse(date_elem.text)
                except:
                    publication_date = datetime.now()
            else:
                publication_date = datetime.now()
            
            return ResearchPaper(
                oai_identifier=identifier,
                title=title,
                authors=authors,
                abstract=abstract,
                publication_date=publication_date,
                subject_areas=subjects,
                citation_count=None,  # Not available in OAI-PMH
                related_courses=[]  # To be determined by cross-referencing
            )
            
        except Exception as e:
            logger.error(f"Error parsing record: {e}")
            raise DataParsingError(f"Failed to parse record: {e}")
    
    def _matches_criteria(
        self, 
        paper: ResearchPaper, 
        keywords: Optional[List[str]], 
        subject_areas: Optional[List[str]]
    ) -> bool:
        """Check if a paper matches the search criteria."""
        if not keywords and not subject_areas:
            return True
        
        text_to_search = f"{paper.title} {paper.abstract} {' '.join(paper.subject_areas)}".lower()
        
        # Check keywords
        if keywords:
            keyword_match = any(keyword.lower() in text_to_search for keyword in keywords)
            if not keyword_match:
                return False
        
        # Check subject areas
        if subject_areas:
            subject_match = any(
                any(subject.lower() in paper_subject.lower() for paper_subject in paper.subject_areas)
                for subject in subject_areas
            )
            if not subject_match:
                return False
        
        return True
    
    def _clean_author_name(self, author: str) -> str:
        """Clean author name by removing affiliation info."""
        # Remove common affiliation patterns
        patterns = [
            r'\(.*?\)',  # Remove parenthetical info
            r',\s*Georgia Institute of Technology.*',  # Remove GT affiliation
            r',\s*Georgia Tech.*',  # Remove GT affiliation
        ]
        
        cleaned = author
        for pattern in patterns:
            cleaned = re.sub(pattern, '', cleaned, flags=re.IGNORECASE)
        
        return cleaned.strip()
    
    def _format_date(self, date_str: str) -> str:
        """Format date for OAI-PMH (YYYY-MM-DD format)."""
        try:
            if isinstance(date_str, str):
                # Try to parse and reformat
                parsed_date = date_parser.parse(date_str)
                return parsed_date.strftime('%Y-%m-%d')
            return date_str
        except:
            return date_str