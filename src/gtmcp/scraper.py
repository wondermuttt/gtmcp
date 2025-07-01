"""Georgia Tech OSCAR web scraper."""

import logging
import re
import time
from typing import List, Optional
from urllib.parse import urlencode

import requests
from bs4 import BeautifulSoup

from .exceptions import NetworkError, ParseError, ValidationError
from .models import CourseDetails, CourseInfo, RegistrationInfo, Semester, Subject

logger = logging.getLogger(__name__)


class GTOscarScraper:
    """Scraper for Georgia Tech OSCAR course schedule system."""
    
    BASE_URL = "https://oscar.gatech.edu"
    SEMESTER_URL = f"{BASE_URL}/pls/bprod/bwckschd.p_disp_dyn_sched"
    TERM_SUBMIT_URL = f"{BASE_URL}/bprod/bwckgens.p_proc_term_date"
    COURSE_SEARCH_URL = f"{BASE_URL}/bprod/bwckschd.p_get_crse_unsec"
    COURSE_DETAIL_URL_TEMPLATE = f"{BASE_URL}/bprod/bwckschd.p_disp_detail_sched"
    
    def __init__(self, delay: float = 1.0, timeout: int = 30, max_retries: int = 3):
        """Initialize scraper with configuration options."""
        if delay < 0:
            raise ValidationError("Delay must be non-negative")
        if timeout <= 0:
            raise ValidationError("Timeout must be positive")
        if max_retries < 1:
            raise ValidationError("Max retries must be at least 1")
            
        self.session = requests.Session()
        self.delay = delay
        self.timeout = timeout
        self.max_retries = max_retries
        
        # Set user agent for respectful scraping
        self.session.headers.update({
            'User-Agent': 'GTMCP/1.0 (Educational Tool; +https://github.com/user/gtmcp)'
        })
        
        logger.info(f"Initialized scraper with delay={delay}s, timeout={timeout}s, max_retries={max_retries}")
        
    def _make_request(self, method: str, url: str, **kwargs) -> requests.Response:
        """Make HTTP request with delay, timeout, and retry logic."""
        if not url or not method:
            raise ValidationError("URL and method are required")
            
        if self.delay > 0:
            time.sleep(self.delay)
        
        # Set timeout if not provided
        if 'timeout' not in kwargs:
            kwargs['timeout'] = self.timeout
            
        last_exception = None
        for attempt in range(self.max_retries):
            try:
                logger.debug(f"Making {method} request to {url} (attempt {attempt + 1}/{self.max_retries})")
                response = self.session.request(method, url, **kwargs)
                response.raise_for_status()
                
                logger.debug(f"Request successful: {response.status_code}")
                return response
                
            except requests.exceptions.Timeout as e:
                last_exception = e
                logger.warning(f"Request timeout on attempt {attempt + 1}: {e}")
            except requests.exceptions.ConnectionError as e:
                last_exception = e
                logger.warning(f"Connection error on attempt {attempt + 1}: {e}")
            except requests.exceptions.HTTPError as e:
                last_exception = e
                logger.error(f"HTTP error on attempt {attempt + 1}: {e}")
                # Don't retry on client errors (4xx)
                if 400 <= response.status_code < 500:
                    break
            except requests.RequestException as e:
                last_exception = e
                logger.warning(f"Request error on attempt {attempt + 1}: {e}")
                
            if attempt < self.max_retries - 1:
                wait_time = self.delay * (2 ** attempt)  # Exponential backoff
                logger.info(f"Retrying in {wait_time:.1f} seconds...")
                time.sleep(wait_time)
                    
        error_msg = f"Request failed after {self.max_retries} attempts: {last_exception}"
        logger.error(error_msg)
        raise NetworkError(error_msg) from last_exception
    
    def get_available_semesters(self) -> List[Semester]:
        """Get list of available semesters."""
        try:
            logger.info("Fetching available semesters")
            response = self._make_request("GET", self.SEMESTER_URL)
            
            if not response.text:
                raise ParseError("Empty response from semester page")
                
            soup = BeautifulSoup(response.text, 'html.parser')
            
            select = soup.find('select', {'name': 'p_term'})
            if not select:
                logger.error("Semester dropdown not found in page")
                raise ParseError("Could not find semester selection dropdown")
                
            semesters = []
            option_count = 0
            
            for option in select.find_all('option'):
                option_count += 1
                value = option.get('value', '').strip()
                text = option.get_text().strip()
                
                # Skip empty or "None" options
                if not value or value.lower() == "none":
                    continue
                    
                try:
                    view_only = "(View only)" in text
                    clean_name = text.replace("(View only)", "").strip()
                    
                    if not clean_name:
                        logger.warning(f"Empty semester name for code: {value}")
                        continue
                        
                    semester = Semester(
                        code=value,
                        name=clean_name,
                        view_only=view_only
                    )
                    semesters.append(semester)
                    
                except Exception as e:
                    logger.warning(f"Failed to parse semester option: {text}, error: {e}")
                    continue
                    
            logger.info(f"Found {len(semesters)} valid semesters out of {option_count} options")
            
            if not semesters:
                logger.warning("No valid semesters found")
                
            return semesters
            
        except (NetworkError, ParseError):
            raise
        except Exception as e:
            logger.error(f"Unexpected error getting semesters: {e}")
            raise ParseError(f"Failed to retrieve semesters: {e}") from e
    
    def get_subjects(self, term_code: str) -> List[Subject]:
        """Get available subjects for a given term."""
        if not term_code or not term_code.strip():
            raise ValidationError("Term code is required and cannot be empty")
            
        try:
            logger.info(f"Fetching subjects for term: {term_code}")
            
            # Submit term selection to get course search form
            form_data = {
                'p_calling_proc': 'bwckschd.p_disp_dyn_sched',
                'p_term': term_code.strip()
            }
            
            response = self._make_request(
                "POST", 
                self.TERM_SUBMIT_URL,
                data=form_data,
                headers={'Content-Type': 'application/x-www-form-urlencoded'}
            )
            
            if not response.text:
                raise ParseError("Empty response from term submission")
                
            soup = BeautifulSoup(response.text, 'html.parser')
            select = soup.find('select', {'name': 'sel_subj'})
            
            if not select:
                logger.error("Subject dropdown not found in page")
                raise ParseError("Could not find subject selection dropdown")
                
            subjects = []
            option_count = 0
            
            for option in select.find_all('option'):
                option_count += 1
                value = option.get('value', '').strip()
                text = option.get_text().strip()
                
                # Skip dummy/placeholder options
                if not value or value in ['dummy', '%', '']:
                    continue
                    
                try:
                    if not text:
                        logger.warning(f"Empty subject name for code: {value}")
                        continue
                        
                    subject = Subject(code=value, name=text)
                    subjects.append(subject)
                    
                except Exception as e:
                    logger.warning(f"Failed to parse subject option: {value} - {text}, error: {e}")
                    continue
                    
            logger.info(f"Found {len(subjects)} valid subjects out of {option_count} options")
            
            if not subjects:
                logger.warning(f"No subjects found for term: {term_code}")
                
            return subjects
            
        except (NetworkError, ParseError, ValidationError):
            raise
        except Exception as e:
            logger.error(f"Unexpected error getting subjects for term {term_code}: {e}")
            raise ParseError(f"Failed to retrieve subjects: {e}") from e
    
    def search_courses(
        self, 
        term_code: str, 
        subject: str, 
        course_num: Optional[str] = None,
        title: Optional[str] = None
    ) -> List[CourseInfo]:
        """Search for courses in a given term and subject."""
        # Build form data for course search - note: using multiple sel_subj entries
        form_data = [
            ('term_in', term_code),
            ('sel_subj', 'dummy'),
            ('sel_day', 'dummy'), 
            ('sel_schd', 'dummy'),
            ('sel_insm', 'dummy'),
            ('sel_camp', 'dummy'),
            ('sel_levl', 'dummy'),
            ('sel_sess', 'dummy'),
            ('sel_instr', 'dummy'),
            ('sel_ptrm', 'dummy'),
            ('sel_attr', 'dummy'),
            ('sel_subj', subject),  # The actual subject we want
            ('sel_crse', course_num or ''),
            ('sel_title', title or ''),
            ('sel_schd', '%'),
            ('sel_from_cred', ''),
            ('sel_to_cred', ''),
            ('sel_levl', '%'),
            ('sel_camp', '%'),
            ('sel_ptrm', '%'),
            ('sel_instr', '%'),
            ('sel_attr', '%'),
            ('begin_hh', '0'),
            ('begin_mi', '0'), 
            ('begin_ap', 'a'),
            ('end_hh', '0'),
            ('end_mi', '0'),
            ('end_ap', 'a')
        ]
        
        response = self._make_request(
            "POST",
            self.COURSE_SEARCH_URL,
            data=form_data,
            headers={'Content-Type': 'application/x-www-form-urlencoded'}
        )
        
        soup = BeautifulSoup(response.text, 'html.parser')
        courses = []
        
        # Find course listing table
        for th in soup.find_all('th', class_='ddtitle'):
            link = th.find('a')
            if link:
                # Extract CRN from link URL
                href = link.get('href', '')
                crn_match = re.search(r'crn_in=(\d+)', href)
                if crn_match:
                    crn = crn_match.group(1)
                    
                    # Parse course title for subject, number, section
                    title_text = link.get_text().strip()
                    # Format: "Course Title - CRN - SUBJ NUM - SECTION"
                    parts = title_text.split(' - ')
                    if len(parts) >= 4:
                        course_title = parts[0]
                        course_code_section = parts[2]  # e.g., "CS 1100"
                        section = parts[3]
                        
                        code_parts = course_code_section.split()
                        if len(code_parts) >= 2:
                            subj = code_parts[0]
                            num = code_parts[1]
                            
                            courses.append(CourseInfo(
                                crn=crn,
                                title=course_title,
                                subject=subj,
                                course_number=num,
                                section=section
                            ))
                            
        return courses
    
    def get_course_details(self, term_code: str, crn: str) -> CourseDetails:
        """Get detailed information for a specific course."""
        params = {'term_in': term_code, 'crn_in': crn}
        url = f"{self.COURSE_DETAIL_URL_TEMPLATE}?{urlencode(params)}"
        
        response = self._make_request("GET", url)
        soup = BeautifulSoup(response.text, 'html.parser')
        
        # Parse course title and basic info
        title_th = soup.find('th', class_='ddlabel')
        if not title_th:
            raise Exception("Could not find course title")
            
        title_text = title_th.get_text().strip()
        # Parse title format: "Course Title - CRN - SUBJ NUM - SECTION"
        parts = title_text.split(' - ')
        if len(parts) < 4:
            raise Exception(f"Unexpected title format: {title_text}")
            
        course_title = parts[0]
        parsed_crn = parts[1]
        course_code = parts[2]  # e.g., "CS 1100"
        section = parts[3]
        
        code_parts = course_code.split()
        if len(code_parts) < 2:
            raise Exception(f"Could not parse course code: {course_code}")
            
        subject = code_parts[0]
        course_number = code_parts[1]
        
        # Parse course details from the main content
        content_td = soup.find('td', class_='dddefault')
        if not content_td:
            raise Exception("Could not find course content")
            
        content_text = content_td.get_text()
        
        # Extract term
        term_match = re.search(r'Associated Term:\s*([^\n]+)', content_text)
        term = term_match.group(1).strip() if term_match else ""
        
        # Extract levels
        levels_match = re.search(r'Levels:\s*([^\n]+)', content_text)
        levels = []
        if levels_match:
            levels_text = levels_match.group(1).strip()
            levels = [level.strip() for level in levels_text.split(',')]
        
        # Extract campus
        campus_match = re.search(r'([^*]+)\*\s*Campus', content_text)
        campus = campus_match.group(1).strip() if campus_match else ""
        
        # Extract schedule type  
        schedule_match = re.search(r'([^*]+)\*\s*Schedule Type', content_text)
        schedule_type = schedule_match.group(1).strip() if schedule_match else ""
        
        # Extract credits
        credits_match = re.search(r'(\d+(?:\.\d+)?)\s*Credits', content_text)
        credits = float(credits_match.group(1)) if credits_match else 0.0
        
        # Parse registration table - find the correct one with caption "Registration Availability"
        reg_table = None
        for table in soup.find_all('table', class_='datadisplaytable'):
            caption = table.find('caption', class_='captiontext')
            if caption and 'Registration Availability' in caption.get_text():
                reg_table = table
                break
        
        registration = self._parse_registration_table(reg_table)
        
        # Extract restrictions
        restrictions = self._parse_restrictions(content_text)
        
        # Find catalog link
        catalog_link = content_td.find('a', href=re.compile(r'bwckctlg\.p_display_courses'))
        catalog_url = None
        if catalog_link:
            catalog_url = self.BASE_URL + catalog_link.get('href')
        
        return CourseDetails(
            crn=crn,
            title=course_title,
            subject=subject,
            course_number=course_number,
            section=section,
            term=term,
            credits=credits,
            schedule_type=schedule_type,
            campus=campus,
            levels=levels,
            registration=registration,
            restrictions=restrictions,
            catalog_url=catalog_url
        )
    
    def _parse_registration_table(self, table) -> RegistrationInfo:
        """Parse the registration availability table."""
        if not table:
            return RegistrationInfo(
                seats_capacity=0, seats_actual=0, seats_remaining=0,
                waitlist_capacity=0, waitlist_actual=0, waitlist_remaining=0
            )
            
        # Find seats and waitlist rows
        seats_data = [0, 0, 0]  # capacity, actual, remaining
        waitlist_data = [0, 0, 0]
        
        for row in table.find_all('tr'):
            th = row.find('th', class_='ddlabel')
            if th:
                label = th.get_text().strip()
                tds = row.find_all('td', class_='dddefault')
                
                if 'Seats' in label and 'Waitlist' not in label and len(tds) >= 3:
                    try:
                        seats_data = [int(td.get_text().strip()) for td in tds[:3]]
                    except ValueError:
                        # Skip if can't parse as integers
                        pass
                elif 'Waitlist Seats' in label and len(tds) >= 3:
                    try:
                        waitlist_data = [int(td.get_text().strip()) for td in tds[:3]]
                    except ValueError:
                        # Skip if can't parse as integers
                        pass
                    
        return RegistrationInfo(
            seats_capacity=seats_data[0],
            seats_actual=seats_data[1], 
            seats_remaining=seats_data[2],
            waitlist_capacity=waitlist_data[0],
            waitlist_actual=waitlist_data[1],
            waitlist_remaining=waitlist_data[2]
        )
    
    def _parse_restrictions(self, content_text: str) -> List[str]:
        """Parse course restrictions from content text."""
        restrictions = []
        
        # Look for restrictions section
        restrictions_match = re.search(r'Restrictions:(.*?)(?:\n\n|\n\s*\n|$)', content_text, re.DOTALL)
        if restrictions_match:
            restrictions_text = restrictions_match.group(1).strip()
            
            # Split on common restriction patterns
            restriction_lines = re.split(r'\n\s*', restrictions_text)
            for line in restriction_lines:
                line = line.strip()
                if line and not line.startswith('&nbsp;'):
                    restrictions.append(line)
                    
        return restrictions