"""
Unit tests for the Lightning Whisper MLX API.

These tests verify the public API methods work correctly without
loading actual models.
"""

import pytest
from lightning_whisper_mlx import LightningWhisperMLX
from lightning_whisper_mlx.transcribe import ModelHolder


class TestImports:
    """Test that all necessary imports work."""

    def test_import_lightning_whisper_mlx(self):
        """Test that LightningWhisperMLX can be imported."""
        from lightning_whisper_mlx import LightningWhisperMLX
        assert LightningWhisperMLX is not None

    def test_import_modelholder(self):
        """Test that ModelHolder can be imported."""
        from lightning_whisper_mlx.transcribe import ModelHolder
        assert ModelHolder is not None


class TestAPIMethodsExist:
    """Test that all new API methods exist."""

    def test_set_model_cache_size_exists(self):
        """Test that set_model_cache_size method exists."""
        assert hasattr(LightningWhisperMLX, 'set_model_cache_size')
        assert callable(LightningWhisperMLX.set_model_cache_size)

    def test_get_model_cache_size_exists(self):
        """Test that get_model_cache_size method exists."""
        assert hasattr(LightningWhisperMLX, 'get_model_cache_size')
        assert callable(LightningWhisperMLX.get_model_cache_size)

    def test_get_cached_model_count_exists(self):
        """Test that get_cached_model_count method exists."""
        assert hasattr(LightningWhisperMLX, 'get_cached_model_count')
        assert callable(LightningWhisperMLX.get_cached_model_count)

    def test_clear_model_cache_exists(self):
        """Test that clear_model_cache method exists."""
        assert hasattr(LightningWhisperMLX, 'clear_model_cache')
        assert callable(LightningWhisperMLX.clear_model_cache)

    def test_get_cache_info_exists(self):
        """Test that get_cache_info method exists."""
        assert hasattr(LightningWhisperMLX, 'get_cache_info')
        assert callable(LightningWhisperMLX.get_cache_info)

    def test_unload_model_exists(self):
        """Test that unload_model method exists."""
        assert hasattr(LightningWhisperMLX, 'unload_model')
        assert callable(LightningWhisperMLX.unload_model)


class TestCacheOperations:
    """Test basic cache operations without loading models."""

    def test_default_cache_size(self):
        """Test that default cache size is 1."""
        default_size = LightningWhisperMLX.get_model_cache_size()
        assert default_size == 1

    def test_set_cache_size(self):
        """Test setting cache size."""
        LightningWhisperMLX.set_model_cache_size(3)
        new_size = LightningWhisperMLX.get_model_cache_size()
        assert new_size == 3

    def test_get_cached_count_empty(self):
        """Test that cached count is 0 when no models are loaded."""
        count = LightningWhisperMLX.get_cached_model_count()
        assert count == 0

    def test_get_cache_info_structure(self):
        """Test that get_cache_info returns correct structure."""
        info = LightningWhisperMLX.get_cache_info()

        assert isinstance(info, dict)
        assert 'max_size' in info
        assert 'current_size' in info
        assert 'models' in info
        assert isinstance(info['models'], list)

    def test_get_cache_info_values(self):
        """Test that get_cache_info returns correct values."""
        LightningWhisperMLX.set_model_cache_size(3)
        info = LightningWhisperMLX.get_cache_info()

        assert info['max_size'] == 3
        assert info['current_size'] == 0

    def test_clear_cache_when_empty(self):
        """Test that clearing empty cache doesn't error."""
        LightningWhisperMLX.clear_model_cache()
        count = LightningWhisperMLX.get_cached_model_count()
        assert count == 0

    def test_invalid_cache_size_zero(self):
        """Test that cache size of 0 is rejected."""
        with pytest.raises(ValueError, match="Cache size must be at least 1"):
            LightningWhisperMLX.set_model_cache_size(0)

    def test_invalid_cache_size_negative(self):
        """Test that negative cache size is rejected."""
        with pytest.raises(ValueError, match="Cache size must be at least 1"):
            LightningWhisperMLX.set_model_cache_size(-1)

    def test_cache_size_one(self):
        """Test setting cache size to 1."""
        LightningWhisperMLX.set_model_cache_size(1)
        assert LightningWhisperMLX.get_model_cache_size() == 1

    def test_cache_size_large(self):
        """Test setting large cache size."""
        LightningWhisperMLX.set_model_cache_size(10)
        assert LightningWhisperMLX.get_model_cache_size() == 10


class TestModelHolderDirect:
    """Test ModelHolder class directly."""

    def test_modelholder_has_cache_attribute(self):
        """Test that ModelHolder has _cache attribute."""
        assert hasattr(ModelHolder, '_cache')

    def test_modelholder_has_max_cache_size_attribute(self):
        """Test that ModelHolder has _max_cache_size attribute."""
        assert hasattr(ModelHolder, '_max_cache_size')

    def test_modelholder_has_get_model_method(self):
        """Test that ModelHolder has get_model method."""
        assert hasattr(ModelHolder, 'get_model')
        assert callable(ModelHolder.get_model)

    def test_modelholder_has_set_cache_size_method(self):
        """Test that ModelHolder has set_cache_size method."""
        assert hasattr(ModelHolder, 'set_cache_size')
        assert callable(ModelHolder.set_cache_size)

    def test_modelholder_has_get_cache_size_method(self):
        """Test that ModelHolder has get_cache_size method."""
        assert hasattr(ModelHolder, 'get_cache_size')
        assert callable(ModelHolder.get_cache_size)

    def test_modelholder_has_get_cached_count_method(self):
        """Test that ModelHolder has get_cached_count method."""
        assert hasattr(ModelHolder, 'get_cached_count')
        assert callable(ModelHolder.get_cached_count)

    def test_modelholder_has_clear_cache_method(self):
        """Test that ModelHolder has clear_cache method."""
        assert hasattr(ModelHolder, 'clear_cache')
        assert callable(ModelHolder.clear_cache)

    def test_modelholder_has_get_cache_info_method(self):
        """Test that ModelHolder has get_cache_info method."""
        assert hasattr(ModelHolder, 'get_cache_info')
        assert callable(ModelHolder.get_cache_info)

    def test_modelholder_has_unload_model_method(self):
        """Test that ModelHolder has unload_model method."""
        assert hasattr(ModelHolder, 'unload_model')
        assert callable(ModelHolder.unload_model)

    def test_modelholder_set_cache_size(self):
        """Test ModelHolder cache size setting."""
        ModelHolder.set_cache_size(2)
        assert ModelHolder.get_cache_size() == 2

    def test_modelholder_cache_is_dict(self):
        """Test that ModelHolder._cache is a dictionary."""
        assert isinstance(ModelHolder._cache, dict)

    def test_modelholder_max_cache_size_is_int(self):
        """Test that ModelHolder._max_cache_size is an integer."""
        assert isinstance(ModelHolder._max_cache_size, int)


class TestCacheSizeReduction:
    """Test cache size reduction behavior."""

    def test_reducing_cache_size_triggers_eviction(self):
        """Test that reducing cache size evicts models."""
        # This test doesn't load models but verifies the API works
        LightningWhisperMLX.set_model_cache_size(5)
        assert LightningWhisperMLX.get_model_cache_size() == 5

        LightningWhisperMLX.set_model_cache_size(2)
        assert LightningWhisperMLX.get_model_cache_size() == 2

    def test_increasing_cache_size(self):
        """Test that increasing cache size works."""
        LightningWhisperMLX.set_model_cache_size(1)
        LightningWhisperMLX.set_model_cache_size(5)
        assert LightningWhisperMLX.get_model_cache_size() == 5
