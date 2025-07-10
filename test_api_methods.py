#!/usr/bin/env python3
"""
Test script demonstrating the new SPOT API methods.
"""

from datetime import datetime, timedelta
from drifterdata.spot_tracker import SpotTrackerAPI

def test_api_methods():
    """Test the new SPOT API methods."""
    
    # Initialize API (you'll need to set SPOT_FEED_ID environment variable)
    try:
        api = SpotTrackerAPI()
        print("✓ API initialized successfully")
    except ValueError as e:
        print(f"✗ API initialization failed: {e}")
        print("Please set SPOT_FEED_ID environment variable")
        return
    
    # Test connection
    print("\n--- Testing Connection ---")
    if api.test_connection():
        print("✓ Connection test passed")
    else:
        print("✗ Connection test failed")
        return
    
    # Test get_latest_position
    print("\n--- Testing get_latest_position ---")
    try:
        latest_position = api.get_latest_position()
        if latest_position:
            print(f"✓ Latest position: {latest_position.asset_id} at {latest_position.timestamp}")
            print(f"  Location: {latest_position.latitude}, {latest_position.longitude}")
        else:
            print("⚠ No latest position found")
    except Exception as e:
        print(f"✗ get_latest_position failed: {e}")
    
    # Test get_messages (recent messages)
    print("\n--- Testing get_messages (recent) ---")
    try:
        messages = api.get_messages()
        print(f"✓ Retrieved {len(messages)} recent messages")
        if messages:
            print(f"  Most recent: {messages[0].asset_id} at {messages[0].timestamp}")
    except Exception as e:
        print(f"✗ get_messages failed: {e}")
    
    # Test get_messages with pagination
    print("\n--- Testing get_messages with pagination ---")
    try:
        messages_page2 = api.get_messages(start=51)
        print(f"✓ Retrieved {len(messages_page2)} messages from page 2")
    except Exception as e:
        print(f"✗ get_messages with pagination failed: {e}")
    
    # Test get_messages_by_date_range
    print("\n--- Testing get_messages_by_date_range ---")
    try:
        end_date = datetime.now()
        start_date = end_date - timedelta(days=2)  # Last 2 days
        
        date_messages = api.get_messages_by_date_range(start_date, end_date)
        print(f"✓ Retrieved {len(date_messages)} messages from last 2 days")
        if date_messages:
            print(f"  Date range: {start_date.strftime('%Y-%m-%d')} to {end_date.strftime('%Y-%m-%d')}")
    except Exception as e:
        print(f"✗ get_messages_by_date_range failed: {e}")
    
    # Test deprecated method (should show warning)
    print("\n--- Testing deprecated get_latest_positions ---")
    try:
        legacy_positions = api.get_latest_positions()
        print(f"✓ Legacy method returned {len(legacy_positions)} positions (with deprecation warning)")
    except Exception as e:
        print(f"✗ get_latest_positions failed: {e}")
    
    print("\n--- API Method Tests Complete ---")

if __name__ == "__main__":
    test_api_methods()
