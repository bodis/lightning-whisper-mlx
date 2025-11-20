"""
Pytest configuration and shared fixtures for Lightning Whisper MLX tests.
"""

import pytest
from lightning_whisper_mlx import LightningWhisperMLX
from lightning_whisper_mlx.transcribe import ModelHolder


@pytest.fixture(autouse=True)
def reset_model_cache():
    """
    Automatically reset the model cache before and after each test.

    This ensures test isolation - no test can affect another test's
    cache state.
    """
    # Before test: clear cache and reset to default
    ModelHolder.clear_cache()
    ModelHolder.set_cache_size(1)

    yield

    # After test: clear cache and reset to default
    ModelHolder.clear_cache()
    ModelHolder.set_cache_size(1)


@pytest.fixture
def cache_size_2():
    """Fixture that sets cache size to 2 for the test."""
    LightningWhisperMLX.set_model_cache_size(2)
    yield 2


@pytest.fixture
def cache_size_3():
    """Fixture that sets cache size to 3 for the test."""
    LightningWhisperMLX.set_model_cache_size(3)
    yield 3


@pytest.fixture
def sample_models():
    """
    Returns a list of sample model names for testing.

    These are lightweight models that can be used for testing
    without requiring large downloads.
    """
    return ["distil-small.en", "small", "base"]


@pytest.fixture
def test_model_name():
    """Returns a single lightweight model name for basic testing."""
    return "distil-small.en"
