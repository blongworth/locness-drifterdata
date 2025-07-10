"""
Tests for the SpotPosition model.
"""

import pytest
from datetime import datetime, timezone
from pydantic import ValidationError
from drifterdata.spot_tracker import SpotPosition


class TestSpotPosition:
    """Test suite for SpotPosition model."""

    def test_create_spot_position_success(self):
        """Test creating a SpotPosition with valid data."""
        position = SpotPosition(
            asset_id="Test Tracker",
            timestamp=datetime(2025, 7, 10, 12, 0, 0, tzinfo=timezone.utc),
            latitude=40.7128,
            longitude=-74.0060,
            altitude=10.5,
            message_type="OK",
            battery_state="GOOD"
        )

        assert position.asset_id == "Test Tracker"
        assert position.latitude == 40.7128
        assert position.longitude == -74.0060
        assert position.altitude == 10.5
        assert position.message_type == "OK"
        assert position.battery_state == "GOOD"

    def test_create_spot_position_minimal(self):
        """Test creating a SpotPosition with minimal required data."""
        position = SpotPosition(
            asset_id="Test Tracker",
            timestamp=datetime(2025, 7, 10, 12, 0, 0, tzinfo=timezone.utc),
            latitude=40.7128,
            longitude=-74.0060
        )

        assert position.asset_id == "Test Tracker"
        assert position.latitude == 40.7128
        assert position.longitude == -74.0060
        assert position.altitude is None
        assert position.message_type is None
        assert position.battery_state is None

    def test_parse_iso_timestamp_string(self):
        """Test parsing ISO format timestamp string."""
        position = SpotPosition(
            asset_id="Test Tracker",
            timestamp="2025-07-10T12:00:00Z",
            latitude=40.7128,
            longitude=-74.0060
        )

        assert position.timestamp.year == 2025
        assert position.timestamp.month == 7
        assert position.timestamp.day == 10
        assert position.timestamp.hour == 12
        assert position.timestamp.tzinfo == timezone.utc

    def test_parse_iso_timestamp_with_offset(self):
        """Test parsing ISO format timestamp with offset."""
        position = SpotPosition(
            asset_id="Test Tracker",
            timestamp="2025-07-10T12:00:00+00:00",
            latitude=40.7128,
            longitude=-74.0060
        )

        assert position.timestamp.year == 2025
        assert position.timestamp.month == 7
        assert position.timestamp.day == 10
        assert position.timestamp.hour == 12
        assert position.timestamp.tzinfo == timezone.utc

    def test_parse_unix_timestamp_int(self):
        """Test parsing Unix timestamp as integer."""
        position = SpotPosition(
            asset_id="Test Tracker",
            timestamp=1720612800,  # 2024-07-10 12:00:00 UTC
            latitude=40.7128,
            longitude=-74.0060
        )

        assert position.timestamp.year == 2024
        assert position.timestamp.month == 7
        assert position.timestamp.day == 10
        assert position.timestamp.hour == 12
        assert position.timestamp.tzinfo == timezone.utc

    def test_parse_unix_timestamp_float(self):
        """Test parsing Unix timestamp as float."""
        position = SpotPosition(
            asset_id="Test Tracker",
            timestamp=1720612800.5,  # 2024-07-10 12:00:00.5 UTC
            latitude=40.7128,
            longitude=-74.0060
        )

        assert position.timestamp.year == 2024
        assert position.timestamp.month == 7
        assert position.timestamp.day == 10
        assert position.timestamp.hour == 12
        assert position.timestamp.microsecond == 500000

    def test_parse_timestamp_without_timezone(self):
        """Test parsing timestamp string without timezone."""
        position = SpotPosition(
            asset_id="Test Tracker",
            timestamp="2025-07-10T12:00:00",
            latitude=40.7128,
            longitude=-74.0060
        )

        assert position.timestamp.year == 2025
        assert position.timestamp.month == 7
        assert position.timestamp.day == 10
        assert position.timestamp.hour == 12
        assert position.timestamp.tzinfo == timezone.utc

    def test_parse_timestamp_space_format(self):
        """Test parsing timestamp with space separator."""
        position = SpotPosition(
            asset_id="Test Tracker",
            timestamp="2025-07-10 12:00:00",
            latitude=40.7128,
            longitude=-74.0060
        )

        assert position.timestamp.year == 2025
        assert position.timestamp.month == 7
        assert position.timestamp.day == 10
        assert position.timestamp.hour == 12
        assert position.timestamp.tzinfo == timezone.utc

    def test_parse_invalid_timestamp(self):
        """Test parsing invalid timestamp raises ValidationError."""
        with pytest.raises(ValidationError):
            SpotPosition(
                asset_id="Test Tracker",
                timestamp="invalid-timestamp",
                latitude=40.7128,
                longitude=-74.0060
            )

    def test_datetime_object_timestamp(self):
        """Test passing datetime object as timestamp."""
        dt = datetime(2025, 7, 10, 12, 0, 0, tzinfo=timezone.utc)
        position = SpotPosition(
            asset_id="Test Tracker",
            timestamp=dt,
            latitude=40.7128,
            longitude=-74.0060
        )

        assert position.timestamp == dt

    def test_required_fields_validation(self):
        """Test that required fields are validated."""
        # Missing asset_id
        with pytest.raises(ValidationError):
            SpotPosition(
                timestamp=datetime.now(timezone.utc),
                latitude=40.7128,
                longitude=-74.0060
            )

        # Missing timestamp
        with pytest.raises(ValidationError):
            SpotPosition(
                asset_id="Test Tracker",
                latitude=40.7128,
                longitude=-74.0060
            )

        # Missing latitude
        with pytest.raises(ValidationError):
            SpotPosition(
                asset_id="Test Tracker",
                timestamp=datetime.now(timezone.utc),
                longitude=-74.0060
            )

        # Missing longitude
        with pytest.raises(ValidationError):
            SpotPosition(
                asset_id="Test Tracker",
                timestamp=datetime.now(timezone.utc),
                latitude=40.7128
            )

    def test_coordinate_types(self):
        """Test that coordinates are properly converted to float."""
        position = SpotPosition(
            asset_id="Test Tracker",
            timestamp=datetime.now(timezone.utc),
            latitude="40.7128",  # String
            longitude="-74.0060"  # String
        )

        assert isinstance(position.latitude, float)
        assert isinstance(position.longitude, float)
        assert position.latitude == 40.7128
        assert position.longitude == -74.0060

    def test_altitude_conversion(self):
        """Test that altitude is properly converted to float."""
        position = SpotPosition(
            asset_id="Test Tracker",
            timestamp=datetime.now(timezone.utc),
            latitude=40.7128,
            longitude=-74.0060,
            altitude="10.5"  # String
        )

        assert isinstance(position.altitude, float)
        assert position.altitude == 10.5

    def test_model_serialization(self):
        """Test that the model can be serialized to dict."""
        position = SpotPosition(
            asset_id="Test Tracker",
            timestamp=datetime(2025, 7, 10, 12, 0, 0, tzinfo=timezone.utc),
            latitude=40.7128,
            longitude=-74.0060,
            altitude=10.5,
            message_type="OK",
            battery_state="GOOD"
        )

        data = position.dict()

        assert data["asset_id"] == "Test Tracker"
        assert data["latitude"] == 40.7128
        assert data["longitude"] == -74.0060
        assert data["altitude"] == 10.5
        assert data["message_type"] == "OK"
        assert data["battery_state"] == "GOOD"

    def test_model_json_serialization(self):
        """Test that the model can be serialized to JSON."""
        position = SpotPosition(
            asset_id="Test Tracker",
            timestamp=datetime(2025, 7, 10, 12, 0, 0, tzinfo=timezone.utc),
            latitude=40.7128,
            longitude=-74.0060
        )

        json_str = position.json()

        assert '"asset_id":"Test Tracker"' in json_str
        assert '"latitude":40.7128' in json_str
        assert '"longitude":-74.006' in json_str
