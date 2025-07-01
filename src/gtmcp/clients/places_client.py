"""GT Places API client for campus location and building information."""

import logging
from typing import List, Optional, Dict, Any, Tuple
import json

from .base_client import BaseClient, DataParsingError, ValidationError
from ..models import CampusLocation, RouteOptimization, RouteStep

logger = logging.getLogger(__name__)


class PlacesClient(BaseClient):
    """Client for Georgia Tech Places API."""
    
    def __init__(self, **kwargs):
        """Initialize GT Places client."""
        super().__init__(
            base_url="https://rnoc.gatech.edu/gt-places-api",
            **kwargs
        )
    
    def test_connection(self) -> bool:
        """Test connection to GT Places API."""
        try:
            # Try to access the API documentation or health endpoint
            response = self._make_request('GET', '')
            return response.status_code == 200
        except Exception as e:
            logger.error(f"GT Places connection test failed: {e}")
            return False
    
    async def atest_connection(self) -> bool:
        """Async test connection to GT Places API."""
        try:
            async with self._async_session.get('') as response:
                return response.status == 200
        except Exception as e:
            logger.error(f"GT Places async connection test failed: {e}")
            return False
    
    def get_all_locations(self) -> List[CampusLocation]:
        """Get all campus locations and buildings."""
        try:
            logger.info("Fetching all campus locations")
            
            # This is a placeholder implementation - actual API structure needs to be determined
            response = self._make_request('GET', '/locations')
            
            if response.headers.get('content-type', '').startswith('application/json'):
                data = response.json()
            else:
                raise DataParsingError("Expected JSON response from Places API")
            
            locations = []
            
            # Parse location data (structure will depend on actual API)
            if isinstance(data, list):
                location_list = data
            elif isinstance(data, dict) and 'locations' in data:
                location_list = data['locations']
            else:
                raise DataParsingError("Unexpected response structure from Places API")
            
            for item in location_list:
                location = self._parse_location_data(item)
                if location:
                    locations.append(location)
            
            logger.info(f"Found {len(locations)} campus locations")
            return locations
            
        except Exception as e:
            logger.error(f"Error fetching campus locations: {e}")
            raise DataParsingError(f"Failed to fetch campus locations: {e}")
    
    def search_locations(
        self,
        query: Optional[str] = None,
        building_name: Optional[str] = None,
        services: Optional[List[str]] = None,
        accessible: bool = False
    ) -> List[CampusLocation]:
        """Search for campus locations by various criteria."""
        try:
            logger.info(f"Searching locations with query: {query}, services: {services}")
            
            # Build search parameters
            params = {}
            if query:
                params['q'] = query
            if building_name:
                params['building'] = building_name
            if services:
                params['services'] = ','.join(services)
            if accessible:
                params['accessible'] = 'true'
            
            # Make API request
            if params:
                response = self._make_request('GET', '/search', params=params)
            else:
                # If no specific criteria, get all locations and filter
                return self.get_all_locations()
            
            if response.headers.get('content-type', '').startswith('application/json'):
                data = response.json()
            else:
                raise DataParsingError("Expected JSON response from Places API")
            
            locations = []
            location_list = data if isinstance(data, list) else data.get('results', [])
            
            for item in location_list:
                location = self._parse_location_data(item)
                if location and self._matches_search_criteria(location, query, services, accessible):
                    locations.append(location)
            
            logger.info(f"Found {len(locations)} matching locations")
            return locations
            
        except Exception as e:
            logger.error(f"Error searching locations: {e}")
            raise DataParsingError(f"Failed to search locations: {e}")
    
    def get_location_by_id(self, building_id: str) -> Optional[CampusLocation]:
        """Get detailed information for a specific building/location."""
        if not building_id or not building_id.strip():
            raise ValidationError("building_id is required and cannot be empty")
        
        try:
            logger.info(f"Fetching location details for ID: {building_id}")
            
            response = self._make_request('GET', f'/locations/{building_id}')
            
            if response.headers.get('content-type', '').startswith('application/json'):
                data = response.json()
            else:
                raise DataParsingError("Expected JSON response from Places API")
            
            location = self._parse_location_data(data)
            
            if location:
                logger.info(f"Successfully retrieved location: {building_id}")
                return location
            else:
                logger.warning(f"No location found for ID: {building_id}")
                return None
                
        except Exception as e:
            logger.error(f"Error fetching location {building_id}: {e}")
            raise DataParsingError(f"Failed to fetch location {building_id}: {e}")
    
    def find_nearby_locations(
        self,
        center_location: CampusLocation,
        radius_meters: int = 500,
        services: Optional[List[str]] = None
    ) -> List[CampusLocation]:
        """Find locations near a given center point."""
        try:
            logger.info(f"Finding locations near {center_location.building_name}")
            
            if not center_location.gps_coordinates:
                logger.warning("Center location has no GPS coordinates")
                return []
            
            lat, lon = center_location.gps_coordinates
            
            params = {
                'lat': lat,
                'lon': lon,
                'radius': radius_meters
            }
            
            if services:
                params['services'] = ','.join(services)
            
            response = self._make_request('GET', '/nearby', params=params)
            
            if response.headers.get('content-type', '').startswith('application/json'):
                data = response.json()
            else:
                raise DataParsingError("Expected JSON response from Places API")
            
            locations = []
            location_list = data if isinstance(data, list) else data.get('results', [])
            
            for item in location_list:
                location = self._parse_location_data(item)
                if location:
                    locations.append(location)
            
            logger.info(f"Found {len(locations)} nearby locations")
            return locations
            
        except Exception as e:
            logger.error(f"Error finding nearby locations: {e}")
            raise DataParsingError(f"Failed to find nearby locations: {e}")
    
    def get_accessibility_info(self, building_id: str) -> Dict[str, Any]:
        """Get detailed accessibility information for a building."""
        try:
            logger.info(f"Fetching accessibility info for building: {building_id}")
            
            response = self._make_request('GET', f'/accessibility/{building_id}')
            
            if response.headers.get('content-type', '').startswith('application/json'):
                data = response.json()
            else:
                raise DataParsingError("Expected JSON response from Places API")
            
            # Structure accessibility information
            accessibility_info = {
                'building_id': building_id,
                'wheelchair_accessible': data.get('wheelchair_accessible', False),
                'accessible_entrances': data.get('accessible_entrances', []),
                'accessible_restrooms': data.get('accessible_restrooms', []),
                'elevator_access': data.get('elevator_access', False),
                'accessible_parking': data.get('accessible_parking', []),
                'assistance_services': data.get('assistance_services', []),
                'notes': data.get('accessibility_notes', '')
            }
            
            logger.info(f"Retrieved accessibility info for {building_id}")
            return accessibility_info
            
        except Exception as e:
            logger.error(f"Error fetching accessibility info: {e}")
            raise DataParsingError(f"Failed to fetch accessibility info: {e}")
    
    def _parse_location_data(self, data: Dict[str, Any]) -> Optional[CampusLocation]:
        """Parse location data from API response into CampusLocation object."""
        try:
            # Extract basic information
            building_id = data.get('id', data.get('building_id', ''))
            building_name = data.get('name', data.get('building_name', ''))
            address = data.get('address', '')
            
            if not building_id or not building_name:
                logger.warning(f"Incomplete location data: {data}")
                return None
            
            # Parse GPS coordinates
            gps_coordinates = None
            if 'lat' in data and 'lon' in data:
                try:
                    gps_coordinates = (float(data['lat']), float(data['lon']))
                except (ValueError, TypeError):
                    logger.warning(f"Invalid GPS coordinates in data: {data}")
            elif 'coordinates' in data:
                coords = data['coordinates']
                if isinstance(coords, list) and len(coords) >= 2:
                    try:
                        gps_coordinates = (float(coords[0]), float(coords[1]))
                    except (ValueError, TypeError):
                        logger.warning(f"Invalid coordinates format: {coords}")
            
            # Extract accessibility features
            accessibility_features = []
            if data.get('wheelchair_accessible'):
                accessibility_features.append('Wheelchair Accessible')
            if data.get('elevator_access'):
                accessibility_features.append('Elevator Access')
            if data.get('accessible_parking'):
                accessibility_features.append('Accessible Parking')
            
            # Extract available services
            available_services = data.get('services', [])
            if isinstance(available_services, str):
                available_services = [s.strip() for s in available_services.split(',')]
            
            # Extract operating hours
            operating_hours = data.get('hours', {})
            if isinstance(operating_hours, str):
                # If hours are provided as a string, create a simple structure
                operating_hours = {'general': operating_hours}
            
            # Extract capacity information
            capacity_info = data.get('capacity', {})
            if isinstance(capacity_info, int):
                capacity_info = {'total': capacity_info}
            
            return CampusLocation(
                building_id=building_id,
                building_name=building_name,
                address=address,
                gps_coordinates=gps_coordinates,
                accessibility_features=accessibility_features,
                available_services=available_services,
                operating_hours=operating_hours,
                capacity_info=capacity_info
            )
            
        except Exception as e:
            logger.error(f"Error parsing location data: {e}")
            return None
    
    def _matches_search_criteria(
        self,
        location: CampusLocation,
        query: Optional[str],
        services: Optional[List[str]],
        accessible: bool
    ) -> bool:
        """Check if a location matches the search criteria."""
        # Check query match
        if query:
            query_lower = query.lower()
            searchable_text = f"{location.building_name} {location.address}".lower()
            if query_lower not in searchable_text:
                return False
        
        # Check services match
        if services:
            location_services = [s.lower() for s in location.available_services]
            for required_service in services:
                if not any(required_service.lower() in service for service in location_services):
                    return False
        
        # Check accessibility requirement
        if accessible:
            accessibility_indicators = [
                'wheelchair accessible',
                'accessible',
                'elevator access'
            ]
            location_features = [f.lower() for f in location.accessibility_features]
            if not any(indicator in ' '.join(location_features) for indicator in accessibility_indicators):
                return False
        
        return True