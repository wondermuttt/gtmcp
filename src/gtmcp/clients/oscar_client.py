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
                ('sel_schd', 'dummy'),  # Required dummy
                ('sel_schd', '%'),      # All schedule types
                ('sel_insm', 'dummy'),
                ('sel_insm', '%'),      # All instruction methods
                ('sel_camp', 'dummy'),  # Required dummy
                ('sel_camp', '%'),      # All campuses  
                ('sel_levl', 'dummy'),  # Required dummy
                ('sel_levl', '%'),      # All levels
                ('sel_sess', 'dummy'),  # Required dummy
                ('sel_instr', 'dummy'), # Required dummy
                ('sel_instr', '%'),     # All instructors
                ('sel_ptrm', 'dummy'),  # Required dummy
                ('sel_ptrm', '%'),      # All part of term
                ('sel_attr', 'dummy'),  # Required dummy
                ('sel_attr', '%'),      # All attributes
                ('sel_crse', ''),       # No specific course filter
                ('sel_title', ''),      # No title filter
                ('sel_from_cred', ''),  # Credit range
                ('sel_to_cred', ''),    
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
            
            # Look for course data in th elements with class ddtitle
            # Format: "Introduction to Computing - 82294 - CS 1301 - A"
            for th in soup.find_all('th', class_='ddtitle'):
                # Get the link inside the th element
                link = th.find('a')
                if not link:
                    continue
                
                course_text = link.get_text(strip=True)
                
                # Extract course info from the text
                if ' - ' in course_text:
                    try:
                        parts = course_text.split(' - ')
                        if len(parts) >= 4:
                            title = parts[0].strip()
                            crn = parts[1].strip()
                            course_code = parts[2].strip()
                            section = parts[3].strip()
                            
                            # Parse course code to get subject and number
                            course_match = re.match(r'^([A-Z]+)\s*(\d+[A-Z]*)$', course_code)
                            if course_match:
                                course_subject = course_match.group(1)
                                course_number = course_match.group(2)
                                
                                # Find the next tr with course details
                                next_tr = th.find_parent('tr').find_next_sibling('tr')
                                description = ""
                                credit_hours = 3  # Default
                                
                                # Extract campus from section code patterns
                                campus = None
                                if section:
                                    # Common campus patterns based on section codes
                                    if section.startswith('L'):  # L00, L01 etc are Lorraine
                                        campus = 'L'
                                    elif section.startswith('O'):  # O01, O02, OAN etc are Online
                                        campus = 'O'
                                    elif section in ['OSZ']:  # Special online Shenzhen
                                        campus = 'S'  # But it's online, so maybe O?
                                    elif section.startswith('Q'):  # QSA, QCH etc are Professional (Atlanta-based)
                                        campus = 'A'
                                    elif section[0].isalpha() and len(section) <= 3:  # A, B, C, etc are Atlanta
                                        # Exclude already handled patterns
                                        if section[0] not in ['L', 'O', 'Q', 'V']:
                                            campus = 'A'
                                
                                if next_tr:
                                    # Look for course details in the dddefault td
                                    details_td = next_tr.find('td', class_='dddefault')
                                    if details_td:
                                        details_text = details_td.get_text()
                                        
                                        # Try to extract campus from details text if available
                                        if 'Campus:' in details_text:
                                            campus_start = details_text.find('Campus:') + len('Campus:')
                                            campus_end = details_text.find('\n', campus_start)
                                            if campus_end != -1:
                                                campus_text = details_text[campus_start:campus_end].strip()
                                                # Map campus names to codes
                                                campus_map = {
                                                    'Atlanta': 'A',
                                                    'Online': 'O',
                                                    'Lorraine': 'L',
                                                    'Shenzhen': 'S'
                                                }
                                                for name, code in campus_map.items():
                                                    if name in campus_text:
                                                        campus = code
                                                        break
                                        
                                        # Extract description if present
                                        if 'Course Info:' in details_text:
                                            desc_start = details_text.find('Course Info:') + len('Course Info:')
                                            desc_end = details_text.find('Associated Term:', desc_start)
                                            if desc_end == -1:
                                                desc_end = details_text.find('\n', desc_start + 100)
                                            if desc_end != -1:
                                                description = details_text[desc_start:desc_end].strip()
                                
                                # Look for credit hours in nearby elements
                                # This is typically in a separate cell
                                
                                course = CourseInfo(
                                    crn=crn,
                                    title=title,
                                    subject=course_subject,
                                    course_number=course_number,
                                    section=section,
                                    campus=campus
                                )
                                courses.append(course)
                                
                    except Exception as e:
                        logger.warning(f"Error parsing course '{course_text}': {e}")
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
            
            # Extract basic course information from th element
            course_header = main_table.find('th', class_='ddlabel')
            if not course_header:
                raise ParseError("Could not find course header")
            
            header_text = course_header.get_text(strip=True)
            parts = header_text.split(' - ')
            
            if len(parts) < 4:
                raise ParseError(f"Invalid course header format: {header_text}")
            
            title = parts[0].strip()
            crn_from_caption = parts[1].strip()
            course_code = parts[2].strip()
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
                        
                        if 'Waitlist' in row_text:
                            try:
                                registration_info.waitlist_capacity = int(cells[1].get_text(strip=True))
                                registration_info.waitlist_actual = int(cells[2].get_text(strip=True))
                                registration_info.waitlist_remaining = int(cells[3].get_text(strip=True))
                            except (ValueError, IndexError):
                                logger.warning("Could not parse waitlist information")
                        
                        elif 'Seats' in row_text or 'Class' in row_text:
                            try:
                                registration_info.seats_capacity = int(cells[1].get_text(strip=True))
                                registration_info.seats_actual = int(cells[2].get_text(strip=True))
                                registration_info.seats_remaining = int(cells[3].get_text(strip=True))
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