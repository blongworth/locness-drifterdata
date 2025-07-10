"""
Tests for the SpotTrackerAPI class.
"""

import pytest
import requests
from datetime import datetime, timezone
from unittest.mock import Mock, patch
from drifterdata.spot_tracker import SpotTrackerAPI, SpotPosition


class TestSpotTrackerAPI:
    """Test suite for SpotTrackerAPI class."""

    @pytest.fixture
    def api(self):
        """Create a SpotTrackerAPI instance for testing."""
        return SpotTrackerAPI(feed_id="test_feed_id")

    @pytest.fixture
    def mock_response_data(self):
        """Mock response data from SPOT API."""
        return {
            "response": {
                "feedMessageResponse": {
                    "count": 2,
                    "messages": {
                        "message": [
                            {
                                "id": 123456,
                                "messengerName": "Test Tracker",
                                "dateTime": "2025-07-10T12:00:00+0000",
                                "latitude": 40.7128,
                                "longitude": -74.0060,
                                "altitude": 10.5,
                                "messageType": "OK",
                                "batteryState": "GOOD"
                            },
                            {
                                "id": 123457,
                                "messengerName": "Test Tracker",
                                "dateTime": "2025-07-10T11:00:00+0000",
                                "latitude": 40.7129,
                                "longitude": -74.0061,
                                "altitude": 9.8,
                                "messageType": "OK",
                                "batteryState": "GOOD"
                            }
                        ]
                    }
                }
            }
        }

    @pytest.fixture
    def mock_single_message_response(self):
        """Mock response data with single message."""
        return {
            "response": {
                "feedMessageResponse": {
                    "count": 1,
                    "messages": {
                        "message": {
                            "id": 123456,
                            "messengerName": "Test Tracker",
                            "dateTime": "2025-07-10T12:00:00+0000",
                            "latitude": 40.7128,
                            "longitude": -74.0060,
                            "altitude": 10.5,
                            "messageType": "OK",
                            "batteryState": "GOOD"
                        }
                    }
                }
            }
        }

    @pytest.fixture
    def mock_empty_response(self):
        """Mock empty response from SPOT API."""
        return {
            "response": {
                "feedMessageResponse": {
                    "count": 0,
                    "messages": {}
                }
            }
        }

    def test_init_with_feed_id(self):
        """Test initialization with feed ID."""
        api = SpotTrackerAPI(feed_id="test_feed")
        assert api.feed_id == "test_feed"
        assert api.base_url == "https://api.findmespot.com/spot-main-web/consumer/rest-api/2.0/public/feed"

    def test_init_without_feed_id(self):
        """Test initialization without feed ID raises ValueError."""
        with patch.dict('os.environ', {}, clear=True):
            with pytest.raises(ValueError, match="SPOT feed ID is required"):
                SpotTrackerAPI()

    def test_init_with_env_var(self):
        """Test initialization with environment variable."""
        with patch.dict('os.environ', {'SPOT_FEED_ID': 'env_feed_id'}):
            api = SpotTrackerAPI()
            assert api.feed_id == "env_feed_id"

    @patch('drifterdata.spot_tracker.requests.Session.get')
    def test_get_latest_position_success(self, mock_get, api, mock_single_message_response):
        """Test successful get_latest_position call."""
        mock_response = Mock()
        mock_response.json.return_value = mock_single_message_response
        mock_response.raise_for_status.return_value = None
        mock_get.return_value = mock_response

        position = api.get_latest_position()

        assert position is not None
        assert isinstance(position, SpotPosition)
        assert position.asset_id == "Test Tracker"
        assert position.latitude == 40.7128
        assert position.longitude == -74.0060
        assert position.altitude == 10.5
        assert position.message_type == "OK"
        assert position.battery_state == "GOOD"

        mock_get.assert_called_once_with(
            f"{api.base_url}/{api.feed_id}/latest.json",
            params={},
            timeout=30
        )

    @patch('drifterdata.spot_tracker.requests.Session.get')
    def test_get_latest_position_with_password(self, mock_get, api, mock_single_message_response):
        """Test get_latest_position with password."""
        mock_response = Mock()
        mock_response.json.return_value = mock_single_message_response
        mock_response.raise_for_status.return_value = None
        mock_get.return_value = mock_response

        api.get_latest_position(feed_password="test_password")

        assert mock_get.call_count == 1
        mock_get.assert_called_with(
            f"{api.base_url}/{api.feed_id}/latest.json",
            params={"feedPassword": "test_password"},
            timeout=30
        )

    @patch('drifterdata.spot_tracker.requests.Session.get')
    def test_get_latest_position_empty_response(self, mock_get, api, mock_empty_response):
        """Test get_latest_position with empty response."""
        mock_response = Mock()
        mock_response.json.return_value = mock_empty_response
        mock_response.raise_for_status.return_value = None
        mock_get.return_value = mock_response

        position = api.get_latest_position()

        assert position is None

    @patch('drifterdata.spot_tracker.requests.Session.get')
    def test_get_messages_success(self, mock_get, api, mock_response_data):
        """Test successful get_messages call."""
        mock_response = Mock()
        mock_response.json.return_value = mock_response_data
        mock_response.raise_for_status.return_value = None
        mock_get.return_value = mock_response

        positions = api.get_messages()

        assert len(positions) == 2
        assert all(isinstance(pos, SpotPosition) for pos in positions)
        assert positions[0].asset_id == "Test Tracker"
        assert positions[0].latitude == 40.7128

        mock_get.assert_called_once_with(
            f"{api.base_url}/{api.feed_id}/message.json",
            params={},
            timeout=30
        )

    @patch('drifterdata.spot_tracker.requests.Session.get')
    def test_get_messages_with_pagination(self, mock_get, api, mock_response_data):
        """Test get_messages with pagination."""
        mock_response = Mock()
        mock_response.json.return_value = mock_response_data
        mock_response.raise_for_status.return_value = None
        mock_get.return_value = mock_response

        api.get_messages(start=51)

        mock_get.assert_called_once_with(
            f"{api.base_url}/{api.feed_id}/message.json",
            params={"start": 51},
            timeout=30
        )

    @patch('drifterdata.spot_tracker.requests.Session.get')
    def test_get_messages_with_count_limit(self, mock_get, api, mock_response_data):
        """Test get_messages with count limit."""
        mock_response = Mock()
        mock_response.json.return_value = mock_response_data
        mock_response.raise_for_status.return_value = None
        mock_get.return_value = mock_response

        positions = api.get_messages(count=1)

        assert len(positions) == 1

    @patch('drifterdata.spot_tracker.requests.Session.get')
    def test_get_messages_by_date_range(self, mock_get, api, mock_response_data):
        """Test get_messages_by_date_range."""
        mock_response = Mock()
        mock_response.json.return_value = mock_response_data
        mock_response.raise_for_status.return_value = None
        mock_get.return_value = mock_response

        start_date = datetime(2025, 7, 8, 12, 0, 0, tzinfo=timezone.utc)
        end_date = datetime(2025, 7, 10, 12, 0, 0, tzinfo=timezone.utc)

        positions = api.get_messages_by_date_range(start_date, end_date)

        assert len(positions) == 2

        expected_params = {
            "startDate": "2025-07-08T12:00:00-0000",
            "endDate": "2025-07-10T12:00:00-0000"
        }
        mock_get.assert_called_once_with(
            f"{api.base_url}/{api.feed_id}/message.json",
            params=expected_params,
            timeout=30
        )

    @patch('drifterdata.spot_tracker.requests.Session.get')
    def test_get_messages_by_date_range_with_password(self, mock_get, api, mock_response_data):
        """Test get_messages_by_date_range with password."""
        mock_response = Mock()
        mock_response.json.return_value = mock_response_data
        mock_response.raise_for_status.return_value = None
        mock_get.return_value = mock_response

        start_date = datetime(2025, 7, 8, 12, 0, 0, tzinfo=timezone.utc)
        end_date = datetime(2025, 7, 10, 12, 0, 0, tzinfo=timezone.utc)

        api.get_messages_by_date_range(start_date, end_date, feed_password="test_password")

        expected_params = {
            "startDate": "2025-07-08T12:00:00-0000",
            "endDate": "2025-07-10T12:00:00-0000",
            "feedPassword": "test_password"
        }
        mock_get.assert_called_once_with(
            f"{api.base_url}/{api.feed_id}/message.json",
            params=expected_params,
            timeout=30
        )

    @patch('drifterdata.spot_tracker.requests.Session.get')
    def test_get_latest_positions_deprecated(self, mock_get, api, mock_response_data):
        """Test deprecated get_latest_positions method."""
        mock_response = Mock()
        mock_response.json.return_value = mock_response_data
        mock_response.raise_for_status.return_value = None
        mock_get.return_value = mock_response

        # The deprecation warning is logged, not raised as a warning
        with patch('drifterdata.spot_tracker.logger.warning') as mock_warning:
            positions = api.get_latest_positions()
            
            # Check that warning was logged
            mock_warning.assert_called_once_with(
                "get_latest_positions() is deprecated. Use get_messages() or get_messages_by_date_range() instead."
            )

        assert len(positions) == 2

    @patch('drifterdata.spot_tracker.requests.Session.get')
    def test_request_exception_handling(self, mock_get, api):
        """Test handling of request exceptions."""
        mock_get.side_effect = requests.exceptions.RequestException("Connection error")

        with pytest.raises(requests.exceptions.RequestException):
            api.get_latest_position()

    @patch('drifterdata.spot_tracker.requests.Session.get')
    def test_http_error_handling(self, mock_get, api):
        """Test handling of HTTP errors."""
        mock_response = Mock()
        mock_response.raise_for_status.side_effect = requests.exceptions.HTTPError("404 Not Found")
        mock_get.return_value = mock_response

        with pytest.raises(requests.exceptions.HTTPError):
            api.get_latest_position()

    @patch('drifterdata.spot_tracker.requests.Session.get')
    def test_json_decode_error_handling(self, mock_get, api):
        """Test handling of JSON decode errors."""
        mock_response = Mock()
        mock_response.raise_for_status.return_value = None
        mock_response.json.side_effect = ValueError("Invalid JSON")
        mock_get.return_value = mock_response

        with pytest.raises(ValueError):
            api.get_latest_position()

    def test_parse_message_success(self, api):
        """Test successful message parsing."""
        message = {
            "messengerName": "Test Tracker",
            "dateTime": "2025-07-10T12:00:00+0000",
            "latitude": 40.7128,
            "longitude": -74.0060,
            "altitude": 10.5,
            "messageType": "OK",
            "batteryState": "GOOD"
        }

        position = api._parse_message(message)

        assert position is not None
        assert position.asset_id == "Test Tracker"
        assert position.latitude == 40.7128
        assert position.longitude == -74.0060
        assert position.altitude == 10.5
        assert position.message_type == "OK"
        assert position.battery_state == "GOOD"

    def test_parse_message_missing_coordinates(self, api):
        """Test parsing message with missing coordinates."""
        message = {
            "messengerName": "Test Tracker",
            "dateTime": "2025-07-10T12:00:00+0000"
            # Missing latitude/longitude
        }

        position = api._parse_message(message)

        assert position is None

    def test_parse_message_missing_timestamp(self, api):
        """Test parsing message with missing timestamp."""
        message = {
            "messengerName": "Test Tracker",
            "latitude": 40.7128,
            "longitude": -74.0060
            # Missing dateTime
        }

        position = api._parse_message(message)

        assert position is None

    def test_parse_message_with_unix_timestamp(self, api):
        """Test parsing message with Unix timestamp."""
        message = {
            "messengerName": "Test Tracker",
            "unixTime": 1720612800,  # 2024-07-10 12:00:00 UTC
            "latitude": 40.7128,
            "longitude": -74.0060
        }

        position = api._parse_message(message)

        assert position is not None
        assert position.timestamp.year == 2024
        assert position.timestamp.month == 7
        assert position.timestamp.day == 10

    @patch('drifterdata.spot_tracker.SpotTrackerAPI.get_latest_position')
    @patch('drifterdata.spot_tracker.SpotTrackerAPI.get_messages')
    def test_connection_test_success_with_latest(self, mock_get_messages, mock_get_latest, api):
        """Test successful connection test with latest position."""
        mock_position = Mock()
        mock_get_latest.return_value = mock_position

        result = api.test_connection()

        assert result is True
        mock_get_latest.assert_called_once()
        mock_get_messages.assert_not_called()

    @patch('drifterdata.spot_tracker.SpotTrackerAPI.get_latest_position')
    @patch('drifterdata.spot_tracker.SpotTrackerAPI.get_messages')
    def test_connection_test_success_with_messages(self, mock_get_messages, mock_get_latest, api):
        """Test successful connection test with messages."""
        mock_get_latest.return_value = None
        mock_get_messages.return_value = [Mock(), Mock()]

        result = api.test_connection()

        assert result is True
        mock_get_latest.assert_called_once()
        mock_get_messages.assert_called_once()

    @patch('drifterdata.spot_tracker.SpotTrackerAPI.get_latest_position')
    def test_connection_test_failure(self, mock_get_latest, api):
        """Test connection test failure."""
        mock_get_latest.side_effect = Exception("Connection error")

        result = api.test_connection()

        assert result is False
