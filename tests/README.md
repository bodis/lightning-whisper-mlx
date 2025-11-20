# Tests

## Run Tests

```bash
# Install dependencies
uv sync --extra test

# Run all tests
uv run pytest

# Run with coverage
uv run pytest --cov=lightning_whisper_mlx

# Run in parallel
uv run pytest -n auto
```

## Test Files

- `test_api.py` - Unit tests for API methods (30 tests)
- `test_cache_behavior.py` - Cache behavior tests with mocking (9 tests)
- `conftest.py` - Shared fixtures
