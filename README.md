# SPOT Tracker Data Collection System

A Python module for accessing SPOT Satellite GPS Messenger data through their API and storing position data in a SQLite database.

## Features

- **API Integration**: Connects to SPOT's REST API to fetch position data
- **Database Storage**: Stores position data in SQLite with proper indexing
- **Periodic Collection**: Automatically collects data at configurable intervals
- **Data Management**: Automatic cleanup of old position data
- **Command-line Interface**: Easy-to-use CLI for all operations
- **Logging**: Comprehensive logging for monitoring and debugging

## Installation

1. Install the package dependencies using uv:
```bash
uv sync
```

This will install all required dependencies including:
- Core data collection: `requests`, `python-dotenv`, `schedule`, `pydantic`
- Web dashboard: `streamlit`, `folium`, `streamlit-folium`, `pandas`

2. Create your configuration file:
```bash
uv run python main.py config
```

3. Edit the `.env` file with your SPOT credentials:
```bash
cp .env.example .env
# Edit .env with your actual SPOT_API_KEY and SPOT_FEED_ID
```

## Getting SPOT API Credentials

1. Go to [SPOT's website](https://www.findmespot.com/)
2. Log in to your account
3. Navigate to "My Account" → "API Keys"
4. Generate a new API key
5. Find your Feed ID in the sharing options for your tracker

## Usage

### Command Line Interface

Test your setup:
```bash
uv run python main.py test
```

Run a single data collection:
```bash
uv run python main.py collect
```

Start continuous data collection:
```bash
uv run python main.py start
```

View database statistics:
```bash
uv run python main.py status
```

Clean up old data:
```bash
uv run python main.py cleanup --days 7
```

Launch the web dashboard:
```bash
uv run python main.py dashboard
```

## Web Dashboard

The project includes a Streamlit-based web dashboard for visualizing drifter position data:

### Features:
- **Interactive Map**: View drifter traces on an interactive map with Folium
- **Multi-drifter Support**: Display traces for multiple drifters with different colors
- **Time Range Control**: Filter data by number of days of history
- **Position Details**: Click markers to see detailed position information
- **Real-time Stats**: Live database statistics and metrics
- **Responsive Design**: Works on desktop and mobile devices

### Usage:
```bash
# Launch the dashboard (opens at http://localhost:8501 or similar)
uv run python main.py dashboard

# Dashboard will automatically use the same database as the collector
# Navigate to the URL shown in the terminal to view the interface
```

### Dashboard Components:
- **Sidebar Controls**: Select drifters, adjust time range, view stats
- **Main Map**: Interactive map showing drifter traces and positions
- **Data Table**: Summary of recent positions and detailed data view
- **Markers**: Start (play icon), current (stop icon), and intermediate positions

## Programmatic Usage

```python
from spot_tracker import SpotTrackerAPI
from spot_database import SpotDatabase
from spot_collector import SpotDataCollector

# Initialize API client
api = SpotTrackerAPI(api_key="your_key", feed_id="your_feed_id")

# Get latest positions
positions = api.get_latest_positions()

# Initialize database
db = SpotDatabase("positions.db")

# Store positions
db.insert_positions(positions)

# Start automated collection
collector = SpotDataCollector(
    api_key="your_key",
    feed_id="your_feed_id",
    collection_interval=15  # minutes
)
collector.start()
```

## Database Schema

The SQLite database contains a `positions` table with the following structure:

| Column | Type | Description |
|--------|------|-------------|
| id | INTEGER | Primary key |
| asset_id | TEXT | Tracker/asset identifier |
| timestamp | TEXT | Position timestamp (ISO format) |
| latitude | REAL | Latitude coordinate |
| longitude | REAL | Longitude coordinate |
| altitude | REAL | Altitude in meters (optional) |
| message_type | TEXT | Type of SPOT message (optional) |
| battery_state | TEXT | Battery status (optional) |
| created_at | TEXT | Record creation timestamp |

## Configuration

Configuration can be provided via environment variables or a `.env` file:

- `SPOT_API_KEY`: Your SPOT API key
- `SPOT_FEED_ID`: Your SPOT feed ID
- `DB_PATH`: Path to SQLite database file
- `COLLECTION_INTERVAL`: Collection interval in minutes
- `CLEANUP_DAYS`: Number of days to keep old positions
- `LOG_LEVEL`: Logging level (DEBUG, INFO, WARNING, ERROR)

## API Reference

### SpotTrackerAPI

Main class for interacting with the SPOT API.

#### Methods:
- `get_latest_positions(start_date=None)`: Fetch latest position data
- `test_connection()`: Test API connectivity

### SpotDatabase

SQLite database manager for position data.

#### Methods:
- `insert_position(position)`: Insert a single position
- `insert_positions(positions)`: Insert multiple positions
- `get_latest_position(asset_id=None)`: Get most recent position
- `get_positions_since(since, asset_id=None)`: Get positions since timestamp
- `get_database_stats()`: Get database statistics
- `cleanup_old_positions(days_to_keep)`: Remove old positions

### SpotDataCollector

Coordinates periodic data collection.

#### Methods:
- `start()`: Start periodic collection
- `stop()`: Stop collection
- `run_once()`: Run single collection cycle
- `test_setup()`: Test API and database setup
- `get_status()`: Get collector status

## Logging

Logs are written to:
- `spot_tracker.log`: Main application log
- `spot_collector.log`: Data collector specific log
- Console output

## Error Handling

The system includes comprehensive error handling:
- API connection failures
- Database errors
- Invalid data formats
- Network timeouts
- Graceful shutdown on interrupts

## Development

### Project Structure

```
drifterdata/
├── main.py              # CLI interface
├── spot_tracker.py      # SPOT API client
├── spot_database.py     # SQLite database manager
├── spot_collector.py    # Periodic data collector
├── pyproject.toml       # Project configuration
├── .env.example         # Example configuration
└── README.md           # This file
```

### Running Tests

```bash
# Test API connection
python main.py test

# Test single collection
python main.py collect

# View database stats
python main.py status
```

## License

This project is licensed under the MIT License.
