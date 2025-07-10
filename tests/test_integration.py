"""
Integration tests for the SPOT API functionality.

These tests can be run against the real SPOT API if environment variables are set,
or they will be skipped if no credentials are available.
"""

import os
import pytest
from datetime import datetime, timezone, timedelta
from drifterdata.spot_tracker import SpotTrackerAPI


class TestSpotTrackerAPIIntegration:
    """Integration test suite for SpotTrackerAPI."""

    @pytest.fixture
    def real_api(self):
        """Create a real API instance if credentials are available."""
        feed_id = os.getenv('SPOT_FEED_ID')
        if not feed_id or feed_id == 'test_feed_id':
            pytest.skip("No real SPOT_FEED_ID provided for integration tests")
        
        return SpotTrackerAPI(feed_id=feed_id)

    @pytest.fixture
    def feed_password(self):
        """Get feed password from environment if available."""
        return os.getenv('SPOT_FEED_PASSWORD')

    @pytest.mark.integration
    def test_real_connection(self, real_api):
        """Test connection to real SPOT API."""
        result = real_api.test_connection()
        assert result is True

    @pytest.mark.integration
    def test_real_get_latest_position(self, real_api, feed_password):
        """Test getting latest position from real SPOT API."""
        position = real_api.get_latest_position(feed_password=feed_password)
        
        # Position might be None if no recent data
        if position:
            assert position.asset_id is not None
            assert isinstance(position.latitude, float)
            assert isinstance(position.longitude, float)
            assert -90 <= position.latitude <= 90
            assert -180 <= position.longitude <= 180
            assert isinstance(position.timestamp, datetime)

    @pytest.mark.integration
    def test_real_get_messages(self, real_api, feed_password):
        """Test getting messages from real SPOT API."""
        messages = real_api.get_messages(feed_password=feed_password)
        
        # Messages might be empty if no recent data
        assert isinstance(messages, list)
        
        for message in messages:
            assert message.asset_id is not None
            assert isinstance(message.latitude, float)
            assert isinstance(message.longitude, float)
            assert -90 <= message.latitude <= 90
            assert -180 <= message.longitude <= 180
            assert isinstance(message.timestamp, datetime)

    @pytest.mark.integration
    def test_real_get_messages_by_date_range(self, real_api, feed_password):
        """Test getting messages by date range from real SPOT API."""
        end_date = datetime.now(timezone.utc)
        start_date = end_date - timedelta(days=2)  # Last 2 days
        
        messages = real_api.get_messages_by_date_range(
            start_date, end_date, feed_password=feed_password
        )
        
        # Messages might be empty if no data in range
        assert isinstance(messages, list)
        
        for message in messages:
            assert message.asset_id is not None
            assert isinstance(message.latitude, float)
            assert isinstance(message.longitude, float)
            assert isinstance(message.timestamp, datetime)
            # Check that messages are within the requested range
            assert start_date <= message.timestamp <= end_date

    @pytest.mark.integration
    def test_real_pagination(self, real_api, feed_password):
        """Test pagination with real SPOT API."""
        # Get first page
        first_page = real_api.get_messages(feed_password=feed_password)
        
        # Get second page (if there are enough messages)
        second_page = real_api.get_messages(start=51, feed_password=feed_password)
        
        # Both should be lists
        assert isinstance(first_page, list)
        assert isinstance(second_page, list)
        
        # If both pages have data, they should be different
        if first_page and second_page:
            first_ids = {msg.timestamp for msg in first_page}
            second_ids = {msg.timestamp for msg in second_page}
            # There should be no overlap in timestamps between pages
            assert not first_ids.intersection(second_ids)

    @pytest.mark.integration
    def test_real_invalid_feed_password(self, real_api):
        """Test with invalid feed password."""
        # This should not raise an exception for public feeds
        # but might return empty results for password-protected feeds
        try:
            messages = real_api.get_messages(feed_password="invalid_password")
            assert isinstance(messages, list)
        except Exception:
            # Some feeds might return errors for invalid passwords
            pass

    @pytest.mark.integration
    def test_real_date_range_too_large(self, real_api, feed_password):
        """Test date range larger than 7 days (should still work but limited by API)."""
        end_date = datetime.now(timezone.utc)
        start_date = end_date - timedelta(days=10)  # 10 days - exceeds 7-day limit
        
        # Should not raise an exception, but API will limit to 7 days
        messages = real_api.get_messages_by_date_range(
            start_date, end_date, feed_password=feed_password
        )
        
        assert isinstance(messages, list)

    @pytest.mark.integration
    def test_real_deprecated_method(self, real_api):
        """Test deprecated get_latest_positions method with real API."""
        with pytest.warns(UserWarning, match="get_latest_positions\\(\\) is deprecated"):
            positions = real_api.get_latest_positions()
        
        assert isinstance(positions, list)


# Utility function to run integration tests
def run_integration_tests():
    """
    Run integration tests against real SPOT API.
    
    Set the following environment variables:
    - SPOT_FEED_ID: Your real SPOT feed ID
    - SPOT_FEED_PASSWORD: Your feed password (if required)
    
    Then run: pytest -m integration
    """
    import subprocess
    import sys
    
    result = subprocess.run([
        sys.executable, "-m", "pytest", "-m", "integration", "-v"
    ])
    return result.returncode


if __name__ == "__main__":
    exit_code = run_integration_tests()
    exit(exit_code)
