"""
Main entry point for the SPOT tracker data collection system.
"""

import sys
import logging
import argparse
from pathlib import Path

from drifterdata.spot_collector import SpotDataCollector, create_config_file
from drifterdata.spot_database import SpotDatabase


def setup_logging(level: str = "INFO"):
    """Setup logging configuration."""
    logging.basicConfig(
        level=getattr(logging, level.upper()),
        format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
        handlers=[logging.FileHandler("spot_tracker.log"), logging.StreamHandler()],
    )


def cmd_start(args):
    """Start the data collector."""
    collector = SpotDataCollector(
        db_path=args.db_path,
        collection_interval=args.interval,
        cleanup_days=args.cleanup_days,
    )
    collector.start()


def cmd_test(args):
    """Test the API connection and database setup."""
    collector = SpotDataCollector(db_path=args.db_path)
    if collector.test_setup():
        print("✓ Setup test passed!")
        return 0
    else:
        print("✗ Setup test failed!")
        return 1


def cmd_collect(args):
    """Run a single data collection cycle."""
    collector = SpotDataCollector(
        db_path=args.db_path,
        collection_interval=args.interval,
        cleanup_days=args.cleanup_days,
    )
    collector.run_once()


def cmd_status(args):
    """Show database status and statistics."""
    db = SpotDatabase(args.db_path)
    stats = db.get_database_stats()

    print("Database Statistics:")
    print(f"  Total positions: {stats['total_positions']}")
    print(f"  Unique assets: {stats['unique_assets']}")
    print(f"  Earliest position: {stats['earliest_position']}")
    print(f"  Latest position: {stats['latest_position']}")
    print("\nAsset Breakdown:")
    for asset in stats["asset_breakdown"]:
        print(
            f"  {asset['asset_id']}: {asset['count']} positions "
            f"(first: {asset['first_seen']}, last: {asset['last_seen']})"
        )


def cmd_cleanup(args):
    """Clean up old position data."""
    db = SpotDatabase(args.db_path)
    deleted_count = db.cleanup_old_positions(args.days)
    print(f"Cleaned up {deleted_count} old positions (older than {args.days} days)")


def cmd_dashboard(args):
    """Launch the Streamlit dashboard."""
    import subprocess
    import sys
    import importlib.util
    
    # Check if streamlit is available
    if importlib.util.find_spec("streamlit") is None:
        print("Streamlit is not installed. Please install it with:")
        print("uv add streamlit folium streamlit-folium pandas")
        return 1
    
    # Get the dashboard module path
    dashboard_path = Path(__file__).parent / "dashboard.py"
    
    # Build command based on whether --use-db flag is provided
    cmd = [sys.executable, "-m", "streamlit", "run", str(dashboard_path), "--"]
    
    # Add db-path argument if using database mode
    if args.use_db:
        cmd.extend(["--db-path", args.db_path])
        data_source_name = "database"
    else:
        data_source_name = "SPOT API"
    
    print(f"Starting dashboard with {data_source_name} data source at http://localhost:8501")
    print("Press Ctrl+C to stop the dashboard")
    
    try:
        subprocess.run(cmd)
    except KeyboardInterrupt:
        print("\nDashboard stopped")
        return 0


def cmd_config(args):
    """Create a sample configuration file."""
    create_config_file(args.config_path)


def main():
    """Main entry point."""
    parser = argparse.ArgumentParser(
        description="SPOT Tracker Data Collection System",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  %(prog)s start                    # Start the data collector
  %(prog)s test                     # Test API connection
  %(prog)s collect                  # Run single collection cycle
  %(prog)s status                   # Show database statistics
  %(prog)s cleanup --days 7         # Clean up positions older than 7 days
  %(prog)s config                   # Create sample config file
  %(prog)s dashboard                # Launch web dashboard (API mode)
  %(prog)s dashboard --use-db       # Launch web dashboard (database mode)
        """,
    )

    parser.add_argument(
        "--db-path",
        default="spot_positions.db",
        help="Path to SQLite database file (default: spot_positions.db)",
    )

    parser.add_argument(
        "--log-level",
        default="INFO",
        choices=["DEBUG", "INFO", "WARNING", "ERROR"],
        help="Logging level (default: INFO)",
    )

    subparsers = parser.add_subparsers(dest="command", help="Available commands")

    # Start command
    start_parser = subparsers.add_parser("start", help="Start the data collector")
    start_parser.add_argument(
        "--interval",
        type=int,
        default=15,
        help="Collection interval in minutes (default: 15)",
    )
    start_parser.add_argument(
        "--cleanup-days",
        type=int,
        default=30,
        help="Days to keep old positions (default: 30)",
    )
    start_parser.set_defaults(func=cmd_start)

    # Test command
    test_parser = subparsers.add_parser(
        "test", help="Test API connection and database setup"
    )
    test_parser.set_defaults(func=cmd_test)

    # Collect command
    collect_parser = subparsers.add_parser(
        "collect", help="Run a single data collection cycle"
    )
    collect_parser.add_argument(
        "--interval",
        type=int,
        default=15,
        help="Collection interval in minutes (default: 15)",
    )
    collect_parser.add_argument(
        "--cleanup-days",
        type=int,
        default=30,
        help="Days to keep old positions (default: 30)",
    )
    collect_parser.set_defaults(func=cmd_collect)

    # Status command
    status_parser = subparsers.add_parser(
        "status", help="Show database status and statistics"
    )
    status_parser.set_defaults(func=cmd_status)

    # Cleanup command
    cleanup_parser = subparsers.add_parser("cleanup", help="Clean up old position data")
    cleanup_parser.add_argument(
        "--days",
        type=int,
        default=30,
        help="Remove positions older than this many days (default: 30)",
    )
    cleanup_parser.set_defaults(func=cmd_cleanup)

    # Config command
    config_parser = subparsers.add_parser(
        "config", help="Create sample configuration file"
    )
    config_parser.add_argument(
        "--config-path",
        default=".env",
        help="Path to configuration file (default: .env)",
    )
    config_parser.set_defaults(func=cmd_config)

    # Dashboard command
    dashboard_parser = subparsers.add_parser(
        "dashboard", help="Launch the Streamlit dashboard"
    )
    dashboard_parser.add_argument(
        "--use-db",
        action="store_true",
        help="Use database mode instead of API mode"
    )
    dashboard_parser.set_defaults(func=cmd_dashboard)

    args = parser.parse_args()

    # Setup logging
    setup_logging(args.log_level)

    # If no command specified, show help
    if not args.command:
        parser.print_help()
        return 1

    # Load environment variables if .env file exists
    env_file = Path(".env")
    if env_file.exists():
        try:
            from dotenv import load_dotenv

            load_dotenv()
        except ImportError:
            pass  # dotenv not available, that's okay

    # Execute the command
    try:
        return args.func(args)
    except KeyboardInterrupt:
        print("\nInterrupted by user")
        return 1
    except Exception as e:
        logging.error(f"Unexpected error: {e}")
        return 1


if __name__ == "__main__":
    sys.exit(main())
