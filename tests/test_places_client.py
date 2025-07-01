"""Tests for the Places client functionality."""

import pytest
from unittest.mock import Mock, patch, MagicMock
from datetime import datetime

from gtmcp.clients.places_client import PlacesClient
from gtmcp.clients.base_client import NetworkError, DataParsingError, ValidationError
from gtmcp.models import CampusLocation, RouteOptimization


class TestPlacesClientInit:
    """Test PlacesClient initialization."""
    
    def test_init_with_defaults(self):
        """Test initialization with default values."""
        client = PlacesClient()
        
        assert client.base_url == "https://gis.gatech.edu"
        assert client.search_url == "https://gis.gatech.edu/search/building"
        assert client.accessibility_url == "https://gis.gatech.edu/accessibility"


class TestPlacesClientConnection:
    """Test Places client connection functionality."""
    
    @patch('gtmcp.clients.places_client.PlacesClient._make_request')
    def test_connection_success(self, mock_request):
        """Test successful connection to Places API."""
        mock_response = Mock()
        mock_response.text = "GT Campus Map"
        mock_request.return_value = mock_response
        
        client = PlacesClient()
        
        with client:
            result = client.test_connection()
        
        assert result is True
    
    @patch('gtmcp.clients.places_client.PlacesClient._make_request')
    def test_connection_failure(self, mock_request):
        """Test failed connection to Places API."""
        mock_request.side_effect = Exception("Connection failed")
        
        client = PlacesClient()
        
        with client:
            result = client.test_connection()
        
        assert result is False


class TestPlacesClientBuildingSearch:
    """Test building search functionality."""
    
    @patch('gtmcp.clients.places_client.PlacesClient._make_request')
    def test_search_buildings_success(self, mock_request):
        """Test successful building search."""
        mock_data = {
            'buildings': [
                {
                    'name': 'Klaus Advanced Computing Building',
                    'code': 'KLAUS',
                    'address': '266 Ferst Dr NW, Atlanta, GA 30332',
                    'coordinates': {'lat': 33.777, 'lng': -84.396},
                    'accessibility': {
                        'wheelchair_accessible': True,
                        'elevator_access': True,
                        'accessible_parking': True
                    },
                    'amenities': ['Computer Labs', 'Study Rooms', 'Food Court']
                },
                {
                    'name': 'Student Center',
                    'code': 'STUC',
                    'address': '350 Ferst Dr NW, Atlanta, GA 30332',
                    'coordinates': {'lat': 33.774, 'lng': -84.398},
                    'accessibility': {
                        'wheelchair_accessible': True,
                        'elevator_access': True,
                        'accessible_parking': True
                    },
                    'amenities': ['Dining', 'Bookstore', 'Meeting Rooms']
                }
            ]
        }
        
        mock_response = Mock()
        mock_response.json.return_value = mock_data
        mock_request.return_value = mock_response
        
        client = PlacesClient()
        
        with client:
            buildings = client.search_buildings("Klaus")
        
        assert len(buildings) == 2
        assert buildings[0].name == "Klaus Advanced Computing Building"
        assert buildings[0].building_code == "KLAUS" 
        assert buildings[0].latitude == 33.777
        assert buildings[0].longitude == -84.396
        assert buildings[0].wheelchair_accessible is True
        assert "Computer Labs" in buildings[0].amenities
    
    @patch('gtmcp.clients.places_client.PlacesClient._make_request')
    def test_search_buildings_no_results(self, mock_request):
        """Test building search with no results."""
        mock_response = Mock()
        mock_response.json.return_value = {'buildings': []}
        mock_request.return_value = mock_response
        
        client = PlacesClient()
        
        with client:
            buildings = client.search_buildings("NonexistentBuilding")
        
        assert buildings == []
    
    def test_search_buildings_empty_query(self):
        """Test building search with empty query."""
        client = PlacesClient()
        
        with pytest.raises(ValidationError, match="query is required"):
            with client:
                client.search_buildings("")


class TestPlacesClientBuildingDetails:
    """Test building details functionality."""
    
    @patch('gtmcp.clients.places_client.PlacesClient._make_request')
    def test_get_building_details_success(self, mock_request):
        """Test successful building details retrieval."""
        mock_data = {
            'building': {
                'name': 'Klaus Advanced Computing Building',
                'code': 'KLAUS',
                'address': '266 Ferst Dr NW, Atlanta, GA 30332',
                'coordinates': {'lat': 33.777, 'lng': -84.396},
                'accessibility': {
                    'wheelchair_accessible': True,
                    'elevator_access': True,
                    'accessible_parking': True,
                    'braille_signage': True,
                    'accessible_restrooms': True
                },
                'amenities': ['Computer Labs', 'Study Rooms', 'Food Court', 'WiFi'],
                'hours': {
                    'monday': '7:00 AM - 11:00 PM',
                    'tuesday': '7:00 AM - 11:00 PM',
                    'weekend': '9:00 AM - 9:00 PM'
                },
                'departments': ['Computer Science', 'Computational Science and Engineering'],
                'parking': ['Visitor Parking Available', 'Handicap Accessible Spaces']
            }
        }
        
        mock_response = Mock()
        mock_response.json.return_value = mock_data
        mock_request.return_value = mock_response
        
        client = PlacesClient()
        
        with client:
            building = client.get_building_details("KLAUS")
        
        assert building.name == "Klaus Advanced Computing Building"
        assert building.building_code == "KLAUS"
        assert building.address == "266 Ferst Dr NW, Atlanta, GA 30332" 
        assert building.latitude == 33.777
        assert building.longitude == -84.396
        assert building.wheelchair_accessible is True
        assert building.elevator_access is True
        assert "Computer Labs" in building.amenities
        assert "Computer Science" in building.departments
    
    def test_get_building_details_empty_code(self):
        """Test building details with empty building code."""
        client = PlacesClient()
        
        with pytest.raises(ValidationError, match="building_code is required"):
            with client:
                client.get_building_details("")


class TestPlacesClientAccessibility:
    """Test accessibility features."""
    
    @patch('gtmcp.clients.places_client.PlacesClient._make_request')
    def test_find_accessible_buildings_success(self, mock_request):
        """Test successful accessible building search."""
        mock_data = {
            'accessible_buildings': [
                {
                    'name': 'Student Center',
                    'code': 'STUC',
                    'accessibility_score': 95,
                    'features': ['Wheelchair Accessible', 'Elevator Access', 'Accessible Parking'],
                    'coordinates': {'lat': 33.774, 'lng': -84.398}
                },
                {
                    'name': 'Library West',
                    'code': 'LIBW',
                    'accessibility_score': 92,
                    'features': ['Wheelchair Accessible', 'Braille Signage', 'Audio Assistance'],
                    'coordinates': {'lat': 33.776, 'lng': -84.396}
                }
            ]
        }
        
        mock_response = Mock()
        mock_response.json.return_value = mock_data
        mock_request.return_value = mock_response
        
        client = PlacesClient()
        
        with client:
            buildings = client.find_accessible_buildings()
        
        assert len(buildings) == 2
        assert buildings[0].name == "Student Center"
        assert buildings[0].wheelchair_accessible is True
        assert buildings[0].elevator_access is True
    
    @patch('gtmcp.clients.places_client.PlacesClient._make_request')
    def test_find_accessible_buildings_with_filters(self, mock_request):
        """Test accessible building search with specific accessibility needs."""
        mock_response = Mock()
        mock_response.json.return_value = {'accessible_buildings': []}
        mock_request.return_value = mock_response
        
        client = PlacesClient()
        
        with client:
            buildings = client.find_accessible_buildings(
                wheelchair_access=True,
                elevator_access=True,
                accessible_parking=True
            )
        
        assert buildings == []
        # Verify request was made with filters
        mock_request.assert_called_once()


class TestPlacesClientRouteOptimization:
    """Test route optimization functionality."""
    
    @patch('gtmcp.clients.places_client.PlacesClient._make_request')
    def test_optimize_route_success(self, mock_request):
        """Test successful route optimization."""
        mock_data = {
            'route': {
                'waypoints': ['KLAUS', 'STUC', 'LIBW'],
                'total_distance': 0.8,
                'estimated_time': 12,
                'accessibility_rating': 'fully_accessible',
                'instructions': [
                    'Start at Klaus Advanced Computing Building',
                    'Walk east on Ferst Drive for 0.3 miles',
                    'Arrive at Student Center',
                    'Continue north for 0.2 miles',
                    'Arrive at Library West'
                ],
                'elevation_changes': [
                    {'point': 'KLAUS', 'elevation': 320},
                    {'point': 'STUC', 'elevation': 315},
                    {'point': 'LIBW', 'elevation': 325}
                ]
            }
        }
        
        mock_response = Mock()
        mock_response.json.return_value = mock_data
        mock_request.return_value = mock_response
        
        client = PlacesClient()
        
        with client:
            route = client.optimize_route(['KLAUS', 'STUC', 'LIBW'])
        
        assert route.waypoints == ['KLAUS', 'STUC', 'LIBW']
        assert route.total_distance_miles == 0.8
        assert route.estimated_time_minutes == 12
        assert route.accessibility_rating == 'fully_accessible'
        assert len(route.step_by_step_directions) == 5
    
    def test_optimize_route_empty_locations(self):
        """Test route optimization with empty locations."""
        client = PlacesClient()
        
        with pytest.raises(ValidationError, match="At least 2 locations required"):
            with client:
                client.optimize_route([])
    
    def test_optimize_route_single_location(self):
        """Test route optimization with single location."""
        client = PlacesClient()
        
        with pytest.raises(ValidationError, match="At least 2 locations required"):
            with client:
                client.optimize_route(['KLAUS'])


class TestPlacesClientUtilities:
    """Test utility methods."""
    
    def test_calculate_distance(self):
        """Test distance calculation between coordinates."""
        client = PlacesClient()
        
        with client:
            # Klaus to Student Center (approximate)
            distance = client._calculate_distance(33.777, -84.396, 33.774, -84.398)
        
        # Should be approximately 0.25 miles
        assert 0.2 < distance < 0.3
    
    def test_format_accessibility_features(self):
        """Test accessibility features formatting."""
        client = PlacesClient()
        
        features = {
            'wheelchair_accessible': True,
            'elevator_access': True,
            'accessible_parking': False,
            'braille_signage': True,
            'accessible_restrooms': True
        }
        
        with client:
            formatted = client._format_accessibility_features(features)
        
        assert 'Wheelchair Accessible' in formatted
        assert 'Elevator Access' in formatted
        assert 'Braille Signage' in formatted
        assert 'Accessible Restrooms' in formatted
        # Should not include features that are False
        assert 'Accessible Parking' not in formatted
    
    def test_validate_building_code(self):
        """Test building code validation."""
        client = PlacesClient()
        
        with client:
            # Valid building codes
            assert client._validate_building_code('KLAUS') is True
            assert client._validate_building_code('STUC') is True
            assert client._validate_building_code('LIBW') is True
            
            # Invalid building codes
            assert client._validate_building_code('') is False
            assert client._validate_building_code(None) is False
            assert client._validate_building_code('invalid123') is False


class TestPlacesClientErrorHandling:
    """Test error handling scenarios."""
    
    @patch('gtmcp.clients.places_client.PlacesClient._make_request')
    def test_search_buildings_api_error(self, mock_request):
        """Test building search when API returns error."""
        mock_request.side_effect = NetworkError("API unavailable")
        
        client = PlacesClient()
        
        with client:
            with pytest.raises(NetworkError):
                client.search_buildings("Klaus")
    
    @patch('gtmcp.clients.places_client.PlacesClient._make_request')
    def test_get_building_details_not_found(self, mock_request):
        """Test building details when building not found."""
        mock_response = Mock()
        mock_response.json.return_value = {'error': 'Building not found'}
        mock_request.return_value = mock_response
        
        client = PlacesClient()
        
        with client:
            with pytest.raises(DataParsingError, match="Building not found"):
                client.get_building_details("INVALID")
    
    @patch('gtmcp.clients.places_client.PlacesClient._make_request')
    def test_optimize_route_invalid_location(self, mock_request):
        """Test route optimization with invalid location."""
        mock_response = Mock()
        mock_response.json.return_value = {'error': 'Invalid location: INVALID'}
        mock_request.return_value = mock_response
        
        client = PlacesClient()
        
        with client:
            with pytest.raises(DataParsingError, match="Invalid location"):
                client.optimize_route(['KLAUS', 'INVALID'])