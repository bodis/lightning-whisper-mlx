# Lightning Whisper MLX

An incredibly fast implementation of Whisper optimized for Apple Silicon.

![Whisper Decoding Speed](./speed_image.png)

10x faster than Whisper CPP, 4x faster than current MLX Whisper implementation.

## Features

- **Batched Decoding** -> Higher Throughput
- **Distilled Models** -> Faster Decoding (less layers)
- **Quantized Models** -> Faster Memory Movement
- _Coming Soon: Speculative Decoding -> Faster Decoding with Assistant Model_

## Installation

Install lightning whisper mlx using pip:

```bash
pip install lightning-whisper-mlx
```

## Usage

Models

```
["tiny", "small", "distil-small.en", "base", "medium", distil-medium.en", "large", "large-v2", "distil-large-v2", "large-v3", "distil-large-v3"]
```

Quantization

```
[None, "4bit", "8bit"]
```

#### Example

```python
from lightning_whisper_mlx import LightningWhisperMLX

whisper = LightningWhisperMLX(model="distil-medium.en", batch_size=12, quant=None)

text = whisper.transcribe(audio_path="/audio.mp3")['text']

print(text)
```

## Notes

- The default batch_size is `12`, higher is better for throughput but you might run into memory issues. The heuristic is it really depends on the size of the model. If you are running the smaller models, then higher batch size, larger models, lower batch size. Also keep in mind your unified memory!

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
