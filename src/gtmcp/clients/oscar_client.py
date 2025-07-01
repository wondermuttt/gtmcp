"""OSCAR course scheduling client using new base client architecture."""

import logging
import re
from typing import List, Optional
from urllib.parse import urlencode

from bs4 import BeautifulSoup

from .base_client import BaseClient, DataParsingError, ValidationError
from ..exceptions import NetworkError, ParseError
from ..models import CourseDetails, CourseInfo, RegistrationInfo, Semester, Subject

logger = logging.getLogger(__name__)


class OscarClient(BaseClient):
    """Client for Georgia Tech OSCAR course schedule system."""
    
    def __init__(self, **kwargs):
        """Initialize OSCAR client."""
        super().__init__(
            base_url="https://oscar.gatech.edu",
            **kwargs
        )
        self.semester_url = f"{self.base_url}/pls/bprod/bwckschd.p_disp_dyn_sched"
        self.term_submit_url = f"{self.base_url}/bprod/bwckgens.p_proc_term_date"
        self.course_search_url = f"{self.base_url}/bprod/bwckschd.p_get_crse_unsec"
        self.course_detail_url_template = f"{self.base_url}/bprod/bwckschd.p_disp_detail_sched"
    
    def test_connection(self) -> bool:
        """Test connection to OSCAR system."""
        try:
            response = self._make_request('GET', self.semester_url)
            return "Schedule of Classes" in response.text or "bwckschd" in response.text
        except Exception as e:
            logger.error(f"OSCAR connection test failed: {e}")
            return False
    
    async def atest_connection(self) -> bool:
        """Async test connection to OSCAR system."""
        try:
            async with self._async_session.get(self.semester_url) as response:
                text = await response.text()
                return "Schedule of Classes" in text or "bwckschd" in text
        except Exception as e:
            logger.error(f"OSCAR async connection test failed: {e}")
            return False
    
    def get_available_semesters(self) -> List[Semester]:
        """Get list of available semesters."""
        try:
            logger.info("Fetching available semesters")
            response = self._make_request('GET', self.semester_url)
            
            soup = BeautifulSoup(response.content, 'html.parser')
            
            # Find semester select dropdown
            semester_select = soup.find('select', {'name': 'p_term'})
            if not semester_select:
                raise ParseError("Could not find semester dropdown")
            
            semesters = []
            for option in semester_select.find_all('option'):
                value = option.get('value', '').strip()
                text = option.get_text(strip=True)
                
                if value and text and value != '%':
                    # Check if this is a view-only semester (usually indicated in text)
                    view_only = 'view only' in text.lower()
                    semesters.append(Semester(
                        code=value,
                        name=text,
                        view_only=view_only
                    ))
            
            logger.info(f"Found {len(semesters)} available semesters")
            return semesters
            
        except Exception as e:
            logger.error(f"Error fetching available semesters: {e}")
            raise NetworkError(f"Failed to fetch available semesters: {e}")
    
    def get_subjects(self, term_code: str) -> List[Subject]:
        """Get list of available subjects for a given term."""
        if not term_code or not term_code.strip():
            raise ValidationError("term_code is required and cannot be empty")
        
        try:
            logger.info(f"Fetching subjects for term {term_code}")
            
            # First, submit the term to get the course search form
            form_data = {
                'p_calling_proc': 'bwckschd.p_disp_dyn_sched',
                'p_term': term_code
            }
            
            response = self._make_request('POST', self.term_submit_url, data=form_data)
            soup = BeautifulSoup(response.content, 'html.parser')
            
            # Find the subject select dropdown
            subject_select = soup.find('select', {'name': 'sel_subj'})
            if not subject_select:
                raise ParseError("Could not find subject dropdown")
            
            subjects = []
            for option in subject_select.find_all('option'):
                value = option.get('value', '').strip()
                text = option.get_text(strip=True)
                
                if value and text and value != '%':
                    subjects.append(Subject(code=value, name=text))
            
            logger.info(f"Found {len(subjects)} subjects for term {term_code}")
            return subjects
            
        except Exception as e:
            logger.error(f"Error fetching subjects for term {term_code}: {e}")
            raise NetworkError(f"Failed to fetch subjects for term {term_code}: {e}")
    
    def get_courses_by_subject(self, term_code: str, subject: str) -> List[CourseInfo]:
        """
        Get ALL courses for a subject using the correct OSCAR workflow.
        This replaces the problematic search_courses method.
        """
        if not term_code or not term_code.strip():
            raise ValidationError("term_code is required and cannot be empty")
        if not subject or not subject.strip():
            raise ValidationError("subject is required and cannot be empty")
        
        try:
            logger.info(f"Getting all courses for term {term_code}, subject {subject}")
            
            # Step 1: Submit term to get to course selection form
            term_form_data = {
                'p_calling_proc': 'bwckschd.p_disp_dyn_sched',
                'p_term': term_code
            }
            
            response = self._make_request('POST', self.term_submit_url, data=term_form_data)
            
            # Step 2: Submit subject selection to get course list
            # This is the key fix - we select the subject to get ALL courses, not search
            subject_form_data = [
                ('term_in', term_code),
                ('sel_subj', 'dummy'),  # Required first entry
                ('sel_subj', subject),  # Actual subject selection
                ('sel_day', 'dummy'),
                ('sel_schd', '%'),      # All schedule types
                ('sel_insm', 'dummy'),
                ('sel_camp', '%'),      # All campuses  
                ('sel_levl', '%'),      # All levels
                ('sel_sess', '%'),      # All sessions
                ('sel_instr', '%'),     # All instructors
                ('sel_ptrm', '%'),      # All part of term
                ('sel_attr', '%'),      # All attributes
                ('sel_crse', ''),       # No specific course filter
                ('sel_title', ''),      # No title filter
                ('begin_hh', '0'),      # Time filters
                ('begin_mi', '0'),
                ('begin_ap', 'a'),
                ('end_hh', '0'),
                ('end_mi', '0'),
                ('end_ap', 'a')
            ]
            
            response = self._make_request('POST', self.course_search_url, data=subject_form_data)
            
            # Parse results
            soup = BeautifulSoup(response.content, 'html.parser')
            
            courses = []
            
            # Look for course data tables
            for table in soup.find_all('table', class_='datadisplaytable'):
                caption = table.find('caption', class_='captiontext')
                if not caption:
                    continue
                
                caption_text = caption.get_text(strip=True)
                
                # Extract course info from caption
                if ' - ' in caption_text:
                    try:
                        parts = caption_text.split(' - ')
                        if len(parts) >= 4:
                            title = parts[0].strip()
                            course_code = parts[1].strip()
                            crn = parts[2].strip()
                            section = parts[3].strip()
                            
                            # Parse course code to get subject and number
                            course_match = re.match(r'^([A-Z]+)\s*(\d+[A-Z]*)$', course_code)
                            if course_match:
                                course_subject = course_match.group(1)
                                course_number = course_match.group(2)
                                
                                course = CourseInfo(
                                    crn=crn,
                                    title=title,
                                    subject=course_subject,
                                    course_number=course_number,
                                    section=section
                                )
                                courses.append(course)
                                
                    except Exception as e:
                        logger.warning(f"Error parsing course caption '{caption_text}': {e}")
                        continue
            
            logger.info(f"Found {len(courses)} courses for {subject} in {term_code}")
            return courses
            
        except Exception as e:
            logger.error(f"Error getting courses for {subject} in {term_code}: {e}")
            raise NetworkError(f"Failed to get courses for {subject}: {e}")
    
    def search_courses(
        self, 
        term_code: str, 
        subject: str, 
        course_num: Optional[str] = None, 
        title: Optional[str] = None
    ) -> List[CourseInfo]:
        """
        Search for courses - now uses the working get_courses_by_subject method
        and filters locally for better reliability.
        """
        # Get all courses for the subject first
        all_courses = self.get_courses_by_subject(term_code, subject)
        
        # Apply local filtering if needed
        filtered_courses = all_courses
        
        if course_num:
            course_num = course_num.strip()
            filtered_courses = [c for c in filtered_courses 
                              if course_num in c.course_number or 
                                 c.course_number.startswith(course_num)]
        
        if title:
            title_lower = title.lower().strip()
            filtered_courses = [c for c in filtered_courses 
                              if title_lower in c.title.lower()]
        
        logger.info(f"Filtered to {len(filtered_courses)} courses from {len(all_courses)} total")
        return filtered_courses
    
    def get_course_details(self, term_code: str, crn: str) -> CourseDetails:
        """Get detailed information for a specific course."""
        if not term_code or not term_code.strip():
            raise ValidationError("term_code is required and cannot be empty")
        if not crn or not crn.strip():
            raise ValidationError("crn is required and cannot be empty")
        
        try:
            logger.info(f"Fetching course details for CRN {crn} in term {term_code}")
            
            url = f"{self.course_detail_url_template}?term_in={term_code}&crn_in={crn}"
            response = self._make_request('GET', url)
            
            soup = BeautifulSoup(response.content, 'html.parser')
            
            # Find main course info table
            main_table = soup.find('table', class_='datadisplaytable')
            if not main_table:
                raise ParseError("Could not find course details table")
            
            # Extract basic course information
            caption = main_table.find('caption', class_='captiontext')
            if not caption:
                raise ParseError("Could not find course caption")
            
            caption_text = caption.get_text(strip=True)
            parts = caption_text.split(' - ')
            
            if len(parts) < 4:
                raise ParseError(f"Invalid course caption format: {caption_text}")
            
            title = parts[0].strip()
            course_code = parts[1].strip()
            crn_from_caption = parts[2].strip()
            section = parts[3].strip()
            
            # Parse course code
            course_match = re.match(r'^([A-Z]+)\s*(\d+[A-Z]*)$', course_code)
            if not course_match:
                raise ParseError(f"Invalid course code format: {course_code}")
            
            subject = course_match.group(1)
            course_number = course_match.group(2)
            
            # Extract detailed information from table rows
            rows = main_table.find_all('tr')
            
            # Initialize with defaults
            credits = 0.0
            schedule_type = ""
            campus = ""
            levels = []
            term = ""
            
            # Parse table rows for details
            for row in rows:
                cells = row.find_all(['th', 'td'])
                if len(cells) >= 2:
                    header = cells[0].get_text(strip=True)
                    value = cells[1].get_text(strip=True)
                    
                    if 'Credits' in header:
                        try:
                            credits = float(value)
                        except ValueError:
                            logger.warning(f"Could not parse credits: {value}")
                    elif 'Schedule Type' in header:
                        schedule_type = value
                    elif 'Campus' in header:
                        campus = value
                    elif 'Levels' in header:
                        levels = [level.strip() for level in value.split(',')]
                    elif 'Associated Term' in header:
                        term = value
            
            # Extract registration information
            registration_info = self._extract_registration_info(soup)
            
            # Extract restrictions
            restrictions = self._extract_restrictions(soup)
            
            # Find catalog URL if present
            catalog_url = None
            for link in soup.find_all('a'):
                href = link.get('href', '')
                if 'catalog' in href.lower():
                    catalog_url = href
                    break
            
            course_details = CourseDetails(
                crn=crn_from_caption,
                title=title,
                subject=subject,
                course_number=course_number,
                section=section,
                term=term,
                credits=credits,
                schedule_type=schedule_type,
                campus=campus,
                levels=levels,
                registration=registration_info,
                restrictions=restrictions,
                catalog_url=catalog_url
            )
            
            logger.info(f"Successfully extracted course details for CRN {crn}")
            return course_details
            
        except Exception as e:
            logger.error(f"Error fetching course details for CRN {crn}: {e}")
            raise NetworkError(f"Failed to fetch course details for CRN {crn}: {e}")
    
    def _extract_registration_info(self, soup: BeautifulSoup) -> RegistrationInfo:
        """Extract registration information from course details page."""
        # Look for registration tables
        registration_info = RegistrationInfo(
            seats_capacity=0,
            seats_actual=0,
            seats_remaining=0,
            waitlist_capacity=0,
            waitlist_actual=0,
            waitlist_remaining=0
        )
        
        # Find tables with registration data
        for table in soup.find_all('table', class_='datadisplaytable'):
            caption = table.find('caption')
            if caption and 'Registration Availability' in caption.get_text():
                rows = table.find_all('tr')
                for row in rows:
                    cells = row.find_all(['th', 'td'])
                    if len(cells) >= 4:
                        row_text = ' '.join([cell.get_text(strip=True) for cell in cells])
                        
                        if 'Seats' in row_text:
                            try:
                                registration_info.seats_capacity = int(cells[1].get_text(strip=True))
                                registration_info.seats_actual = int(cells[2].get_text(strip=True))
                                registration_info.seats_remaining = int(cells[3].get_text(strip=True))
                            except (ValueError, IndexError):
                                logger.warning("Could not parse seats information")
                        
                        elif 'Waitlist' in row_text:
                            try:
                                registration_info.waitlist_capacity = int(cells[1].get_text(strip=True))
                                registration_info.waitlist_actual = int(cells[2].get_text(strip=True))
                                registration_info.waitlist_remaining = int(cells[3].get_text(strip=True))
                            except (ValueError, IndexError):
                                logger.warning("Could not parse waitlist information")
        
        return registration_info
    
    def _extract_restrictions(self, soup: BeautifulSoup) -> List[str]:
        """Extract restrictions from course details page."""
        restrictions = []
        
        # Look for restrictions tables
        for table in soup.find_all('table', class_='datadisplaytable'):
            caption = table.find('caption')
            if caption and 'Restrictions' in caption.get_text():
                for row in table.find_all('tr'):
                    cells = row.find_all(['th', 'td'])
                    for cell in cells:
                        text = cell.get_text(strip=True)
                        if text and text not in ['Restrictions', 'None']:
                            restrictions.append(text)
        
        return restrictions