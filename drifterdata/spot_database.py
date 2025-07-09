"""
Database module for storing SPOT tracker position data in SQLite.

This module provides functionality to create and manage a SQLite database
for storing position data from SPOT trackers.
"""

import sqlite3
import logging
from datetime import datetime, timedelta
from typing import List, Optional, Dict, Any
from pathlib import Path

from drifterdata.spot_tracker import SpotPosition


# Configure logging
logger = logging.getLogger(__name__)


class SpotDatabase:
    """
    SQLite database manager for SPOT tracker position data.

    This class handles database creation, connection management, and
    CRUD operations for position data.
    """

    def __init__(self, db_path: str = "spot_positions.db"):
        """
        Initialize the database manager.

        Args:
            db_path: Path to the SQLite database file
        """
        self.db_path = Path(db_path)
        self.connection = None
        self._create_database()

    def _create_database(self):
        """Create the database and tables if they don't exist."""
        try:
            with sqlite3.connect(self.db_path) as conn:
                cursor = conn.cursor()

                # Create positions table
                cursor.execute("""
                    CREATE TABLE IF NOT EXISTS positions (
                        id INTEGER PRIMARY KEY AUTOINCREMENT,
                        asset_id TEXT NOT NULL,
                        timestamp TEXT NOT NULL,
                        latitude REAL NOT NULL,
                        longitude REAL NOT NULL,
                        altitude REAL,
                        message_type TEXT,
                        battery_state TEXT,
                        created_at TEXT DEFAULT CURRENT_TIMESTAMP,
                        UNIQUE(asset_id, timestamp)
                    )
                """)

                # Create index for faster queries
                cursor.execute("""
                    CREATE INDEX IF NOT EXISTS idx_asset_timestamp 
                    ON positions(asset_id, timestamp)
                """)

                cursor.execute("""
                    CREATE INDEX IF NOT EXISTS idx_timestamp 
                    ON positions(timestamp)
                """)

                conn.commit()
                logger.info(f"Database initialized at {self.db_path}")

        except sqlite3.Error as e:
            logger.error(f"Error creating database: {e}")
            raise

    def connect(self):
        """Establish database connection."""
        if self.connection is None:
            try:
                self.connection = sqlite3.connect(self.db_path)
                self.connection.row_factory = sqlite3.Row  # Enable dict-like access
                logger.debug("Database connection established")
            except sqlite3.Error as e:
                logger.error(f"Error connecting to database: {e}")
                raise

    def disconnect(self):
        """Close database connection."""
        if self.connection:
            self.connection.close()
            self.connection = None
            logger.debug("Database connection closed")

    def __enter__(self):
        """Context manager entry."""
        self.connect()
        return self

    def __exit__(self, exc_type, exc_val, exc_tb):
        """Context manager exit."""
        self.disconnect()

    def insert_position(self, position: SpotPosition) -> bool:
        """
        Insert a single position into the database.

        Args:
            position: SpotPosition object to insert

        Returns:
            True if inserted successfully, False if already exists
        """
        try:
            with sqlite3.connect(self.db_path) as conn:
                cursor = conn.cursor()

                cursor.execute(
                    """
                    INSERT OR IGNORE INTO positions 
                    (asset_id, timestamp, latitude, longitude, altitude, message_type, battery_state)
                    VALUES (?, ?, ?, ?, ?, ?, ?)
                """,
                    (
                        position.asset_id,
                        position.timestamp.isoformat(),
                        position.latitude,
                        position.longitude,
                        position.altitude,
                        position.message_type,
                        position.battery_state,
                    ),
                )

                if cursor.rowcount > 0:
                    conn.commit()
                    logger.debug(
                        f"Inserted position for {position.asset_id} at {position.timestamp}"
                    )
                    return True
                else:
                    logger.debug(
                        f"Position already exists for {position.asset_id} at {position.timestamp}"
                    )
                    return False

        except sqlite3.Error as e:
            logger.error(f"Error inserting position: {e}")
            raise

    def insert_positions(self, positions: List[SpotPosition]) -> int:
        """
        Insert multiple positions into the database.

        Args:
            positions: List of SpotPosition objects to insert

        Returns:
            Number of positions successfully inserted
        """
        inserted_count = 0

        try:
            with sqlite3.connect(self.db_path) as conn:
                cursor = conn.cursor()

                for position in positions:
                    cursor.execute(
                        """
                        INSERT OR IGNORE INTO positions 
                        (asset_id, timestamp, latitude, longitude, altitude, message_type, battery_state)
                        VALUES (?, ?, ?, ?, ?, ?, ?)
                    """,
                        (
                            position.asset_id,
                            position.timestamp.isoformat(),
                            position.latitude,
                            position.longitude,
                            position.altitude,
                            position.message_type,
                            position.battery_state,
                        ),
                    )

                    if cursor.rowcount > 0:
                        inserted_count += 1

                conn.commit()
                logger.info(
                    f"Inserted {inserted_count} new positions out of {len(positions)} total"
                )
                return inserted_count

        except sqlite3.Error as e:
            logger.error(f"Error inserting positions: {e}")
            raise

    def get_latest_position(
        self, asset_id: Optional[str] = None
    ) -> Optional[Dict[str, Any]]:
        """
        Get the latest position for a specific asset or all assets.

        Args:
            asset_id: Optional asset ID to filter by

        Returns:
            Dictionary containing position data or None
        """
        try:
            with sqlite3.connect(self.db_path) as conn:
                conn.row_factory = sqlite3.Row
                cursor = conn.cursor()

                if asset_id:
                    cursor.execute(
                        """
                        SELECT * FROM positions 
                        WHERE asset_id = ? 
                        ORDER BY timestamp DESC 
                        LIMIT 1
                    """,
                        (asset_id,),
                    )
                else:
                    cursor.execute("""
                        SELECT * FROM positions 
                        ORDER BY timestamp DESC 
                        LIMIT 1
                    """)

                row = cursor.fetchone()
                if row:
                    return dict(row)
                return None

        except sqlite3.Error as e:
            logger.error(f"Error getting latest position: {e}")
            raise

    def get_positions_since(
        self, since: datetime, asset_id: Optional[str] = None
    ) -> List[Dict[str, Any]]:
        """
        Get all positions since a specific timestamp.

        Args:
            since: Datetime to filter positions from
            asset_id: Optional asset ID to filter by

        Returns:
            List of position dictionaries
        """
        try:
            with sqlite3.connect(self.db_path) as conn:
                conn.row_factory = sqlite3.Row
                cursor = conn.cursor()

                if asset_id:
                    cursor.execute(
                        """
                        SELECT * FROM positions 
                        WHERE asset_id = ? AND timestamp > ?
                        ORDER BY timestamp ASC
                    """,
                        (asset_id, since.isoformat()),
                    )
                else:
                    cursor.execute(
                        """
                        SELECT * FROM positions 
                        WHERE timestamp > ?
                        ORDER BY timestamp ASC
                    """,
                        (since.isoformat(),),
                    )

                rows = cursor.fetchall()
                return [dict(row) for row in rows]

        except sqlite3.Error as e:
            logger.error(f"Error getting positions since {since}: {e}")
            raise

    def get_asset_ids(self) -> List[str]:
        """
        Get all unique asset IDs in the database.

        Returns:
            List of asset IDs
        """
        try:
            with sqlite3.connect(self.db_path) as conn:
                cursor = conn.cursor()
                cursor.execute(
                    "SELECT DISTINCT asset_id FROM positions ORDER BY asset_id"
                )
                return [row[0] for row in cursor.fetchall()]

        except sqlite3.Error as e:
            logger.error(f"Error getting asset IDs: {e}")
            raise

    def get_position_count(self, asset_id: Optional[str] = None) -> int:
        """
        Get the total number of positions in the database.

        Args:
            asset_id: Optional asset ID to filter by

        Returns:
            Number of positions
        """
        try:
            with sqlite3.connect(self.db_path) as conn:
                cursor = conn.cursor()

                if asset_id:
                    cursor.execute(
                        "SELECT COUNT(*) FROM positions WHERE asset_id = ?", (asset_id,)
                    )
                else:
                    cursor.execute("SELECT COUNT(*) FROM positions")

                return cursor.fetchone()[0]

        except sqlite3.Error as e:
            logger.error(f"Error getting position count: {e}")
            raise

    def cleanup_old_positions(self, days_to_keep: int = 30) -> int:
        """
        Remove positions older than specified number of days.

        Args:
            days_to_keep: Number of days to keep positions

        Returns:
            Number of positions deleted
        """
        try:
            cutoff_date = datetime.now().replace(tzinfo=None) - timedelta(
                days=days_to_keep
            )

            with sqlite3.connect(self.db_path) as conn:
                cursor = conn.cursor()
                cursor.execute(
                    """
                    DELETE FROM positions 
                    WHERE timestamp < ?
                """,
                    (cutoff_date.isoformat(),),
                )

                deleted_count = cursor.rowcount
                conn.commit()

                logger.info(
                    f"Cleaned up {deleted_count} old positions (older than {days_to_keep} days)"
                )
                return deleted_count

        except sqlite3.Error as e:
            logger.error(f"Error cleaning up old positions: {e}")
            raise

    def get_database_stats(self) -> Dict[str, Any]:
        """
        Get database statistics.

        Returns:
            Dictionary containing database statistics
        """
        try:
            with sqlite3.connect(self.db_path) as conn:
                conn.row_factory = sqlite3.Row
                cursor = conn.cursor()

                # Get total positions
                cursor.execute("SELECT COUNT(*) as total_positions FROM positions")
                total_positions = cursor.fetchone()["total_positions"]

                # Get unique assets
                cursor.execute(
                    "SELECT COUNT(DISTINCT asset_id) as unique_assets FROM positions"
                )
                unique_assets = cursor.fetchone()["unique_assets"]

                # Get date range
                cursor.execute(
                    "SELECT MIN(timestamp) as earliest, MAX(timestamp) as latest FROM positions"
                )
                date_range = cursor.fetchone()

                # Get asset breakdown
                cursor.execute("""
                    SELECT asset_id, COUNT(*) as count, MIN(timestamp) as first_seen, MAX(timestamp) as last_seen
                    FROM positions 
                    GROUP BY asset_id 
                    ORDER BY count DESC
                """)
                asset_breakdown = [dict(row) for row in cursor.fetchall()]

                return {
                    "total_positions": total_positions,
                    "unique_assets": unique_assets,
                    "earliest_position": date_range["earliest"],
                    "latest_position": date_range["latest"],
                    "asset_breakdown": asset_breakdown,
                }

        except sqlite3.Error as e:
            logger.error(f"Error getting database stats: {e}")
            raise
