# Contributing to Data Space Inetum

Thank you for your interest in contributing! This guide will help you get started.

## Code of Conduct

- Be respectful and inclusive
- Welcome newcomers
- Focus on constructive feedback
- Report issues professionally

## Getting Started

1. Fork the repository
2. Clone your fork: `git clone https://github.com/YOUR_USERNAME/data-space-inetum.git`
3. Add upstream remote: `git remote add upstream https://github.com/yisus189/data-space-inetum.git`
4. Create a feature branch: `git checkout -b feature/my-feature`

## Development Setup

### Backend

```bash
# Create virtual environment
python -m venv .venv
source .venv/bin/activate  # Windows: .venv\Scripts\activate

# Install dependencies
pip install -r requirements.txt

# Run tests
pytest tests/ -v

# Run linters
black src/ tests/
flake8 src/ tests/
```

### Frontend

```bash
cd frontend

# Install dependencies
npm install

# Run development server
npm run dev

# Run linter
npm run lint
```

## Making Changes

### Backend (Python)

1. **Follow PEP 8** style guide
2. **Use type hints** where appropriate
3. **Write docstrings** for functions and classes
4. **Add tests** for new functionality
5. **Update API docs** if adding/changing endpoints

Example:
```python
def create_dataset(
    db: Session, 
    provider_id: str, 
    title: str, 
    description: str
) -> Dataset:
    """Create a new dataset.
    
    Args:
        db: Database session
        provider_id: Provider UUID
        title: Dataset title
        description: Dataset description
        
    Returns:
        Created dataset instance
    """
    # Implementation
```

### Frontend (TypeScript/React)

1. **Use TypeScript** for type safety
2. **Follow React best practices**
3. **Use Material-UI components** consistently
4. **Keep components small and focused**
5. **Add prop types** and documentation

Example:
```typescript
interface DatasetCardProps {
  dataset: Dataset;
  onPublish?: (id: string) => void;
  showActions?: boolean;
}

/**
 * Display dataset information in a card format
 */
export function DatasetCard({ dataset, onPublish, showActions }: DatasetCardProps) {
  // Implementation
}
```

## Testing

### Backend Tests

```bash
# Run all tests
pytest tests/ -v

# Run specific test file
pytest tests/test_storage.py -v

# Run with coverage
pytest tests/ --cov=src --cov-report=html
```

### Writing Tests

Use pytest fixtures and mocks:

```python
def test_create_dataset(mock_db):
    """Test dataset creation."""
    dataset = create_dataset(
        mock_db,
        provider_id="test-id",
        title="Test Dataset",
        description="Test"
    )
    assert dataset.title == "Test Dataset"
```

### E2E Tests

```bash
# Start services
docker-compose up -d

# Run smoke tests
python tests/smoke_test.py
```

## Commit Messages

Use conventional commits format:

```
<type>(<scope>): <subject>

<body>

<footer>
```

Types:
- `feat`: New feature
- `fix`: Bug fix
- `docs`: Documentation changes
- `style`: Code style changes (formatting)
- `refactor`: Code refactoring
- `test`: Adding tests
- `chore`: Maintenance tasks

Examples:
```
feat(datasets): add presigned URL upload support

Implement presigned URL generation for direct client-to-MinIO uploads.
This improves performance for large file uploads.

Closes #123
```

```
fix(auth): handle expired JWT tokens gracefully

Add proper error handling for expired tokens and return 401 status.
```

## Pull Request Process

1. **Update your branch** from upstream main:
   ```bash
   git fetch upstream
   git rebase upstream/main
   ```

2. **Run tests and linters**:
   ```bash
   pytest tests/ -v
   black src/ tests/
   flake8 src/ tests/
   ```

3. **Push to your fork**:
   ```bash
   git push origin feature/my-feature
   ```

4. **Create Pull Request**:
   - Clear title and description
   - Reference related issues
   - Include screenshots for UI changes
   - Ensure CI passes

5. **Code Review**:
   - Address review comments
   - Keep discussion professional
   - Be open to suggestions

## Project Structure

```
data-space-inetum/
├── src/
│   ├── app/
│   │   ├── middleware/     # Request middleware
│   │   └── routers/        # API endpoints
│   ├── auth/              # Authentication
│   ├── db/                # Database models and repos
│   ├── storage/           # MinIO/S3 client
│   ├── config.py          # Configuration
│   ├── logging.py         # Logging setup
│   └── main.py            # FastAPI app
├── frontend/
│   ├── src/
│   │   ├── app/           # Next.js pages
│   │   ├── components/    # React components
│   │   ├── lib/           # Utilities
│   │   └── hooks/         # Custom hooks
├── tests/                 # Backend tests
├── docs/                  # Documentation
└── scripts/               # Utility scripts
```

## Adding New Features

### Backend Endpoint

1. Create router in `src/app/routers/`
2. Add business logic to repository
3. Update database models if needed
4. Write unit tests
5. Update API documentation
6. Add to `src/main.py`

### Frontend Component

1. Create component in `src/components/`
2. Add TypeScript types
3. Import and use in pages
4. Update theme if needed
5. Test responsiveness

### Database Model

1. Add model to `src/db/models.py`
2. Create migration script
3. Update repositories
4. Write tests
5. Update documentation

## Documentation

- Update README.md for major features
- Add API docs in docs/API.md
- Create guides in docs/guides/
- Add inline code comments for complex logic
- Update OpenAPI/Swagger docs

## Security

- **Never commit secrets** or credentials
- **Use environment variables** for configuration
- **Validate all inputs** on backend
- **Sanitize user data** before display
- **Follow OWASP guidelines**
- **Report security issues** privately

## Questions?

- Open an issue for bugs
- Start a discussion for questions
- Check existing issues first
- Provide detailed information

## License

By contributing, you agree that your contributions will be licensed under the Apache License 2.0.
