#!/usr/bin/env python3
"""
Concurrent Oscar Client - Optimized for batch operations
Maintains a connection pool for better performance
"""

import concurrent.futures
import logging
from typing import List, Dict, Any, Optional
from .clients.oscar_client import OscarClient
from .models import CourseDetails

logger = logging.getLogger(__name__)


class ConcurrentOscarClient:
    """Oscar client optimized for concurrent operations"""
    
    def __init__(self, max_workers: int = 10, timeout: int = 30):
        self.max_workers = max_workers
        self.timeout = timeout
        self.executor = concurrent.futures.ThreadPoolExecutor(max_workers=max_workers)
        
    def __enter__(self):
        return self
        
    def __exit__(self, exc_type, exc_val, exc_tb):
        self.executor.shutdown(wait=True)
        
    def fetch_course_details_batch(self, course_requests: List[tuple]) -> Dict[str, CourseDetails]:
        """
        Fetch multiple course details concurrently
        
        Args:
            course_requests: List of (term_code, crn) tuples
            
        Returns:
            Dict mapping crn to CourseDetails
        """
        results = {}
        
        def fetch_single(term_code: str, crn: str) -> tuple:
            """Fetch details for a single course"""
            try:
                # Each thread gets its own client connection
                with OscarClient(timeout=self.timeout) as client:
                    details = client.get_course_details(term_code, crn)
                    return (crn, details)
            except Exception as e:
                logger.error(f"Error fetching {crn} in {term_code}: {e}")
                return (crn, None)
        
        # Submit all requests
        futures = {
            self.executor.submit(fetch_single, term, crn): (term, crn)
            for term, crn in course_requests
        }
        
        # Collect results as they complete
        for future in concurrent.futures.as_completed(futures):
            try:
                crn, details = future.result()
                if details:
                    results[crn] = details
            except Exception as e:
                term, crn = futures[future]
                logger.error(f"Failed to fetch {crn}: {e}")
                
        return results


# Global client pool for reuse
_client_pool = None

def get_concurrent_client() -> ConcurrentOscarClient:
    """Get or create the global concurrent client"""
    global _client_pool
    if _client_pool is None:
        _client_pool = ConcurrentOscarClient()
    return _client_pool