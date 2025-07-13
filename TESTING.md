# Testing Documentation

## Overview

This document describes the comprehensive testing setup for the drifterdata project, which includes unit tests, integration tests, and automated testing workflows.

## Test Structure

### Test Files

- **`tests/test_spot_tracker.py`**: Tests for the SpotTrackerAPI class
- **`tests/test_spot_position.py`**: Tests for the SpotPosition data model
- **`tests/test_integration.py`**: Integration tests against real SPOT API
- **`tests/conftest.py`**: Test configuration and fixtures

### Test Categories

#### Unit Tests
- **Scope**: Test individual components in isolation
- **Mocking**: All external API calls are mocked
- **Coverage**: Comprehensive test coverage for all API methods
- **Speed**: Fast execution (< 1 second)

#### Integration Tests
- **Scope**: Test against real SPOT API endpoints
- **Requirements**: Valid SPOT_FEED_ID environment variable
- **Optional**: Password-protected feeds require SPOT_FEED_PASSWORD
- **Usage**: Verify actual API compatibility

## Running Tests

### Quick Start
```bash
# Install dependencies
uv sync --group dev

# Run unit tests (default)
make test

# Run all available commands
make help
```

### Test Commands

#### Unit Tests
```bash
# Method 1: Using Makefile (recommended)
make test

# Method 2: Using pytest directly
uv run python -m pytest -m "not integration" -v

# Method 3: Using test runner script
python run_tests.py --unit
```

#### Integration Tests
```bash
# Set environment variables first
export SPOT_FEED_ID=your_real_feed_id
export SPOT_FEED_PASSWORD=your_password  # if required

# Run integration tests
make test-integration
uv run python -m pytest -m "integration" -v
python run_tests.py --integration
```

#### Coverage Reports
```bash
# Generate coverage report
make test-coverage

# View HTML coverage report
open htmlcov/index.html
```

## Test Features

### Comprehensive Mocking
- All HTTP requests are mocked in unit tests
- Mock data includes realistic SPOT API responses
- Error conditions are simulated (network errors, HTTP errors, invalid JSON)

### Error Handling Tests
- Connection failures
- HTTP error responses (404, 500, etc.)
- Invalid JSON responses
- Missing required fields
- Invalid timestamp formats

### Data Validation Tests
- Timestamp parsing from various formats (ISO, Unix, string formats)
- Coordinate validation and type conversion
- Required field validation
- Optional field handling

### API Method Tests
- **get_latest_position()**: Latest position retrieval
- **get_messages()**: Message retrieval with pagination
- **test_connection()**: Connection testing

## Integration Test Features

### Real API Testing
- Tests against actual SPOT API endpoints
- Validates real response formats
- Checks data type consistency
- Verifies API behavior changes

### Conditional Execution
- Skips tests if no credentials provided
- Handles both public and password-protected feeds
- Graceful handling of API errors

### Pagination Testing
- Tests pagination functionality
- Verifies no data overlap between pages
- Handles edge cases (empty results, invalid pages)

## Test Configuration

### pytest Configuration (pyproject.toml)
```toml
[tool.pytest.ini_options]
testpaths = ["tests"]
markers = [
    "integration: marks tests as integration tests",
    "unit: marks tests as unit tests",
    "slow: marks tests as slow tests",
]
addopts = ["-v", "--tb=short", "--strict-markers"]
```

### Test Markers
- `@pytest.mark.integration`: Integration tests
- `@pytest.mark.unit`: Unit tests (default)
- `@pytest.mark.slow`: Slow tests (can be skipped)

## Continuous Integration

### GitHub Actions
- **File**: `.github/workflows/tests.yml`
- **Triggers**: Push to main/develop, pull requests
- **Matrix**: Python 3.11 and 3.12
- **Coverage**: Uploads to Codecov

### Workflow Jobs
1. **Unit Tests**: Run on all Python versions
2. **Linting**: Code style and format checking
3. **Integration Tests**: Run on main branch pushes only

## Code Quality

### Linting and Formatting
```bash
# Check code style
make lint
uv run ruff check .

# Format code
make format
uv run ruff format .
```

### Coverage Requirements
- Target: >90% test coverage
- Reports: HTML and XML formats
- Integration: Codecov for coverage tracking

## Test Data

### Mock Responses
- Realistic SPOT API response structures
- Multiple message formats (single and multiple messages)
- Error response formats
- Empty response handling

### Test Fixtures
- Pre-configured API instances
- Mock response data
- Environment variable setup
- Isolated test environments

## Best Practices

### Writing Tests
1. **Isolation**: Each test should be independent
2. **Naming**: Use descriptive test names
3. **AAA Pattern**: Arrange, Act, Assert
4. **Mocking**: Mock external dependencies
5. **Edge Cases**: Test error conditions

### Test Organization
1. **Group Related Tests**: Use test classes
2. **Fixtures**: Reuse common setup code
3. **Parameterization**: Test multiple scenarios
4. **Clear Documentation**: Document test purpose

## Troubleshooting

### Common Issues
1. **Environment Variables**: Ensure test environment variables are set
2. **Mock Issues**: Check mock setup and return values
3. **Integration Tests**: Verify SPOT API credentials
4. **Coverage**: Ensure all code paths are tested

### Debug Commands
```bash
# Run specific test
uv run python -m pytest tests/test_spot_tracker.py::TestSpotTrackerAPI::test_get_latest_position_success -v

# Run with debug output
uv run python -m pytest --tb=long -s

# Run with coverage debug
uv run python -m pytest --cov=drifterdata --cov-report=term-missing -v
```

## Performance

### Test Execution Times
- Unit tests: < 1 second
- Integration tests: 5-10 seconds (depends on API response time)
- Coverage tests: < 2 seconds

### Optimization
- Parallel test execution where possible
- Efficient mock setup
- Minimal test data
- Fast assertions

## Future Enhancements

### Planned Improvements
1. **Property-based Testing**: Use hypothesis for more comprehensive testing
2. **Performance Tests**: Add performance benchmarks
3. **Database Tests**: Add database integration tests
4. **Mock Server**: Use mock server for more realistic API testing
5. **Mutation Testing**: Add mutation testing for test quality
