"""
Integration tests for model cache behavior.

These tests directly test the ModelHolder cache mechanism with mock models.
"""

import pytest
import time
from unittest.mock import Mock, MagicMock, patch
import mlx.core as mx
from lightning_whisper_mlx import LightningWhisperMLX
from lightning_whisper_mlx.transcribe import ModelHolder


@pytest.fixture
def mock_model():
    """Create a mock Whisper model."""
    model = Mock()
    model.dims = Mock()
    model.dims.n_mels = 80
    return model


class TestDefaultCacheBehavior:
    """Test default cache behavior (cache size = 1)."""

    def test_single_model_cached(self, mock_model):
        """Test that a single model stays in cache."""
        # Load model into cache
        with patch('lightning_whisper_mlx.transcribe.load_model', return_value=mock_model):
            cached_model = ModelHolder.get_model("./test_model_1", mx.float16)

        # Check cache
        assert ModelHolder.get_cached_count() == 1
        info = ModelHolder.get_cache_info()
        assert info['current_size'] == 1
        assert info['max_size'] == 1

    def test_second_model_evicts_first(self, mock_model):
        """Test that loading second model evicts first (cache size = 1)."""
        # Load first model
        with patch('lightning_whisper_mlx.transcribe.load_model', return_value=mock_model):
            model1 = ModelHolder.get_model("./test_model_1", mx.float16)
            assert ModelHolder.get_cached_count() == 1

            # Load second model - should evict first
            model2 = ModelHolder.get_model("./test_model_2", mx.float16)
            assert ModelHolder.get_cached_count() == 1

        # Verify second model is in cache
        info = ModelHolder.get_cache_info()
        assert len(info['models']) == 1
        assert "./test_model_2" in info['models'][0]['model_path']


class TestMultiModelCaching:
    """Test caching multiple models (cache size = 2)."""

    def test_two_models_both_cached(self, cache_size_2, mock_model):
        """Test that two models can be cached simultaneously."""
        with patch('lightning_whisper_mlx.transcribe.load_model', return_value=mock_model):
            # Load first model
            model1 = ModelHolder.get_model("./test_model_1", mx.float16)
            assert ModelHolder.get_cached_count() == 1

            time.sleep(0.01)  # Ensure different timestamps

            # Load second model
            model2 = ModelHolder.get_model("./test_model_2", mx.float16)
            assert ModelHolder.get_cached_count() == 2

        # Both should be in cache
        info = ModelHolder.get_cache_info()
        assert info['current_size'] == 2
        assert info['max_size'] == 2

    def test_reaccessing_model_updates_timestamp(self, cache_size_2, mock_model):
        """Test that re-accessing a model updates its timestamp."""
        with patch('lightning_whisper_mlx.transcribe.load_model', return_value=mock_model):
            # Load two models
            model1 = ModelHolder.get_model("./test_model_1", mx.float16)
            time.sleep(0.01)
            model2 = ModelHolder.get_model("./test_model_2", mx.float16)

            # Get initial timestamp for first model
            info1 = ModelHolder.get_cache_info()
            model1_time = next(
                m['last_access'] for m in info1['models']
                if "./test_model_1" in m['model_path']
            )

            time.sleep(0.01)

            # Re-access first model
            model1_again = ModelHolder.get_model("./test_model_1", mx.float16)

            # Timestamp should be updated
            info2 = ModelHolder.get_cache_info()
            model1_time_new = next(
                m['last_access'] for m in info2['models']
                if "./test_model_1" in m['model_path']
            )

            assert model1_time_new > model1_time

    def test_lru_eviction(self, cache_size_2, mock_model):
        """Test that LRU eviction works correctly."""
        with patch('lightning_whisper_mlx.transcribe.load_model', return_value=mock_model):
            # Load two models
            model1 = ModelHolder.get_model("./test_model_1", mx.float16)
            time.sleep(0.01)
            model2 = ModelHolder.get_model("./test_model_2", mx.float16)
            time.sleep(0.01)

            # Re-access first model (updates its timestamp)
            model1_again = ModelHolder.get_model("./test_model_1", mx.float16)
            time.sleep(0.01)

            # Load third model - should evict second (LRU)
            model3 = ModelHolder.get_model("./test_model_3", mx.float16)

        # Check cache
        assert ModelHolder.get_cached_count() == 2
        info = ModelHolder.get_cache_info()

        # First and third should be cached, second evicted
        cached_paths = [m['model_path'] for m in info['models']]
        assert any("./test_model_1" in path for path in cached_paths)
        assert any("./test_model_3" in path for path in cached_paths)
        assert not any("./test_model_2" in path for path in cached_paths)


class TestCacheClearing:
    """Test manual cache clearing."""

    def test_clear_cache_removes_all_models(self, cache_size_2, mock_model):
        """Test that clear_cache removes all models."""
        with patch('lightning_whisper_mlx.transcribe.load_model', return_value=mock_model):
            # Load two models
            model1 = ModelHolder.get_model("./test_model_1", mx.float16)
            model2 = ModelHolder.get_model("./test_model_2", mx.float16)
            assert ModelHolder.get_cached_count() == 2

        # Clear cache
        ModelHolder.clear_cache()

        # Cache should be empty
        assert ModelHolder.get_cached_count() == 0
        info = ModelHolder.get_cache_info()
        assert info['current_size'] == 0
        assert len(info['models']) == 0


class TestCacheInfo:
    """Test cache info reporting."""

    def test_cache_info_with_models(self, cache_size_2, mock_model):
        """Test that cache info contains correct model information."""
        with patch('lightning_whisper_mlx.transcribe.load_model', return_value=mock_model):
            # Load model
            model = ModelHolder.get_model("./test_model_1", mx.float16)

        # Get cache info
        info = ModelHolder.get_cache_info()

        assert info['current_size'] == 1
        assert info['max_size'] == 2
        assert len(info['models']) == 1

        model_info = info['models'][0]
        assert 'model_path' in model_info
        assert 'dtype' in model_info
        assert 'last_access' in model_info
        assert "./test_model_1" in model_info['model_path']


class TestCacheSizeReduction:
    """Test reducing cache size with models loaded."""

    def test_reduce_cache_size_evicts_models(self, cache_size_3, mock_model):
        """Test that reducing cache size evicts oldest models."""
        with patch('lightning_whisper_mlx.transcribe.load_model', return_value=mock_model):
            # Load 3 models
            model1 = ModelHolder.get_model("./test_model_1", mx.float16)
            time.sleep(0.01)
            model2 = ModelHolder.get_model("./test_model_2", mx.float16)
            time.sleep(0.01)
            model3 = ModelHolder.get_model("./test_model_3", mx.float16)

            assert ModelHolder.get_cached_count() == 3

        # Reduce cache size to 1
        ModelHolder.set_cache_size(1)

        # Should only have 1 model now (most recent)
        assert ModelHolder.get_cached_count() == 1

        info = ModelHolder.get_cache_info()
        assert info['max_size'] == 1
        assert info['current_size'] == 1

        # Most recent model should still be cached
        assert "./test_model_3" in info['models'][0]['model_path']


class TestDifferentDtypes:
    """Test that different dtypes create separate cache entries."""

    def test_same_path_different_dtype_separate_cache(self, cache_size_2, mock_model):
        """Test that same model path with different dtype is cached separately."""
        with patch('lightning_whisper_mlx.transcribe.load_model', return_value=mock_model):
            # Load model with float16
            model1 = ModelHolder.get_model("./test_model", mx.float16)
            assert ModelHolder.get_cached_count() == 1

            # Load same path with float32 - should be separate entry
            model2 = ModelHolder.get_model("./test_model", mx.float32)
            assert ModelHolder.get_cached_count() == 2

        # Both should be in cache
        info = ModelHolder.get_cache_info()
        assert info['current_size'] == 2

        dtypes = [m['dtype'] for m in info['models']]
        assert 'mlx.core.float16' in dtypes
        assert 'mlx.core.float32' in dtypes


class TestManualUnload:
    """Test manual model unloading."""

    def test_unload_specific_model(self, cache_size_2, mock_model):
        """Test unloading a specific model from cache."""
        with patch('lightning_whisper_mlx.transcribe.load_model', return_value=mock_model):
            # Load two models
            model1 = ModelHolder.get_model("./test_model_1", mx.float16)
            model2 = ModelHolder.get_model("./test_model_2", mx.float16)
            assert ModelHolder.get_cached_count() == 2

        # Unload first model
        result = ModelHolder.unload_model("./test_model_1", mx.float16)
        assert result is True
        assert ModelHolder.get_cached_count() == 1

        # Verify only second model remains
        info = ModelHolder.get_cache_info()
        assert len(info['models']) == 1
        assert "./test_model_2" in info['models'][0]['model_path']

    def test_unload_model_not_in_cache(self):
        """Test unloading a model that's not in cache returns False."""
        result = ModelHolder.unload_model("./nonexistent", mx.float16)
        assert result is False

    def test_unload_all_dtypes_for_model(self, cache_size_3, mock_model):
        """Test unloading all dtypes for a specific model path."""
        with patch('lightning_whisper_mlx.transcribe.load_model', return_value=mock_model):
            # Load same model with different dtypes
            model1 = ModelHolder.get_model("./test_model", mx.float16)
            model2 = ModelHolder.get_model("./test_model", mx.float32)
            model3 = ModelHolder.get_model("./other_model", mx.float16)
            assert ModelHolder.get_cached_count() == 3

        # Unload all dtypes for test_model (don't specify dtype)
        result = ModelHolder.unload_model("./test_model")
        assert result is True
        assert ModelHolder.get_cached_count() == 1

        # Verify only other_model remains
        info = ModelHolder.get_cache_info()
        assert len(info['models']) == 1
        assert "./other_model" in info['models'][0]['model_path']

    def test_unload_via_lightning_api(self, cache_size_2, mock_model):
        """Test unloading model via LightningWhisperMLX API."""
        with patch('lightning_whisper_mlx.transcribe.load_model', return_value=mock_model):
            model1 = ModelHolder.get_model("./test_model_1", mx.float16)
            model2 = ModelHolder.get_model("./test_model_2", mx.float16)
            assert LightningWhisperMLX.get_cached_model_count() == 2

        # Unload via public API
        result = LightningWhisperMLX.unload_model("./test_model_1")
        assert result is True
        assert LightningWhisperMLX.get_cached_model_count() == 1
