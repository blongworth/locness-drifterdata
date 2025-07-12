"""
SPOT Tracker API module for accessing position data.

This module provides functionality to interact with the SPOT Satellite GPS Messenger
API to retrieve position data for tracked assets.
"""

import os
import logging
from datetime import datetime, timezone
from typing import Optional, List, Dict, Any

import requests
from pydantic import BaseModel, Field, validator
from drifterdata.logging_config import setup_logging


# Setup logging
setup_logging()

logger = logging.getLogger(__name__)


class SpotPosition(BaseModel):
    """Model for SPOT position data."""
    asset_id: str = Field(..., description="Asset/tracker ID")
    timestamp: datetime = Field(..., description="Position timestamp")
    latitude: float = Field(..., description="Latitude coordinate")
    longitude: float = Field(..., description="Longitude coordinate")
    altitude: Optional[float] = Field(None, description="Altitude in meters")
    message_type: Optional[str] = Field(None, description="Message type")
    battery_state: Optional[str] = Field(None, description="Battery status")
    
    @validator('timestamp', pre=True)
    def parse_timestamp(cls, v):
        """Parse timestamp from various formats."""
        if isinstance(v, str):
            try:
                # Try ISO format first
                dt = datetime.fromisoformat(v.replace('Z', '+00:00'))
                # If no timezone info, assume UTC
                if dt.tzinfo is None:
                    dt = dt.replace(tzinfo=timezone.utc)
                return dt
            except ValueError:
                # Try Unix timestamp string
                try:
                    return datetime.fromtimestamp(float(v), tz=timezone.utc)
                except ValueError:
                    # Try other common formats
                    for fmt in ['%Y-%m-%dT%H:%M:%S', '%Y-%m-%d %H:%M:%S']:
                        try:
                            dt = datetime.strptime(v, fmt)
                            return dt.replace(tzinfo=timezone.utc)
                        except ValueError:
                            continue
                    raise ValueError(f"Could not parse timestamp: {v}")
        elif isinstance(v, (int, float)):
            return datetime.fromtimestamp(v, tz=timezone.utc)
        return v


class SpotTrackerAPI:
    """
    SPOT Tracker API client for retrieving position data.
    
    This class handles authentication and API requests to retrieve position data
    for SPOT satellite GPS trackers.
    """
    
    def __init__(self, feed_id: str = None):
        """
        Initialize the SPOT Tracker API client.
        
        Args:
            feed_id: SPOT feed ID (can also be set via SPOT_FEED_ID environment variable)
        """
        self.feed_id = feed_id or os.getenv('SPOT_FEED_ID')
        
        if not self.feed_id:
            raise ValueError("SPOT feed ID is required. Set SPOT_FEED_ID environment variable or pass feed_id parameter.")
        
        self.base_url = "https://api.findmespot.com/spot-main-web/consumer/rest-api/2.0/public/feed"
        self.session = requests.Session()
        self.session.headers.update({
            'User-Agent': 'SPOT-Tracker-Client/1.0',
            'Accept': 'application/json'
        })
    
    def get_latest_position(self) -> SpotPosition:
        """
        Retrieve the latest position for each device on the feed.
        
        Returns:
            Latest SpotPosition object or None if no data available
        """
        url = f"{self.base_url}/{self.feed_id}/latest.json"
        
        try:
            logger.info(f"Fetching latest position from SPOT API for feed {self.feed_id}")
            response = self.session.get(url, timeout=30)
            response.raise_for_status()
            
            data = response.json()
            
            # Parse the response structure for latest endpoint
            if 'response' in data and 'feedMessageResponse' in data['response']:
                feed_response = data['response']['feedMessageResponse']
                
                if 'count' in feed_response and feed_response['count'] > 0:
                    messages = feed_response.get('messages', {}).get('message', [])
                    
                    # Handle single message vs list of messages
                    if isinstance(messages, dict):
                        messages = [messages]
                    
                    # Return the first (latest) message
                    if messages:
                        position = self._parse_message(messages[0])
                        if position:
                            logger.info("Retrieved latest position from SPOT API")
                            return position
                
            logger.info("No latest position data found")
            return None
                
        except requests.exceptions.RequestException as e:
            logger.error(f"Error fetching latest position from SPOT API: {e}")
            raise
        except Exception as e:
            logger.error(f"Unexpected error processing SPOT API response: {e}")
            raise

    def get_messages(self, start: int = None) -> list[SpotPosition]:
        """
        Retrieve messages from SPOT API with pagination support.

        Args:
            start: Starting position for pagination (1-based, 50 messages per page)

        Returns:
            List of SpotPosition objects
        """
        url = f"{self.base_url}/{self.feed_id}/message.json"
        page_size = 50
        positions = []
        page_start = start if start is not None else 1

        def fetch_page(page_start):
            params = {} if page_start is None else {'start': page_start}
            logger.info(f"Fetching messages from SPOT API for feed {self.feed_id} (start={page_start})")
            response = self.session.get(url, params=params, timeout=30)
            response.raise_for_status()
            data = response.json()
            feed_response = data.get('response', {}).get('feedMessageResponse', {})
            count_in_page = feed_response.get('count', 0)
            page_positions = self._parse_response_data(data)
            return page_positions, count_in_page

        try:
            fetched = 0
            while True:
                page_positions, count_in_page = fetch_page(page_start)
                positions.extend(page_positions)
                fetched += len(page_positions)
                # If less than page_size positions returned, we've reached the end
                if count_in_page < page_size:
                    break

                # Stop if we've fetched all available messages
                if count_in_page <= page_size:
                    break

                page_start += page_size

        except requests.exceptions.RequestException as e:
            logger.error(f"Error fetching messages from SPOT API: {e}")
            raise
        except Exception as e:
            logger.error(f"Unexpected error processing SPOT API response: {e}")
            raise

        return positions
    
    def _parse_response_data(self, data: dict[str, Any]) -> list[SpotPosition]:
        """
        Parse response data from SPOT API.
        
        Args:
            data: Raw response data from SPOT API
            
        Returns:
            List of SpotPosition objects
        """
        positions = []
        
        # Parse the response structure
        if 'response' in data and 'feedMessageResponse' in data['response']:
            feed_response = data['response']['feedMessageResponse']
            
            if 'count' in feed_response and feed_response['count'] > 0:
                messages = feed_response.get('messages', {}).get('message', [])
                
                # Handle single message vs list of messages
                if isinstance(messages, dict):
                    messages = [messages]
                
                for msg in messages:
                    try:
                        position = self._parse_message(msg)
                        if position:
                            positions.append(position)
                    except Exception as e:
                        logger.warning(f"Failed to parse message: {e}")
                        continue
        else:
            logger.warning("Unexpected response structure from SPOT API")
        
        return positions
    
    def _parse_message(self, message: dict[str, Any]) -> SpotPosition:
        """
        Parse a single SPOT message into a SpotPosition object.
        
        Args:
            message: Raw message data from SPOT API
            
        Returns:
            SpotPosition object or None if parsing fails
        """
        try:
            # Extract position data from message
            asset_id = message.get('messengerName', 'unknown')
            
            # Parse timestamp
            timestamp_str = message.get('dateTime', message.get('unixTime'))
            if not timestamp_str:
                logger.warning("No timestamp found in message")
                return None
            
            # Parse coordinates
            latitude = message.get('latitude')
            longitude = message.get('longitude')
            
            if latitude is None or longitude is None:
                logger.warning("Missing coordinates in message")
                return None
            
            # Optional fields
            altitude = message.get('altitude')
            message_type = message.get('messageType')
            battery_state = message.get('batteryState')
            
            position = SpotPosition(
                asset_id=asset_id,
                timestamp=timestamp_str,
                latitude=float(latitude),
                longitude=float(longitude),
                altitude=float(altitude) if altitude is not None else None,
                message_type=message_type,
                battery_state=battery_state
            )
            
            return position
            
        except Exception as e:
            logger.error(f"Error parsing SPOT message: {e}")
            return None
    
    def test_connection(self) -> bool:
        """
        Test the connection to SPOT API.
        
        Returns:
            True if connection is successful, False otherwise
        """
        try:
            # Try to get the latest position first
            latest_position = self.get_latest_position()
            if latest_position:
                logger.info("Connection test successful. Found latest position.")
                return True
            
            # If no latest position, try to get recent messages
            positions = self.get_messages()
            logger.info(f"Connection test successful. Found {len(positions)} recent messages.")
            return True
        except Exception as e:
            logger.error(f"Connection test failed: {e}")
            return False
