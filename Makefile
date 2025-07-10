.PHONY: test test-unit test-integration test-all test-coverage clean help install lint format

# Default target
help:
	@echo "Available commands:"
	@echo "  make install          - Install dependencies"
	@echo "  make test             - Run unit tests (default)"
	@echo "  make test-unit        - Run unit tests only"
	@echo "  make test-integration - Run integration tests only"
	@echo "  make test-all         - Run all tests (unit + integration)"
	@echo "  make test-coverage    - Run tests with coverage report"
	@echo "  make lint             - Run code linting"
	@echo "  make format           - Format code"
	@echo "  make clean            - Clean up test artifacts"
	@echo "  make help             - Show this help message"

# Install dependencies
install:
	uv sync --group dev

# Run unit tests (default)
test: test-unit

# Run unit tests only
test-unit:
	@echo "Running unit tests..."
	uv run python -m pytest -m "not integration" -v

# Run integration tests only
test-integration:
	@echo "Running integration tests..."
	@echo "Make sure SPOT_FEED_ID environment variable is set!"
	uv run python -m pytest -m "integration" -v

# Run all tests
test-all:
	@echo "Running all tests..."
	uv run python -m pytest -v

# Run code linting
lint:
	@echo "Running code linting..."
	uv run ruff check .

# Format code
format:
	@echo "Formatting code..."
	uv run ruff format .

# Run tests with coverage
test-coverage:
	@echo "Running tests with coverage..."
	uv run python -m pytest -m "not integration" --cov=drifterdata --cov-report=term-missing --cov-report=html -v

# Clean up test artifacts
clean:
	@echo "Cleaning up test artifacts..."
	rm -rf .pytest_cache/
	rm -rf htmlcov/
	rm -rf .coverage
	find . -type d -name "__pycache__" -exec rm -rf {} + 2>/dev/null || true
	find . -type f -name "*.pyc" -delete 2>/dev/null || true
