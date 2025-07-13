# SPOT Tracker Data Collection System

A Python module for accessing SPOT Satellite GPS Messenger data through their API and storing position data in a SQLite database.

## Features

- **API Integration**: Connects to SPOT's REST API to fetch position data
- **Database Storage**: Stores position data in SQLite with proper indexing
- **Periodic Collection**: Automatically collects data at configurable intervals
- **Data Management**: Automatic cleanup of old position data
- **Command-line Interface**: Easy-to-use CLI for all operations
- **Web Dashboard**: Interactive map visualization with multiple data sources
- **Live API Access**: Dashboard can fetch real-time data directly from SPOT API
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

3. Edit the `.env` file with your SPOT feed ID:
```bash
cp .env.example .env
# Edit .env with your actual SPOT_FEED_ID
```

## Getting SPOT Feed ID

1. Go to [SPOT's website](https://www.findmespot.com/)
2. Log in to your account
3. Navigate to your tracker's sharing options
4. Find your Feed ID in the sharing URL or settings

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
- **Dual Data Sources**: Use either local database or live SPOT API data
- **Interactive Map**: View drifter traces on an interactive map with Folium
- **Multi-drifter Support**: Display traces for multiple drifters with different colors
- **Time Range Control**: Filter data by number of days of history
- **Position Details**: Click markers to see detailed position information
- **Real-time Stats**: Live statistics from selected data source
- **Clean Interface**: Simplified UI focused on data visualization
- **Responsive Design**: Works on desktop and mobile devices

### Data Sources:
Choose your data source via command line argument:
1. **Database** (`--source database`): Use locally stored position data (default)
2. **SPOT API** (`--source api`): Get real-time data directly from SPOT API

### Usage:

**Database Mode (Default):**
```bash
# Use local database (requires running the collector first)
uv run python main.py dashboard
# or explicitly:
uv run python main.py dashboard --source database
```

**Live API Mode:**
```bash
# Use live SPOT API data
uv run python main.py dashboard --source api
```

### API Configuration:
For live SPOT API data, configure your credentials in `.streamlit/secrets.toml`:

1. **Create secrets file:**
   ```bash
   cp .streamlit/secrets.toml.example .streamlit/secrets.toml
   ```

2. **Edit the secrets file:**
   ```toml
   [spot]
   feed_id = "your_actual_spot_feed_id"
   ```

3. **Launch API dashboard:**
   ```bash
   uv run python main.py dashboard --source api
   ```

**Alternative:** Set environment variable:
```bash
export SPOT_FEED_ID="your_feed_id"
uv run python main.py dashboard --source api
```

### Dashboard Components:
- **Data Source Indicator**: Shows current source (Database or SPOT API)
- **Drifter Selection**: Choose which drifters to display
- **Time Range Slider**: Adjust historical data range (1-30 days)
- **Interactive Map**: Traces with start/end markers and position details
- **Data Statistics**: Real-time metrics from the selected source
- **Position Table**: Summary and detailed view of position data

## Programmatic Usage

```python
from spot_tracker import SpotTrackerAPI
from spot_database import SpotDatabase
from spot_collector import SpotDataCollector

# Initialize API client
api = SpotTrackerAPI(feed_id="your_feed_id")

# Get the latest position for each device
latest_position = api.get_latest_position()

# Get recent messages (last 50 by default)
recent_messages = api.get_messages()

# Get messages with pagination (starting from position 51)
more_messages = api.get_messages(start=51)

# Initialize database
db = SpotDatabase("positions.db")

# Store positions
db.insert_positions(recent_messages)

# Start automated collection
collector = SpotDataCollector(
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

- `SPOT_FEED_ID`: Your SPOT feed ID
- `DB_PATH`: Path to SQLite database file
- `COLLECTION_INTERVAL`: Collection interval in minutes
- `CLEANUP_DAYS`: Number of days to keep old positions
- `LOG_LEVEL`: Logging level (DEBUG, INFO, WARNING, ERROR)

## API Reference

### SpotTrackerAPI

Main class for interacting with the SPOT API.

#### Methods:
- `get_latest_position(feed_password=None)`: Get the latest position for each device
- `get_messages(start=None, count=None, feed_password=None)`: Get messages with pagination
- `test_connection()`: Test API connectivity

#### Parameters:
- `start`: Starting position for pagination (1-based, 50 messages per page)
- `count`: Number of messages to retrieve (for limiting results)

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
├── spot_database.py     # Database management
├── spot_collector.py    # Data collection scheduler
└── dashboard.py         # Streamlit dashboard
tests/
├── test_spot_tracker.py # API client tests
├── test_spot_position.py # Data model tests
├── test_integration.py  # Integration tests
└── conftest.py         # Test configuration
```

### Testing

The project uses pytest for testing with comprehensive test coverage:

#### Unit Tests
```bash
# Run unit tests only (default)
make test
# or
uv run python -m pytest -m "not integration" -v

# Run with coverage
make test-coverage
# or
uv run python -m pytest -m "not integration" --cov=drifterdata --cov-report=html -v
```

#### Integration Tests
Integration tests run against the real SPOT API and require valid credentials:

```bash
# Set environment variables
export SPOT_FEED_ID=your_real_feed_id
export SPOT_FEED_PASSWORD=your_password  # if required

# Run integration tests
make test-integration
# or
uv run python -m pytest -m "integration" -v
```

#### All Tests
```bash
# Run all tests (unit + integration)
make test-all
# or
uv run python -m pytest -v
```

#### Test Features
- **Comprehensive mocking**: All external API calls are mocked in unit tests
- **Error handling**: Tests cover various error conditions and edge cases
- **Data validation**: Tests verify timestamp parsing, coordinate validation, etc.
- **Integration testing**: Optional tests against real SPOT API
- **Coverage reporting**: HTML coverage reports generated in `htmlcov/`

### Development Setup

1. **Install dependencies**:
   ```bash
   uv sync --group dev
   ```

2. **Run tests**:
   ```bash
   make test
   ```

3. **Run with coverage**:
   ```bash
   make test-coverage
   ```

4. **Clean up**:
   ```bash
   make clean
   ```
├── spot_database.py     # SQLite database manager
├── spot_collector.py    # Periodic data collector
├── dashboard.py         # Streamlit web dashboard
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
