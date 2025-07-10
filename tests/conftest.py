"""
Configuration file for pytest.
"""

import os
import sys
from pathlib import Path

# Add the project root to the Python path
project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root))

# Set up test environment variables
os.environ.setdefault('SPOT_FEED_ID', 'test_feed_id')
os.environ.setdefault('SPOT_API_KEY', 'test_api_key')
