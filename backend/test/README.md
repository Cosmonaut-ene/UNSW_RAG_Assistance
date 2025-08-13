# UNSW CSE Chatbot Backend Test Suite

Comprehensive unit and integration tests for the UNSW CSE Open Day Chatbot backend system.

## 🎯 Test Coverage Overview

This test suite provides **85%+ code coverage** across all backend modules with comprehensive testing of:

- **AI Modules**: LLM clients, prompt management, query enhancement, safety checking
- **RAG System**: Vector store operations, BM25 search, hybrid search algorithms
- **Services**: Authentication, caching, logging, query processing
- **API Routes**: User endpoints, admin endpoints with authentication
- **Integration**: End-to-end workflows and error handling

## 📁 Test Structure

```
backend/test/
├── conftest.py                    # Pytest fixtures & configuration
├── pytest.ini                    # Test runner configuration
├── requirements-test.txt          # Testing dependencies
├── unit/                         # Unit tests (isolated components)
│   ├── test_ai/                  # AI module tests
│   ├── test_rag/                 # RAG system tests
│   ├── test_services/            # Service layer tests
│   └── test_routes/              # API endpoint tests
├── integration/                  # Integration tests
│   └── test_query_flow.py        # End-to-end workflows
└── mocks/                        # Mock implementations
    ├── mock_llm.py               # Google Gemini mocks
    └── mock_vector_store.py      # ChromaDB mocks
```

## 🚀 Quick Start

### Install Test Dependencies

```bash
cd backend
pip install -r test/requirements-test.txt
```

### Run All Tests

```bash
# Run complete test suite with coverage
pytest test/ --cov=. --cov-report=html

# Run specific test categories
pytest test/unit/ -v                    # Unit tests only
pytest test/integration/ -v             # Integration tests only
pytest -m "ai" -v                      # AI module tests only
pytest -m "rag" -v                     # RAG system tests only
pytest -m "services" -v                # Service tests only
```

### Quick Verification

```bash
# Fast smoke test (skip slow tests)
pytest test/unit/test_ai/ -v --durations=0
```

## 📊 Test Categories & Markers

### Test Markers

Use pytest markers to run specific test categories:

```bash
pytest -m unit          # Unit tests only
pytest -m integration   # Integration tests only
pytest -m slow          # Long-running tests
pytest -m ai            # AI module tests
pytest -m rag           # RAG system tests
pytest -m services      # Service layer tests
pytest -m auth          # Authentication tests
pytest -m performance   # Performance tests
```

### Test Types

- **Unit Tests**: Test individual functions/classes in isolation
- **Integration Tests**: Test component interactions and workflows
- **Performance Tests**: Verify response times and resource usage
- **Edge Case Tests**: Handle error conditions and malformed inputs

## 🛠 Key Testing Features

### Comprehensive Mocking

All external dependencies are mocked:

- **Google Gemini API**: Predictable responses for different query types
- **ChromaDB**: In-memory vector store with realistic operations
- **File System**: Temporary directories for safe testing
- **Network Requests**: Controlled responses for scraping tests

### Realistic Test Data

- Sample UNSW course information and documents
- Realistic conversation histories and user sessions
- Various query types (course info, locations, greetings, etc.)
- Edge cases with special characters and unicode

### Performance Validation

- Response time limits (< 5 seconds for queries, < 100ms for cache hits)
- Memory usage monitoring
- Concurrent access testing
- Large dataset handling

## 🧪 Test Scenarios Covered

### Happy Path Tests ✅

- Successful query processing with RAG
- Cache hits and misses
- Valid authentication flows
- Proper document indexing and search
- Hybrid search result combination

### Sad Path Tests ❌

- External API failures (Google Gemini, ChromaDB)
- Network timeouts and connection errors
- Invalid user inputs and malformed queries
- Authentication failures and expired tokens
- Empty search results and fallback scenarios

### Edge Cases 🔄

- Unicode characters in queries
- Very long input texts
- Concurrent access scenarios
- Resource exhaustion conditions
- Malformed configuration files

## 📈 Coverage Reports

### Generate Coverage Reports

```bash
# HTML report (detailed, browse at htmlcov/index.html)
pytest test/ --cov=. --cov-report=html

# Terminal report (summary)
pytest test/ --cov=. --cov-report=term-missing

# XML report (for CI/CD)
pytest test/ --cov=. --cov-report=xml
```

### Coverage Targets

- **Overall**: 85%+ code coverage
- **Critical paths**: 95%+ (auth, query processing, safety)
- **Business logic**: 90%+ (AI modules, services)
- **Utilities**: 80%+ (scrapers, helpers)

## 🔧 Testing Configuration

### Environment Variables

Tests use mocked environment variables by default:

```bash
GOOGLE_API_KEY=test-google-api-key
ADMIN_EMAIL=test@unsw.edu.au
ADMIN_PASSWORD=test-password
SECRET_KEY=test-secret-key
```

### Test Database

Tests use temporary, in-memory databases that are:

- Created fresh for each test
- Automatically cleaned up
- Isolated between test runs
- Pre-populated with realistic data

## 🚨 Common Issues & Solutions

### Issue: Tests fail with "ModuleNotFoundError"

**Solution**: Ensure you're running from the backend directory:
```bash
cd backend
pytest test/
```

### Issue: ChromaDB connection errors

**Solution**: Tests use mocked ChromaDB. If you see real connection errors, check imports:
```bash
# Verify mocks are being used
pytest test/unit/test_rag/test_vector_store.py -v -s
```

### Issue: Google API authentication errors

**Solution**: Tests mock all Google APIs. Real API calls indicate missing mocks:
```bash
# Check mock configuration in conftest.py
grep -n "mock_google" test/conftest.py
```

### Issue: Slow test execution

**Solution**: Run specific test categories or use markers:
```bash
# Skip slow integration tests
pytest test/unit/ -v

# Run only fast tests
pytest -m "not slow" -v
```

## 📋 Test Maintenance

### Adding New Tests

1. **Unit Tests**: Add to appropriate `test/unit/test_*/` directory
2. **Integration Tests**: Add to `test/integration/`
3. **Mocks**: Update mocks in `test/mocks/` for new dependencies
4. **Fixtures**: Add reusable test data to `conftest.py`

### Test Naming Conventions

```python
def test_function_name_with_happy_path():          # Happy path
def test_function_name_with_invalid_input():       # Sad path  
def test_function_name_with_edge_case():           # Edge case
def test_function_name_integration():              # Integration
def test_function_name_performance():              # Performance
```

### Mock Updates

When backend code changes:

1. Update corresponding mocks in `test/mocks/`
2. Verify mock behavior matches real API
3. Update test expectations if needed
4. Run full test suite to catch regressions

## 🎯 Quality Gates

All tests must pass these quality gates:

- ✅ **85%+ code coverage** across all modules
- ✅ **All unit tests pass** (isolated component testing)
- ✅ **All integration tests pass** (workflow testing)
- ✅ **Performance benchmarks met** (< 5s query processing)
- ✅ **No security vulnerabilities** in test code
- ✅ **Proper error handling** tested

## 🔄 Continuous Integration

This test suite is designed for CI/CD integration:

```bash
# CI command for full validation
pytest test/ \
  --cov=. \
  --cov-report=xml \
  --cov-fail-under=85 \
  --junit-xml=test-results.xml \
  --maxfail=5 \
  --tb=short
```

## 📞 Support

For test-related questions:

1. Check existing test files for similar scenarios
2. Review mock implementations for external dependencies
3. Consult `conftest.py` for available fixtures
4. Run specific tests with `-v -s` for detailed output

---

**Built with pytest, comprehensive mocking, and ❤️ for quality code!**