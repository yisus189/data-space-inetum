# Contributing to Data Space Inetum

Thank you for your interest in contributing to the Data Space project!

## Development Setup

### Prerequisites

- Python 3.11+
- Docker and Docker Compose
- Git
- PostgreSQL client (optional, for local development)

### Getting Started

1. **Fork and clone the repository**

```bash
git clone https://github.com/yisus189/data-space-inetum.git
cd data-space-inetum
```

2. **Create a virtual environment**

```bash
python -m venv venv
source venv/bin/activate  # On Windows: venv\Scripts\activate
```

3. **Install dependencies**

```bash
pip install -e .[dev]
```

4. **Set up environment variables**

```bash
cp .env.local.example .env.local
# Edit .env.local with your configuration
```

5. **Start the infrastructure**

```bash
docker-compose up -d
# Or use the quick start script
./quickstart.sh
```

## Making Changes

### Code Style

- Follow PEP 8 guidelines
- Use type hints where appropriate
- Write docstrings for functions and classes
- Keep functions small and focused

### Project Structure

```
src/
├── app/          # Application logic (schemas, audit, transfers)
├── db/           # Database models and configuration
├── auth/         # Authentication and authorization
├── catalog/      # OpenMetadata integration
└── main.py       # FastAPI application
```

### Commit Messages

Use conventional commit format:

- `feat:` New features
- `fix:` Bug fixes
- `docs:` Documentation changes
- `test:` Test additions or modifications
- `refactor:` Code refactoring
- `style:` Code style changes
- `chore:` Build process or auxiliary tool changes

Examples:
```
feat: add endpoint for bulk publication import
fix: resolve authentication token expiration issue
docs: update API usage examples in README
```

### Testing

Run tests before submitting:

```bash
# Run all tests
pytest

# Run with coverage
pytest --cov=src --cov-report=html

# Run specific test file
pytest tests/test_api.py -v
```

### Database Migrations

When modifying models:

```bash
# Create a new migration
alembic revision --autogenerate -m "Add new field to Publication"

# Apply migrations
alembic upgrade head

# Review the migration before committing
```

## Pull Request Process

1. **Create a feature branch**

```bash
git checkout -b feature/your-feature-name
```

2. **Make your changes**

- Write tests for new functionality
- Update documentation
- Ensure all tests pass
- Follow code style guidelines

3. **Commit your changes**

```bash
git add .
git commit -m "feat: add your feature description"
```

4. **Push to your fork**

```bash
git push origin feature/your-feature-name
```

5. **Create a Pull Request**

- Provide a clear description of the changes
- Reference any related issues
- Ensure CI passes

## Development Workflow

### Using Make commands

```bash
make help          # Show all available commands
make dev           # Run development server
make test          # Run tests
make lint          # Check code style
make up            # Start docker services
make down          # Stop docker services
make migration     # Create new migration
make migrate       # Apply migrations
```

### Local Development

```bash
# Start services
docker-compose up -d

# Run API locally (connects to containerized DB)
uvicorn src.main:app --reload

# View logs
docker-compose logs -f api
```

### Testing Changes

```bash
# Unit tests
pytest tests/test_models.py

# Integration tests
pytest tests/test_api.py

# With coverage
pytest --cov=src --cov-report=term-missing
```

## Areas for Contribution

### High Priority

- [ ] Enhanced error handling and validation
- [ ] Additional authentication providers
- [ ] Advanced contract templates
- [ ] Data quality checks before transfers
- [ ] Notification system for events

### Documentation

- [ ] API usage examples
- [ ] Architecture diagrams
- [ ] Deployment guides for different platforms
- [ ] Translation to other languages

### Testing

- [ ] Increase test coverage
- [ ] Performance tests
- [ ] Security tests
- [ ] Integration tests with real services

### Infrastructure

- [ ] Kubernetes deployment manifests
- [ ] Terraform configurations
- [ ] Monitoring and alerting setup
- [ ] Backup and disaster recovery procedures

## Code Review

All contributions require code review:

- At least one approval from a maintainer
- All CI checks must pass
- Code coverage should not decrease
- Documentation must be updated

## Questions or Issues?

- Open an issue for bugs or feature requests
- Use discussions for questions and ideas
- Join our community channels (if available)

## License

By contributing, you agree that your contributions will be licensed under the Apache-2.0 License.

## Code of Conduct

- Be respectful and inclusive
- Provide constructive feedback
- Focus on what is best for the community
- Show empathy towards other community members

Thank you for contributing to Data Space Inetum!
