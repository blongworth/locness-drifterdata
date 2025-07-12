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

    @pytest.mark.integration
    def test_real_connection(self, real_api):
        """Test connection to real SPOT API."""
        result = real_api.test_connection()
        assert result is True

    @pytest.mark.integration
    def test_real_get_latest_position(self, real_api):
        """Test getting latest position from real SPOT API."""
        position = real_api.get_latest_position()
        
        # Position might be None if no recent data
        if position:
            assert position.asset_id is not None
            assert isinstance(position.latitude, float)
            assert isinstance(position.longitude, float)
            assert -90 <= position.latitude <= 90
            assert -180 <= position.longitude <= 180
            assert isinstance(position.timestamp, datetime)

    @pytest.mark.integration
    def test_real_get_messages(self, real_api):
        """Test getting messages from real SPOT API."""
        messages = real_api.get_messages()
        
        # Messages might be empty if no recent data
        assert isinstance(messages, list)
        
        for message in messages:
            assert message.asset_id is not None
            assert isinstance(message.latitude, float)
            assert isinstance(message.longitude, float)
            assert -90 <= message.latitude <= 90
            assert -180 <= message.longitude <= 180
            assert isinstance(message.timestamp, datetime)


# Utility function to run integration tests
def run_integration_tests():
    """
    Run integration tests against real SPOT API.
    
    Set the following environment variables:
    - SPOT_FEED_ID: Your real SPOT feed ID
    
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
