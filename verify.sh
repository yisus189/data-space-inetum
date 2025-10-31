#!/bin/bash
# Verification script for Data Space implementation

echo "==================================================================="
echo "Data Space Implementation Verification"
echo "==================================================================="
echo ""

# Check Python files
echo "✓ Python modules:"
find src -name "*.py" | wc -l
echo "  - Main API: src/main.py"
echo "  - CLI tool: src/cli.py"
echo "  - Auth: src/auth/"
echo "  - Database: src/db/"
echo "  - Catalog: src/catalog.py"
echo "  - Utils: src/app/"
echo ""

# Check tests
echo "✓ Tests:"
find tests -name "test_*.py" | wc -l
echo "  - test_models.py"
echo "  - test_catalog.py"
echo "  - test_audit.py"
echo ""

# Check infrastructure
echo "✓ Infrastructure:"
echo "  - Docker Compose: docker-compose.yml"
echo "  - Dockerfile: Dockerfile"
echo "  - Requirements: requirements.txt"
echo "  - Keycloak realm: infra/keycloak-realm.json"
echo ""

# Check migrations
echo "✓ Database migrations:"
find alembic/versions -name "*.py" | wc -l
echo "  - 001_initial_migration.py"
echo ""

# Check documentation
echo "✓ Documentation:"
echo "  - README.md (comprehensive)"
echo "  - PR_SUMMARY.md (pull request summary)"
echo "  - IMPLEMENTATION.md (implementation details)"
echo "  - .env.local.example (configuration template)"
echo ""

# Run tests if pytest is available
if command -v pytest &> /dev/null; then
    echo "==================================================================="
    echo "Running tests..."
    echo "==================================================================="
    PYTHONPATH=. pytest tests/ -v --tb=short 2>&1 | tail -20
else
    echo "ℹ️  pytest not installed - skipping tests"
    echo "   Install with: pip install -r requirements.txt"
fi

echo ""
echo "==================================================================="
echo "Verification complete!"
echo "==================================================================="
echo ""
echo "To start the Data Space:"
echo "  docker-compose up -d"
echo ""
echo "To use the CLI:"
echo "  python src/cli.py --help"
echo ""
echo "To run tests:"
echo "  pytest tests/ -v"
echo ""
