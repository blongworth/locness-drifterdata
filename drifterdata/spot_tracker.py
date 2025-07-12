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
    
    def __init__(self, feed_id: Optional[str] = None, api_key: Optional[str] = None):
        """
        Initialize the SPOT Tracker API client.
        
        Args:
            feed_id: SPOT feed ID (can also be set via SPOT_FEED_ID environment variable)
            api_key: Deprecated - SPOT API only requires feed ID
        """
        self.feed_id = feed_id or os.getenv('SPOT_FEED_ID')
        # Keep api_key for backward compatibility but it's not used
        self.api_key = api_key or os.getenv('SPOT_API_KEY')
        
        if not self.feed_id:
            raise ValueError("SPOT feed ID is required. Set SPOT_FEED_ID environment variable or pass feed_id parameter.")
        
        self.base_url = "https://api.findmespot.com/spot-main-web/consumer/rest-api/2.0/public/feed"
        self.session = requests.Session()
        self.session.headers.update({
            'User-Agent': 'SPOT-Tracker-Client/1.0',
            'Accept': 'application/json'
        })
    
    def get_latest_position(self, feed_password: Optional[str] = None) -> Optional[SpotPosition]:
        """
        Retrieve the latest position for each device on the feed.
        
        Args:
            feed_password: Optional password for protected feeds
            
        Returns:
            Latest SpotPosition object or None if no data available
        """
        url = f"{self.base_url}/{self.feed_id}/latest.json"
        
        params = {}
        if feed_password:
            params['feedPassword'] = feed_password
        
        try:
            logger.info(f"Fetching latest position from SPOT API for feed {self.feed_id}")
            response = self.session.get(url, params=params, timeout=30)
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
    
    def get_messages(self, start: Optional[int] = None, count: Optional[int] = None, 
                    feed_password: Optional[str] = None) -> List[SpotPosition]:
        """
        Retrieve messages from SPOT API with pagination support.
        
        Args:
            start: Starting position for pagination (1-based, 50 messages per page)
            count: Number of messages to retrieve (for backward compatibility)
            feed_password: Optional password for protected feeds
            
        Returns:
            List of SpotPosition objects
        """
        url = f"{self.base_url}/{self.feed_id}/message.json"
        
        params = {}
        if start is not None:
            params['start'] = start
        if feed_password:
            params['feedPassword'] = feed_password
        
        try:
            logger.info(f"Fetching messages from SPOT API for feed {self.feed_id} (start={start})")
            response = self.session.get(url, params=params, timeout=30)
            response.raise_for_status()
            
            data = response.json()
            positions = self._parse_response_data(data)
            
            # If count is specified and we got more messages, limit the results
            if count is not None and len(positions) > count:
                positions = positions[:count]
            
            logger.info(f"Retrieved {len(positions)} messages from SPOT API")
            return positions
                
        except requests.exceptions.RequestException as e:
            logger.error(f"Error fetching messages from SPOT API: {e}")
            raise
        except Exception as e:
            logger.error(f"Unexpected error processing SPOT API response: {e}")
            raise
    
    def get_messages_by_date_range(self, start_date: datetime, end_date: datetime,
                                  feed_password: Optional[str] = None) -> List[SpotPosition]:
        """
        Retrieve messages from SPOT API within a specific date range.
        Note: SPOT API has a 7-day maximum restriction for date ranges.
        
        Args:
            start_date: Start date for the range
            end_date: End date for the range
            feed_password: Optional password for protected feeds
            
        Returns:
            List of SpotPosition objects
        """
        url = f"{self.base_url}/{self.feed_id}/message.json"
        
        # Format dates as required by SPOT API: YYYY-MM-DDTHH:MM:SS-0000
        start_str = start_date.strftime('%Y-%m-%dT%H:%M:%S-0000')
        end_str = end_date.strftime('%Y-%m-%dT%H:%M:%S-0000')
        
        params = {
            'startDate': start_str,
            'endDate': end_str
        }
        if feed_password:
            params['feedPassword'] = feed_password
        
        try:
            logger.info(f"Fetching messages from SPOT API for feed {self.feed_id} "
                       f"from {start_str} to {end_str}")
            response = self.session.get(url, params=params, timeout=30)
            response.raise_for_status()
            
            data = response.json()
            positions = self._parse_response_data(data)
            
            logger.info(f"Retrieved {len(positions)} messages from SPOT API for date range")
            return positions
                
        except requests.exceptions.RequestException as e:
            logger.error(f"Error fetching messages by date range from SPOT API: {e}")
            raise
        except Exception as e:
            logger.error(f"Unexpected error processing SPOT API response: {e}")
            raise
    
    def get_latest_positions(self, start_date: Optional[datetime] = None) -> List[SpotPosition]:
        """
        Retrieve latest position data from SPOT API.
        
        DEPRECATED: Use get_latest_position(), get_messages(), or get_messages_by_date_range() instead.
        
        Args:
            start_date: Optional start date to filter positions (defaults to last 24 hours)
            
        Returns:
            List of SpotPosition objects
        """
        logger.warning("get_latest_positions() is deprecated. Use get_messages() or get_messages_by_date_range() instead.")
        
        if start_date:
            # Use date range method for backward compatibility
            end_date = datetime.now(timezone.utc)
            return self.get_messages_by_date_range(start_date, end_date)
        else:
            # Return recent messages
            return self.get_messages()
    
    def _parse_response_data(self, data: Dict[str, Any]) -> List[SpotPosition]:
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
    
    def _parse_message(self, message: Dict[str, Any]) -> Optional[SpotPosition]:
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
