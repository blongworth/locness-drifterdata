"""
Scheduler module for periodic SPOT tracker data collection.

This module provides functionality to periodically fetch position data
from SPOT trackers and store it in the database.
"""

import time
import logging
from datetime import datetime, timedelta
from typing import Optional, Callable
import schedule
import signal
import sys
from pathlib import Path

from drifterdata.spot_tracker import SpotTrackerAPI
from drifterdata.spot_database import SpotDatabase


# Configure logging
logger = logging.getLogger(__name__)


class SpotDataCollector:
    """
    Periodic data collector for SPOT tracker positions.

    This class coordinates the periodic fetching of position data from
    the SPOT API and storage in the SQLite database.
    """

    def __init__(
        self,
        feed_id: Optional[str] = None,
        api_key: Optional[str] = None,  # Deprecated, kept for backward compatibility
        db_path: str = "spot_positions.db",
        collection_interval: int = 15,  # minutes
        cleanup_days: int = 30,
    ):
        """
        Initialize the data collector.

        Args:
            feed_id: SPOT feed ID
            api_key: Deprecated - SPOT API only requires feed ID
            db_path: Path to SQLite database
            collection_interval: Interval between collections in minutes
            cleanup_days: Days to keep old positions
        """
        self.api = SpotTrackerAPI(feed_id=feed_id)
        self.db = SpotDatabase(db_path)
        self.collection_interval = collection_interval
        self.cleanup_days = cleanup_days
        self.running = False
        self.last_collection = None

        # Setup signal handlers for graceful shutdown
        signal.signal(signal.SIGINT, self._signal_handler)
        signal.signal(signal.SIGTERM, self._signal_handler)

        logger.info(
            f"SpotDataCollector initialized with {collection_interval} minute intervals"
        )

    def _signal_handler(self, signum, frame):
        """Handle shutdown signals gracefully."""
        logger.info(f"Received signal {signum}, shutting down gracefully...")
        self.stop()

    def collect_data(self):
        """
        Collect position data from SPOT API and store in database.

        This method is called periodically by the scheduler.
        """
        try:
            logger.info("Starting data collection cycle")

            # Get positions since last collection (or last 24 hours if first run)
            start_date = self.last_collection or datetime.now() - timedelta(days=1)

            # Fetch positions from API
            positions = self.api.get_latest_positions(start_date)

            if positions:
                # Store in database
                inserted_count = self.db.insert_positions(positions)
                logger.info(
                    f"Collected {len(positions)} positions, inserted {inserted_count} new records"
                )

                # Update last collection time
                self.last_collection = datetime.now()

                # Log some statistics
                stats = self.db.get_database_stats()
                logger.info(
                    f"Database now contains {stats['total_positions']} total positions "
                    f"for {stats['unique_assets']} assets"
                )
            else:
                logger.info("No new positions found")
                self.last_collection = datetime.now()

        except Exception as e:
            logger.error(f"Error during data collection: {e}")
            # Don't update last_collection on error so we retry the same time window

    def cleanup_old_data(self):
        """Clean up old position data from the database."""
        try:
            logger.info("Starting database cleanup")
            deleted_count = self.db.cleanup_old_positions(self.cleanup_days)
            logger.info(f"Cleanup completed, removed {deleted_count} old positions")
        except Exception as e:
            logger.error(f"Error during database cleanup: {e}")

    def test_setup(self) -> bool:
        """
        Test the API connection and database setup.

        Returns:
            True if setup is working, False otherwise
        """
        try:
            logger.info("Testing SPOT API connection...")
            if not self.api.test_connection():
                logger.error("SPOT API connection test failed")
                return False

            logger.info("Testing database connection...")
            count = self.db.get_position_count()
            logger.info(f"Database test successful, found {count} existing positions")

            return True

        except Exception as e:
            logger.error(f"Setup test failed: {e}")
            return False

    def run_once(self):
        """Run a single data collection cycle."""
        logger.info("Running single data collection cycle")
        self.collect_data()

    def start(self):
        """Start the periodic data collection."""
        if self.running:
            logger.warning("Data collector is already running")
            return

        logger.info("Starting SpotDataCollector...")

        # Test setup first
        if not self.test_setup():
            logger.error("Setup test failed, cannot start data collector")
            return

        # Schedule data collection
        schedule.every(self.collection_interval).minutes.do(self.collect_data)

        # Schedule daily cleanup (at 2 AM)
        schedule.every().day.at("02:00").do(self.cleanup_old_data)

        # Run initial collection
        self.collect_data()

        self.running = True
        logger.info(
            f"Data collector started, will collect data every {self.collection_interval} minutes"
        )

        try:
            while self.running:
                schedule.run_pending()
                time.sleep(60)  # Check every minute

        except KeyboardInterrupt:
            logger.info("Received keyboard interrupt, stopping...")
            self.stop()
        except Exception as e:
            logger.error(f"Unexpected error in main loop: {e}")
            self.stop()

    def stop(self):
        """Stop the data collector."""
        if not self.running:
            return

        logger.info("Stopping SpotDataCollector...")
        self.running = False
        schedule.clear()
        logger.info("Data collector stopped")

    def get_status(self) -> dict:
        """
        Get current status of the data collector.

        Returns:
            Dictionary containing status information
        """
        db_stats = self.db.get_database_stats()

        return {
            "running": self.running,
            "last_collection": self.last_collection.isoformat()
            if self.last_collection
            else None,
            "collection_interval_minutes": self.collection_interval,
            "cleanup_days": self.cleanup_days,
            "next_scheduled_jobs": [str(job) for job in schedule.jobs],
            "database_stats": db_stats,
        }


def create_config_file(config_path: str = ".env"):
    """
    Create a sample configuration file.

    Args:
        config_path: Path to the configuration file
    """
    config_content = """# SPOT Tracker Configuration
# Get these values from your SPOT account at https://www.findmespot.com/

# Your SPOT API key
SPOT_API_KEY=your_api_key_here

# Your SPOT feed ID
SPOT_FEED_ID=your_feed_id_here

# Database configuration
DB_PATH=spot_positions.db

# Collection interval in minutes
COLLECTION_INTERVAL=15

# Number of days to keep old positions
CLEANUP_DAYS=30

# Logging level (DEBUG, INFO, WARNING, ERROR)
LOG_LEVEL=INFO
"""

    config_file = Path(config_path)
    if not config_file.exists():
        with open(config_file, "w") as f:
            f.write(config_content)
        logger.info(f"Created sample configuration file at {config_path}")
        logger.info("Please edit the configuration file with your SPOT API credentials")
    else:
        logger.info(f"Configuration file already exists at {config_path}")


if __name__ == "__main__":
    # Setup logging
    logging.basicConfig(
        level=logging.INFO,
        format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
        handlers=[logging.FileHandler("spot_collector.log"), logging.StreamHandler()],
    )

    # Create config file if it doesn't exist
    create_config_file()

    # Initialize and start collector
    collector = SpotDataCollector()
    collector.start()
