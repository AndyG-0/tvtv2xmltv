# Copilot Instructions for tvtv2xmltv

## Python Dependency Management

* **IMPORTANT!!! Always use uv to run python commands and to manage dependencies.**
* Use `uv pip install` for installing packages
* Use `uv run` for running Python scripts and commands
* All dependencies are managed in `pyproject.toml`

## Code Quality and Linting

### Before Committing Code

**ALWAYS run the following checks before committing any code changes:**

1. **Black Formatter** (Code formatting):
   ```bash
   uv run black src/ tests/ example_usage.py
   ```
   - Line length: 100 characters
   - All Python files must be formatted with Black
   - Run `black --check` to verify without modifying files

2. **Flake8** (Style guide enforcement):
   ```bash
   uv run flake8 src/ tests/ --max-line-length=100
   ```
   - Must pass with no errors
   - Maximum line length: 100 characters
   - Follows PEP 8 style guide

3. **Pylint** (Code analysis):
   ```bash
   uv run pylint src/tvtv2xmltv/ --max-line-length=100
   ```
   - Should have minimal warnings
   - Address critical issues before committing

### Complete Linting Command

Run all linters in sequence:
```bash
uv run black src/ tests/ example_usage.py && \
uv run flake8 src/ tests/ --max-line-length=100 && \
uv run pylint src/tvtv2xmltv/ --max-line-length=100
```

## Testing

### Running Tests

**ALWAYS run tests before committing code changes:**

```bash
# Run all tests with verbose output
PYTHONPATH=src uv run pytest tests/ -v

# Run tests with coverage report
PYTHONPATH=src uv run pytest tests/ --cov=src/tvtv2xmltv --cov-report=term-missing

# Run specific test file
PYTHONPATH=src uv run pytest tests/test_config.py -v

# Run specific test function
PYTHONPATH=src uv run pytest tests/test_config.py::test_config_defaults -v
```

### Test Requirements

- All tests must pass before committing
- Maintain or improve code coverage
- Write tests for all new features
- Tests are located in the `tests/` directory

### Complete Pre-Commit Workflow

Run linting and tests together:
```bash
uv run black src/ tests/ example_usage.py && \
uv run flake8 src/ tests/ --max-line-length=100 && \
PYTHONPATH=src uv run pytest tests/ -v
```

## Security Scanning

Run security checks periodically:
```bash
uv run bandit -r src/ -f screen
uv run safety check
```

## Code Standards

- Use timezone-aware datetime objects (prefer `datetime.now(timezone.utc)`)
- Add error handling for external API calls and environment variable parsing
- Use type hints where appropriate
- Follow existing code patterns and structure
- Document complex logic with clear comments
- Keep functions focused and modular
