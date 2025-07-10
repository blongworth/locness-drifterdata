#!/usr/bin/env python3
"""
Test runner for the drifterdata project.

This script provides convenient commands to run different types of tests.
"""

import os
import sys
import subprocess
import argparse
from pathlib import Path


def run_command(cmd, description=""):
    """Run a command and return the exit code."""
    if description:
        print(f"\n{'='*60}")
        print(f"Running: {description}")
        print(f"Command: {' '.join(cmd)}")
        print(f"{'='*60}")
    
    try:
        result = subprocess.run(cmd, check=False)
        return result.returncode
    except KeyboardInterrupt:
        print("\nTest run interrupted by user")
        return 1
    except Exception as e:
        print(f"Error running command: {e}")
        return 1


def main():
    """Main test runner function."""
    parser = argparse.ArgumentParser(description="Test runner for drifterdata project")
    
    # Add command line arguments
    parser.add_argument(
        "--unit", action="store_true",
        help="Run unit tests only"
    )
    parser.add_argument(
        "--integration", action="store_true",
        help="Run integration tests only (requires real SPOT API credentials)"
    )
    parser.add_argument(
        "--all", action="store_true",
        help="Run all tests (unit + integration)"
    )
    parser.add_argument(
        "--coverage", action="store_true",
        help="Run tests with coverage reporting"
    )
    parser.add_argument(
        "--verbose", "-v", action="store_true",
        help="Verbose output"
    )
    parser.add_argument(
        "--file", "-f", type=str,
        help="Run tests from specific file"
    )
    parser.add_argument(
        "--test", "-t", type=str,
        help="Run specific test function"
    )
    
    args = parser.parse_args()
    
    # Change to project directory
    project_dir = Path(__file__).parent
    os.chdir(project_dir)
    
    # Build base pytest command
    cmd = [sys.executable, "-m", "pytest"]
    
    # Add verbosity
    if args.verbose:
        cmd.append("-vv")
    
    # Add coverage if requested
    if args.coverage:
        cmd.extend(["--cov=drifterdata", "--cov-report=term-missing", "--cov-report=html"])
    
    # Determine which tests to run
    if args.unit:
        cmd.extend(["-m", "not integration"])
        description = "Unit Tests"
    elif args.integration:
        cmd.extend(["-m", "integration"])
        description = "Integration Tests"
    elif args.all:
        description = "All Tests"
    else:
        # Default to unit tests only
        cmd.extend(["-m", "not integration"])
        description = "Unit Tests (default)"
    
    # Add specific file or test if provided
    if args.file:
        cmd.append(f"tests/{args.file}")
        description += f" from {args.file}"
    elif args.test:
        cmd.extend(["-k", args.test])
        description += f" matching {args.test}"
    
    # Run the tests
    exit_code = run_command(cmd, description)
    
    # Print summary
    if exit_code == 0:
        print(f"\n✅ {description} completed successfully!")
    else:
        print(f"\n❌ {description} failed with exit code {exit_code}")
    
    # Show integration test instructions if unit tests passed
    if exit_code == 0 and not args.integration and not args.all:
        print("\n" + "="*60)
        print("To run integration tests against real SPOT API:")
        print("1. Set environment variables:")
        print("   export SPOT_FEED_ID=your_real_feed_id")
        print("   export SPOT_FEED_PASSWORD=your_password  # if required")
        print("2. Run: python run_tests.py --integration")
        print("="*60)
    
    return exit_code


if __name__ == "__main__":
    exit_code = main()
    sys.exit(exit_code)
