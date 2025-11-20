# Lightning Whisper MLX

> **Fork Notice**: This is a fork of [mustafaaljadery/lightning-whisper-mlx](https://github.com/mustafaaljadery/lightning-whisper-mlx). All credit for the original implementation goes to [Mustafa Aljadery](https://github.com/mustafaaljadery). This fork focuses on integrating with newer libraries and adding features for specific use cases that may not be common for the original project.

An incredibly fast implementation of Whisper optimized for Apple Silicon.

![Whisper Decoding Speed](./speed_image.png)

10x faster than Whisper CPP, 4x faster than current MLX Whisper implementation.

## Features

- **Batched Decoding** -> Higher Throughput
- **Distilled Models** -> Faster Decoding (less layers)
- **Quantized Models** -> Faster Memory Movement
- **Intelligent Model Caching** -> Keep models in memory for long-running apps (fork feature)
- _Coming Soon: Speculative Decoding -> Faster Decoding with Assistant Model_

## Installation

### Install from PyPI (Original Package)

```bash
pip install lightning-whisper-mlx
```

### Install from This Fork (Recommended for Latest Features)

**Using UV (Recommended):**

Add to your `pyproject.toml`:
```toml
[project]
dependencies = [
    "lightning-whisper-mlx @ git+https://github.com/bodis/lightning-whisper-mlx.git",
]
```

Then install:
```bash
uv sync
```

**Using pip:**
```bash
pip install git+https://github.com/bodis/lightning-whisper-mlx.git
```

**For development (editable install):**
```bash
git clone https://github.com/bodis/lightning-whisper-mlx.git
cd lightning-whisper-mlx
uv pip install -e .
```

## Usage

### Available Models

```python
["tiny", "small", "distil-small.en", "base", "medium", "distil-medium.en",
 "large", "large-v2", "distil-large-v2", "large-v3", "distil-large-v3"]
```

**Model Selection Guide:**
- `*.en` models: English-only, faster and more accurate for English
- Non-`.en` models: Support 99 languages + translation to English
- `distil-*` models: Fewer layers, ~2x faster with minimal accuracy loss
- Size trade-off: `tiny` (fastest, least accurate) → `large` (slowest, most accurate)

### Quantization Options

```python
[None, "4bit", "8bit"]
```

- `None`: Full precision (best quality, slower)
- `"4bit"`: 4-bit quantization (faster, ~75% smaller memory)
- `"8bit"`: 8-bit quantization (balanced speed/quality)

### Basic Example

```python
from lightning_whisper_mlx import LightningWhisperMLX

whisper = LightningWhisperMLX(model="distil-medium.en", batch_size=12, quant=None)

result = whisper.transcribe(audio_path="audio.mp3")

print(result['text'])      # Full transcription text
print(result['language'])  # Detected/specified language
print(result['segments'])  # List of segments with timestamps
```

### Model Caching for Long-Running Applications

**This fork includes intelligent model caching designed for long-running applications** (servers, daemons, etc.) where you want models to stay in memory between transcription requests without repeated loading.

**Default Behavior (Cache Size = 1):**
```python
from lightning_whisper_mlx import LightningWhisperMLX

# Initialize once
whisper = LightningWhisperMLX(model="distil-small.en", batch_size=12)

# First transcription - model loads into memory
result1 = whisper.transcribe("audio1.mp3")

# Hours/days later - model still in cache, no reload!
result2 = whisper.transcribe("audio2.mp3")  # Instant, no loading delay
```

**Multiple Models (Cache Size > 1):**
```python
# Configure to cache 2 models simultaneously
LightningWhisperMLX.set_model_cache_size(2)

# Both models stay in memory for instant switching
whisper_en = LightningWhisperMLX(model="distil-small.en")
whisper_multi = LightningWhisperMLX(model="small")

# Use either model - no reloading needed
if language == "en":
    result = whisper_en.transcribe(audio)
else:
    result = whisper_multi.transcribe(audio)
```

**Manual Memory Management:**
```python
# Unload a specific model when not needed for extended period
LightningWhisperMLX.unload_model("./mlx_models/distil-small.en")

# Model will auto-reload on next use
result = whisper.transcribe("audio.mp3")  # Reloads model

# Clear all cached models
LightningWhisperMLX.clear_model_cache()
```

**Cache Management API:**
```python
# Get current cache size limit
size = LightningWhisperMLX.get_model_cache_size()  # Default: 1

# Set cache size (how many models to keep in memory)
LightningWhisperMLX.set_model_cache_size(3)

# Get number of currently cached models
count = LightningWhisperMLX.get_cached_model_count()

# Get detailed cache information
info = LightningWhisperMLX.get_cache_info()
# Returns: {'max_size': 3, 'current_size': 2, 'models': [...]}
```

**How It Works:**
- Models are cached in memory after first use
- Default cache size is **1** (single model stays in memory)
- When cache is full, least recently used (LRU) model is evicted
- Perfect for long-running apps where you want instant transcription without reload delays
- Manual unloading available for explicit memory control

### Advanced Usage

For advanced features like VAD integration and context prompts, use `transcribe_audio()` directly:

```python
from lightning_whisper_mlx.transcribe import transcribe_audio

result = transcribe_audio(
    audio="audio.mp3",  # Path, numpy array, or MLX array
    path_or_hf_repo="./mlx_models/base.en",
    language="en",                      # Language code or None for auto-detect
    batch_size=12,                      # Higher = faster but more memory
    initial_prompt="Context text...",   # Improve accuracy with domain context
    clip_timestamps=[0, 30, 60, 90],    # Process specific time ranges (VAD)
    task="transcribe",                  # or "translate" for English translation
    temperature=0.0,                    # Sampling temperature (0.0 = greedy)
    verbose=True
)
```

**Key parameters:**
- `audio`: File path, numpy array (16kHz mono float32), or MLX array
- `initial_prompt`: Context to improve accuracy (names, technical terms, etc.)
- `clip_timestamps`: List/string of time ranges in seconds for VAD integration
- `condition_on_previous_text`: Use previous output as context (default: True)
- `batch_size`: Tune based on model size (tiny/base: 12-24, medium: 6-12, large: 1-6)

## Output Structure

The transcription returns a dictionary with the following structure:

```python
{
    'text': str,           # Full transcription text
    'segments': list,      # List of segments with timing information
    'language': str        # Detected or specified language code
}
```

### Segments Format

Each segment in the `segments` list is currently a **list** (not dict) with the format:

```python
[start_frame, end_frame, text]
```

- `start_frame` (int): Starting frame index in mel spectrogram
- `end_frame` (int): Ending frame index in mel spectrogram
- `text` (str): Transcribed text for this segment

**Converting frames to seconds:**

```python
from lightning_whisper_mlx.audio import HOP_LENGTH, SAMPLE_RATE

for start_frame, end_frame, text in result['segments']:
    start_sec = start_frame * HOP_LENGTH / SAMPLE_RATE
    end_sec = end_frame * HOP_LENGTH / SAMPLE_RATE
    print(f"[{start_sec:.2f}s - {end_sec:.2f}s]: {text}")
```

### Complete Output Example

```python
result = whisper.transcribe("audio.mp3")

# Output structure:
{
    'text': ' This is the full transcription of the entire audio file.',
    'segments': [
        [0, 1500, ' This is the full'],
        [1500, 3000, ' transcription of the entire'],
        [3000, 4500, ' audio file.']
    ],
    'language': 'en'
}
```

## Usage Examples

### VAD-Based Segmentation

Process only speech segments with context passing:

```python
from lightning_whisper_mlx.transcribe import transcribe_audio

# Your VAD segments (from silero-vad, pyannote, etc.)
vad_segments = [(0.5, 12.3), (15.8, 45.2), (50.1, 78.6)]  # (start_sec, end_sec)

results = []
context = ""

for start, end in vad_segments:
    result = transcribe_audio(
        audio="podcast.mp3",
        path_or_hf_repo="./mlx_models/base.en",
        clip_timestamps=[start, end],
        initial_prompt=context,  # Pass context from previous segments
        language="en",
        batch_size=12
    )

    results.append({'start': start, 'end': end, 'text': result['text']})
    context = ' '.join(result['text'].split()[-50:])  # Keep last 50 words
```

### Processing Segments with Timestamps

Convert frame indices to seconds:

```python
from lightning_whisper_mlx import LightningWhisperMLX
from lightning_whisper_mlx.audio import HOP_LENGTH, SAMPLE_RATE

whisper = LightningWhisperMLX(model="base.en", batch_size=12)
result = whisper.transcribe("audio.mp3")

for start_frame, end_frame, text in result['segments']:
    start_sec = start_frame * HOP_LENGTH / SAMPLE_RATE
    end_sec = end_frame * HOP_LENGTH / SAMPLE_RATE
    print(f"[{start_sec:.2f}s - {end_sec:.2f}s]: {text}")
```

## Notes

- **Batch size**: Default is 12. Increase for small models (12-24) on high-memory systems. Decrease for large models (1-6). Monitor Activity Monitor.
- **Frame conversion**: Segments use frame indices. Convert to seconds: `frame * HOP_LENGTH / SAMPLE_RATE` (see example above).
- **Context improves accuracy**: Use `initial_prompt` for domain-specific terms, proper nouns, or to maintain context across VAD segments.
- **Audio constants**: Import from `lightning_whisper_mlx.audio`: `HOP_LENGTH=160`, `SAMPLE_RATE=16000`, `FRAMES_PER_SECOND=100`

## Live Audio / Streaming Support

**This library is designed for batch processing of pre-recorded audio files, not real-time streaming.**

### Current Architecture

```
Audio File → Load Complete → Mel Spectrogram → Batch Process → Results
```

- ✅ Optimized for maximum throughput via batching
- ✅ Exceptional speed on pre-recorded files (MP3, WAV, FLAC, etc.)
- ✅ Accepts file paths or numpy/MLX arrays
- ❌ Does NOT include microphone capture
- ❌ Does NOT support incremental/streaming processing
- ❌ Requires complete audio before transcription starts

### Building a Live Transcription System

To use this library for live audio transcription, you need to build additional layers:

**1. Audio Capture** (use `sounddevice`, `PyAudio`, or `AVFoundation`)
```python
import sounddevice as sd
# Capture microphone input in chunks
# Accumulate audio buffer
```

**2. Buffer Management** (implement yourself)
- Maintain sliding window (3-5 seconds)
- Implement Voice Activity Detection (optional)
- Trigger transcription on silence or time threshold

**3. Transcription Engine** (use Lightning Whisper MLX)
```python
from lightning_whisper_mlx import LightningWhisperMLX
whisper = LightningWhisperMLX(model="base.en", batch_size=12)
result = whisper.transcribe(audio_array)  # Fast processing!
```

**4. Result Handling** (implement yourself)
- Display results as they arrive
- Manage context between chunks
- Handle overlapping audio to avoid duplicates

### Expected Latency

- **Audio accumulation**: 1-5 seconds (need enough for accuracy)
- **Transcription**: 0.1-1 second (very fast thanks to MLX optimization!)
- **Total**: ~1-6 seconds end-to-end

### Existing Streaming Solutions

For ready-to-use streaming implementations, check out:
- [whisper_streaming](https://github.com/ufal/whisper_streaming) - Supports MLX backend
- [WhisperLiveKit](https://pypi.org/project/whisperlivekit/) - Real-time with MLX support

These can use Lightning Whisper MLX as the transcription engine for optimal Apple Silicon performance.

## Architecture: Whisper Models & Tokenization

### Model Families

Whisper has **two model families** with different vocabularies:

| Family | Models | Vocabulary | Use Case |
|--------|--------|------------|----------|
| **English-only** | `*.en` (tiny.en, base.en, small.en, etc.) | `gpt2.tiktoken` (50,256 tokens) | Optimized for English audio only |
| **Multilingual** | All others (tiny, base, small, large, etc.) | `multilingual.tiktoken` (50,257 tokens) | Supports 99 languages + translation to English |

The model automatically selects the correct vocabulary based on its `n_vocab` parameter from the model weights.

### Tokenizer Architecture

```
┌─────────────────────────────────────────────────────────────┐
│ Base Vocabulary (bundled files)                            │
│ • gpt2.tiktoken or multilingual.tiktoken                    │
│ • Learned from training data (frozen, universal)            │
│ • ~50K BPE tokens for text encoding                         │
└─────────────────┬───────────────────────────────────────────┘
                  │
                  ▼
┌─────────────────────────────────────────────────────────────┐
│ Special Tokens (generated in tokenizer.py)                 │
│ • 99 language tokens: <|en|>, <|zh|>, <|ja|>, ...           │
│ • 1,501 timestamps: <|0.00|>, <|0.02|>, ..., <|30.00|>      │
│ • Task tokens: <|transcribe|>, <|translate|>, <|nospeech|>  │
│ • Algorithmically generated (not stored in files)           │
└─────────────────┬───────────────────────────────────────────┘
                  │
                  ▼
            Final vocabulary: ~51,864 tokens
```

### Why Bundled Vocabularies?

1. **Offline operation**: Works in air-gapped environments without downloading vocabularies
2. **Deterministic behavior**: Vocabulary is frozen with model weights, ensuring reproducibility
3. **Universal compatibility**: Same vocabulary across all Whisper implementations (OpenAI, MLX, Whisper.cpp, etc.)

**Why special tokens are in code, not files**: The 1,600+ special tokens follow algorithmic patterns (sequential language codes, timestamp intervals). Generating them in `tokenizer.py` allows flexibility (configurable `num_languages`) and prevents errors from manual data entry.

**tiktoken dependency**: The `tiktoken` library (>=0.12.0) provides only the BPE algorithm. Vocabulary data comes from bundled files, so tiktoken can be upgraded safely without affecting tokenization.

## Credits

- [Mustafa](https://github.com/mustafaaljadery) - Creator of Lightning Whisper MLX
- [Awni](https://github.com/awni) - Implementation of Whisper MLX (I built on top of this)
- [Vaibhav](https://github.com/Vaibhavs10) - Inspired me to build this (He created a version optimized for Cuda)
