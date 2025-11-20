#!/usr/bin/env python3
"""
Practical examples of using the model cache in a long-running application.

Demonstrates the use case mentioned: a long-running app where users occasionally
request STT (Speech-to-Text), and you want models to stay cached between requests.
"""

from lightning_whisper_mlx import LightningWhisperMLX


def example_1_single_model():
    """
    Example 1: Single model, long-running app

    Default behavior - model stays in cache between requests.
    Perfect for apps that use only one model.
    """
    print("=" * 60)
    print("Example 1: Single Model (Default)")
    print("=" * 60)

    # Initialize once at app startup
    whisper = LightningWhisperMLX(model="distil-small.en", batch_size=12)

    # Simulate user requests over time
    print("\nUser request 1 (model loads):")
    # result1 = whisper.transcribe("audio1.mp3")  # Model loads here

    print("... waiting a few minutes ...")

    print("\nUser request 2 (model reused from cache):")
    # result2 = whisper.transcribe("audio2.mp3")  # Model already in memory!

    print("\n✓ Model stays in cache - no reloading needed")


def example_2_two_models_parallel():
    """
    Example 2: Two models used in parallel

    Configure cache to hold 2 models, initialize both at startup.
    Both stay in memory and can be used interchangeably.
    """
    print("\n" + "=" * 60)
    print("Example 2: Two Models in Parallel")
    print("=" * 60)

    # Configure cache size BEFORE initializing models
    LightningWhisperMLX.set_model_cache_size(2)
    print(f"Cache size set to: {LightningWhisperMLX.get_model_cache_size()}")

    # Initialize both models at startup
    whisper_en = LightningWhisperMLX(model="distil-small.en", batch_size=12)
    whisper_multi = LightningWhisperMLX(model="small", batch_size=12)

    print(f"\nModels cached: {LightningWhisperMLX.get_cached_model_count()}/2")

    # Use either model at any time - both stay in memory
    print("\nUser request 1 (English audio):")
    # result1 = whisper_en.transcribe("english_audio.mp3")

    print("\nUser request 2 (Spanish audio):")
    # result2 = whisper_multi.transcribe("spanish_audio.mp3")

    print("\nUser request 3 (English audio again):")
    # result3 = whisper_en.transcribe("more_english.mp3")

    print("\n✓ Both models stay cached - instant switching")


def example_3_dynamic_model_switching():
    """
    Example 3: Dynamic model switching with LRU eviction

    Use 3+ different models over time with cache size = 2.
    Least recently used models are automatically evicted.
    """
    print("\n" + "=" * 60)
    print("Example 3: Dynamic Switching with LRU Eviction")
    print("=" * 60)

    # Set cache to hold 2 models
    LightningWhisperMLX.set_model_cache_size(2)

    # Load model A
    print("\n1. Load distil-small.en (cache: 1/2)")
    whisper_a = LightningWhisperMLX(model="distil-small.en", batch_size=12)
    print(f"   Cached: {LightningWhisperMLX.get_cached_model_count()}/2")

    # Load model B
    print("\n2. Load base (cache: 2/2)")
    whisper_b = LightningWhisperMLX(model="base", batch_size=12)
    print(f"   Cached: {LightningWhisperMLX.get_cached_model_count()}/2")

    # Load model C - evicts A (least recently used)
    print("\n3. Load medium (cache full, evicting distil-small.en)")
    whisper_c = LightningWhisperMLX(model="medium", batch_size=12)
    print(f"   Cached: {LightningWhisperMLX.get_cached_model_count()}/2")
    print("   Evicted: distil-small.en (LRU)")
    print("   In cache: base, medium")

    # Reload model A - evicts B now
    print("\n4. Reload distil-small.en (evicting base)")
    whisper_a_again = LightningWhisperMLX(model="distil-small.en", batch_size=12)
    print(f"   Cached: {LightningWhisperMLX.get_cached_model_count()}/2")
    print("   Evicted: base (LRU)")
    print("   In cache: medium, distil-small.en")

    print("\n✓ Automatic LRU eviction keeps cache size bounded")


def example_4_manual_cache_management():
    """
    Example 4: Manual cache management

    Monitor and manually control the cache when needed.
    """
    print("\n" + "=" * 60)
    print("Example 4: Manual Cache Management")
    print("=" * 60)

    # Initialize with some models
    LightningWhisperMLX.set_model_cache_size(2)
    whisper1 = LightningWhisperMLX(model="distil-small.en", batch_size=12)
    whisper2 = LightningWhisperMLX(model="base", batch_size=12)

    # Check cache status
    print("\nCache status:")
    info = LightningWhisperMLX.get_cache_info()
    print(f"  Models cached: {info['current_size']}/{info['max_size']}")
    for model in info['models']:
        print(f"    - {model['model_path']}")
        print(f"      Last accessed: {model['last_access']}")

    # Manual cleanup when needed (e.g., low memory situation)
    print("\nManual cleanup before memory-intensive operation...")
    LightningWhisperMLX.clear_model_cache()
    print(f"Cache cleared. Models in cache: {LightningWhisperMLX.get_cached_model_count()}")

    print("\n✓ Manual cache control available when needed")


def example_5_long_running_app():
    """
    Example 5: Realistic long-running app pattern

    This is the pattern you described - app runs for days/weeks,
    users occasionally request STT, models stay cached.
    """
    print("\n" + "=" * 60)
    print("Example 5: Long-Running App (Your Use Case)")
    print("=" * 60)

    # App initialization
    print("\nApp startup:")
    LightningWhisperMLX.set_model_cache_size(1)  # Only need one model
    whisper = None  # Don't load yet

    # Helper function to handle STT requests
    def handle_stt_request(audio_path, model="distil-small.en"):
        global whisper

        # Lazy initialization - only load when first needed
        if whisper is None:
            print(f"  → First request, loading model '{model}'...")
            whisper = LightningWhisperMLX(model=model, batch_size=12)

        print(f"  → Processing audio: {audio_path}")
        # result = whisper.transcribe(audio_path)
        # return result
        return "transcription result"

    # Simulate app running over time
    print("\nSimulating app lifetime:")

    print("\n[Day 1, 10:00] User request #1")
    handle_stt_request("recording1.mp3")

    print("\n[Day 1, 14:30] User request #2")
    handle_stt_request("recording2.mp3")  # Model still in cache

    print("\n... several hours pass ...")

    print("\n[Day 2, 09:15] User request #3")
    handle_stt_request("recording3.mp3")  # Model STILL in cache!

    print("\n... several days pass ...")

    print("\n[Day 5, 16:45] User request #4")
    handle_stt_request("recording4.mp3")  # Model STILL in cache!

    print("\n✓ Model stays in memory indefinitely - perfect for your use case!")
    print("✓ No need to wrap in 'with' statements")
    print("✓ No repeated loading/unloading")


if __name__ == "__main__":
    print("Lightning Whisper MLX - Practical Usage Examples")
    print("=" * 60)

    # Run all examples
    example_1_single_model()
    example_2_two_models_parallel()
    example_3_dynamic_model_switching()
    example_4_manual_cache_management()
    example_5_long_running_app()

    print("\n" + "=" * 60)
    print("Examples complete!")
    print("=" * 60)

    # Cleanup
    LightningWhisperMLX.clear_model_cache()
    LightningWhisperMLX.set_model_cache_size(1)  # Reset to default
