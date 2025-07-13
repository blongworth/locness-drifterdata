import pytest
from unittest.mock import MagicMock
from datetime import datetime, timedelta
from drifterdata.spot_collector import SpotDataCollector
from drifterdata.spot_tracker import SpotPosition

@pytest.fixture
def mock_db():
    db = MagicMock()
    db.get_latest_position.return_value = None
    db.insert_positions.return_value = 0
    db.get_database_stats.return_value = {'total_positions': 0, 'unique_assets': 0}
    return db

@pytest.fixture
def mock_api():
    api = MagicMock()
    return api

@pytest.fixture
def collector(mock_db, mock_api):
    collector = SpotDataCollector(feed_id='test_feed')
    collector.db = mock_db
    collector.api = mock_api
    return collector

def make_position(ts):
    return SpotPosition(
        asset_id='A',
        timestamp=ts,
        latitude=1.0,
        longitude=2.0,
        altitude=10.0,
        message_type='TRACK',
        battery_state='GOOD'
    )

def test_no_new_records_downloaded(collector, mock_db, mock_api):
    # Last record is recent, API returns only old records
    now = datetime.now()
    mock_db.get_latest_position.return_value = {'timestamp': now.isoformat()}
    mock_api.get_messages.return_value = [make_position(now - timedelta(hours=1))]
    collector.collect_data()
    # Should not insert any new records
    mock_db.insert_positions.assert_called_with([])

def test_new_records_downloaded(collector, mock_db, mock_api):
    # Last record is old, API returns new records
    now = datetime.now()
    old = now - timedelta(days=1)
    mock_db.get_latest_position.return_value = {'timestamp': old.isoformat()}
    new_pos = make_position(now)
    mock_api.get_messages.return_value = [new_pos]
    collector.collect_data()
    # Should insert the new record
    mock_db.insert_positions.assert_called_with([new_pos])

def test_only_new_records_downloaded(collector, mock_db, mock_api):
    # Last record is in the middle, API returns old and new
    now = datetime.now()
    mid = now - timedelta(hours=1)
    old = now - timedelta(days=1)
    mock_db.get_latest_position.return_value = {'timestamp': mid.isoformat()}
    pos_old = make_position(old)
    pos_new = make_position(now)
    mock_api.get_messages.return_value = [pos_old, pos_new]
    collector.collect_data()
    # Should only insert the new record
    mock_db.insert_positions.assert_called_with([pos_new])
