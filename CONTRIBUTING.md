# Contributing to Production to Development Data Anonymizer

Thank you for your interest in contributing to this project! This document provides guidelines for contributing.

## Development Setup

1. Clone the repository:
```bash
git clone https://github.com/listerguy/prod-to-dev-anonymizer.git
cd prod-to-dev-anonymizer
```

2. Create a virtual environment:
```bash
python -m venv venv
source venv/bin/activate  # On Windows: venv\Scripts\activate
```

3. Install dependencies:
```bash
pip install -r requirements.txt
```

4. Copy environment configuration:
```bash
cp .env.example .env
# Edit .env with your configuration
```

## Running Tests

Run the test suite:
```bash
python -m pytest
```

Run tests with coverage:
```bash
python -m pytest --cov=. --cov-report=html
```

## Code Style

This project follows PEP 8 style guidelines. Please ensure your code:
- Uses 4 spaces for indentation
- Has line lengths under 100 characters
- Includes docstrings for all public functions and classes
- Uses type hints where appropriate

## Testing Guidelines

- Write tests for all new functionality
- Ensure tests are isolated and don't depend on external services
- Use mocking for database and HTTP connections
- Aim for high test coverage

## Submitting Changes

1. Fork the repository
2. Create a feature branch: `git checkout -b feature/your-feature-name`
3. Make your changes and add tests
4. Ensure all tests pass
5. Commit your changes with a clear message
6. Push to your fork and submit a pull request

## Pull Request Guidelines

- Provide a clear description of the changes
- Reference any related issues
- Ensure CI checks pass
- Update documentation if needed
- Add tests for new functionality

## Reporting Issues

When reporting issues, please include:
- Python version
- Operating system
- Steps to reproduce the issue
- Expected vs actual behavior
- Any error messages or logs

## Security

If you discover a security vulnerability, please email the maintainers directly rather than opening a public issue.

## License

By contributing, you agree that your contributions will be licensed under the MIT License.
