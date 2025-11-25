"""
pytest configuration file.

This file is loaded before any tests run and configures the test environment.
It's also used by static analysis tools to properly import modules.
"""

import sys
from unittest.mock import MagicMock


# Mock MLX for environments where it's not available (e.g., CI on Linux)
# MLX is Apple Silicon-specific and can't be installed on ubuntu-latest runners
class MockMLXModule(MagicMock):
    """Mock MLX module for static analysis and testing on non-Apple platforms."""

    # Mock common MLX types and values
    float16 = "float16"
    float32 = "float32"

    class array(MagicMock):
        """Mock mlx.core.array"""
        def __init__(self, *args, **kwargs):
            super().__init__()
            self.shape = (0,)

        def flatten(self):
            return self

        def astype(self, dtype):
            return self


# Only mock if MLX is not available (e.g., on CI)
try:
    import mlx.core
except (ImportError, ModuleNotFoundError):
    sys.modules['mlx'] = MockMLXModule()
    sys.modules['mlx.core'] = MockMLXModule()
    print("ℹ️  MLX not available - using mock for static analysis")
