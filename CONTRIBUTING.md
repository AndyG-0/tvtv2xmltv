# Contributing to tvtv2xmltv

Thank you for your interest in contributing to tvtv2xmltv! This document provides guidelines and instructions for contributing.

## Development Setup

1. **Clone the repository**
   ```bash
   git clone https://github.com/AndyG-0/tvtv2xmltv.git
   cd tvtv2xmltv
   ```

2. **Install uv (if not already installed)**
   ```bash
   curl -LsSf https://astral.sh/uv/install.sh | sh
   ```

3. **Install dependencies**
   ```bash
   uv pip install -e ".[dev]"
   ```

4. **Run tests**
   ```bash
   PYTHONPATH=src uv run pytest tests/ -v
   ```

## Code Style

We use the following tools to maintain code quality:

- **Black** for code formatting
- **Flake8** for linting
- **Pytest** for testing

Before submitting a PR, please run:

```bash
# Format code
uv run black src/ tests/

# Lint code
uv run flake8 src/ --max-line-length=100

# Run tests with coverage
PYTHONPATH=src uv run pytest tests/ --cov=tvtv2xmltv --cov-report=term
```

## Testing

- Write tests for all new features
- Ensure all tests pass before submitting a PR
- Maintain or improve code coverage (currently at 78%)
- Tests are located in the `tests/` directory

## Pull Request Process

1. Fork the repository
2. Create a feature branch (`git checkout -b feature/amazing-feature`)
3. Make your changes
4. Write or update tests as needed
5. Ensure all tests pass
6. Run linting and formatting tools
7. Commit your changes (`git commit -m 'Add amazing feature'`)
8. Push to the branch (`git push origin feature/amazing-feature`)
9. Open a Pull Request

## Pull Request Guidelines

- Provide a clear description of the changes
- Reference any related issues
- Include test coverage for new features
- Update documentation as needed
- Follow the existing code style
- Keep changes focused and atomic

## Reporting Bugs

If you find a bug, please open an issue with:

- A clear description of the bug
- Steps to reproduce
- Expected behavior
- Actual behavior
- Environment details (OS, Python version, etc.)

## Feature Requests

We welcome feature requests! Please open an issue with:

- A clear description of the feature
- Use cases and benefits
- Any implementation ideas you have

## Code of Conduct

- Be respectful and inclusive
- Provide constructive feedback
- Focus on what's best for the project
- Show empathy towards other contributors

## Questions?

If you have questions, please:

- Check the README.md first
- Search existing issues
- Open a new issue if your question isn't answered

Thank you for contributing! 🎉
