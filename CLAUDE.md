# Claude Code Context: Lightning Whisper MLX

## Project Overview

**Lightning Whisper MLX** is a high-performance Whisper implementation optimized for Apple Silicon (M1/M2/M3). This is a **fork** of [mustafaaljadery/lightning-whisper-mlx](https://github.com/mustafaaljadery/lightning-whisper-mlx) maintained for:
- Integration with newer libraries (tiktoken >=0.12.0, MLX >=0.29.0, etc.)
- Additional features for specific use cases
- Modern Python packaging (pyproject.toml instead of setup.py)

### Key Characteristics
- **Batch processing only** - NOT designed for real-time streaming
- **Exceptional speed** - 10x faster than Whisper.cpp, 4x faster than standard MLX Whisper
- **Apple Silicon optimized** - Uses MLX framework for M-series chips
- **Two model families** - English-only (*.en) and Multilingual models

## Architecture & Design

### Core Components

1. **Tokenization** (`lightning_whisper_mlx/tokenizer.py`)
   - **Base vocabularies**: `gpt2.tiktoken` (English-only) and `multilingual.tiktoken` (99 languages)
   - **Bundled locally** in `assets/` directory for offline operation
   - **Special tokens generated in code**: 1,607 tokens (99 languages + 1,501 timestamps + task tokens)
   - **tiktoken dependency**: Provides BPE algorithm only, NOT vocabulary data

2. **Model Architecture** (`lightning_whisper_mlx/whisper.py`)
   - Two model families determined by `n_vocab` field:
     - `n_vocab < 51865`: English-only (uses gpt2.tiktoken)
     - `n_vocab >= 51865`: Multilingual (uses multilingual.tiktoken)
   - Models downloaded from HuggingFace Hub on first use
   - Cached in `./mlx_models/` directory

3. **Audio Processing** (`lightning_whisper_mlx/audio.py`)
   - **Batch processing**: Loads entire audio file into memory
   - Uses ffmpeg for audio decoding (must be in PATH)
   - Processes in 30-second windows for throughput optimization
   - **NOT streaming** - requires complete audio before transcription

4. **Transcription** (`lightning_whisper_mlx/transcribe.py`)
   - Batched decoding with configurable `batch_size` (default: 12)
   - Higher batch_size = better throughput but more memory
   - Returns: `{'text': str, 'segments': list, 'language': str}`

### Important Design Decisions

**Why vocabularies are bundled:**
1. Offline operation (works in air-gapped environments)
2. Deterministic behavior (vocabulary matches model weights exactly)
3. Universal compatibility (same vocab across all Whisper implementations)

**Why special tokens are generated in code (not files):**
1. 1,600+ tokens follow algorithmic patterns (sequential, predictable)
2. Allows configurable `num_languages` parameter
3. Prevents errors from manual data entry
4. Easy to modify (e.g., change timestamp precision)

**Why NOT streaming:**
- Architecture requires full audio → mel spectrogram → batch processing
- Optimized for maximum throughput, not latency
- For live audio: build audio capture/buffer layer around this library

## File Structure

```
lightning_whisper_mlx/
├── __init__.py              # Exports LightningWhisperMLX
├── lightning.py             # Main API class
├── transcribe.py            # Core transcription logic
├── whisper.py              # Model architecture
├── tokenizer.py            # Tokenization (base vocab + special tokens)
├── audio.py                # Audio loading/preprocessing
├── decoding.py             # Batch decoding logic
├── load_models.py          # Model loading from HF Hub
├── timing.py               # Word-level timestamps
└── assets/
    ├── gpt2.tiktoken       # English-only base vocabulary (50,256 tokens)
    ├── multilingual.tiktoken # Multilingual base vocabulary (50,257 tokens)
    └── mel_filters.npz     # Mel spectrogram filters
```

## Dependencies

### Critical Dependencies
- **mlx** (>=0.29.0): Apple Silicon ML framework
- **tiktoken** (>=0.12.0): BPE tokenization algorithm only (NOT vocabulary source)
- **torch** (>=2.9.0): Used for some preprocessing
- **numpy** (>=2.3.0): Array operations
- **huggingface-hub**: Model downloads

### Package Management
- **Build system**: hatchling
- **Package manager**: UV (recommended) or pip
- **Configuration**: pyproject.toml (modern Python packaging)

## Common Tasks

### Adding New Features
1. **Understand the batch processing architecture** - NOT streaming!
2. **Check if feature applies to both model families** (English-only vs Multilingual)
3. **Test with different batch sizes** - performance varies significantly
4. **Consider memory implications** - batching can use significant unified memory

### Modifying Tokenization
- **Base vocabularies** (`gpt2.tiktoken`, `multilingual.tiktoken`): FROZEN, DO NOT MODIFY
  - These must match model weights exactly
  - Changes break model compatibility
- **Special tokens** (tokenizer.py:343-354): Can be modified
  - Language tokens: configurable via `num_languages`
  - Timestamp tokens: generated algorithmically (range(1501))
  - Task tokens: hardcoded list

### Updating Dependencies
- **tiktoken**: Safe to upgrade (only provides BPE algorithm)
- **mlx**: Test carefully (model loading/quantization may change)
- **torch**: Used for preprocessing, generally safe
- **numpy**: Version 2.x required (breaking changes from 1.x)

## Testing & Validation

### Quick Test
```python
from lightning_whisper_mlx import LightningWhisperMLX

whisper = LightningWhisperMLX(model="tiny.en", batch_size=12)
result = whisper.transcribe("test_audio.mp3")
assert 'text' in result
assert 'segments' in result
```

### Performance Benchmarks
- Test with different batch sizes: 6, 12, 24
- Monitor unified memory usage (Activity Monitor)
- Compare English-only vs Multilingual models
- Test with different model sizes (tiny → large)

## Known Limitations

1. **NOT for streaming/live audio** - batch processing only
2. **Requires complete audio** - cannot process incrementally
3. **Memory intensive** - higher batch_size = more memory
4. **ffmpeg dependency** - must be installed and in PATH
5. **Apple Silicon only** - MLX framework is Mac-specific

## Integration Points

### For Streaming Applications
Build these layers around this library:
1. **Audio capture** (sounddevice, PyAudio)
2. **Buffer management** (sliding window, VAD)
3. **Call this library** for transcription
4. **Result streaming** (emit results progressively)

**Existing solutions with MLX support:**
- [whisper_streaming](https://github.com/ufal/whisper_streaming)
- [WhisperLiveKit](https://pypi.org/project/whisperlivekit/)

### For Applications Using UV

Add to `pyproject.toml`:
```toml
[project]
dependencies = [
    "lightning-whisper-mlx @ git+https://github.com/bodis/lightning-whisper-mlx.git",
]
```

## Troubleshooting

### Common Issues

**"ffmpeg not found"**
- Install: `brew install ffmpeg`
- Verify: `which ffmpeg`

**Memory issues / OOM**
- Reduce `batch_size` (try 6 or even 1)
- Use smaller models (tiny, base instead of large)
- Use quantized models (4bit, 8bit)
- Check unified memory in Activity Monitor

**Slow performance**
- Increase `batch_size` if memory allows
- Use distilled models (fewer layers)
- Use quantized models (faster memory movement)
- Verify running on Apple Silicon (not Rosetta)

**Wrong vocabulary / token errors**
- Model family mismatch: Check `model.is_multilingual`
- Vocabulary files corrupted: Check `assets/*.tiktoken`
- Special token generation failed: Check `tokenizer.py:343-354`

## Development Workflow

### Making Changes
1. Edit code in local clone
2. Test with: `python -m pytest` or manual testing
3. Commit: `git add . && git commit -m "Description"`
4. Push: `git push origin main`

### Syncing with Upstream
```bash
# One-time setup
git remote add upstream git@github.com:mustafaaljadery/lightning-whisper-mlx.git

# Pull updates
git fetch upstream
git merge upstream/main
git push origin main
```

### Testing Installation from Fork
```bash
# In a test environment
uv pip install "git+https://github.com/bodis/lightning-whisper-mlx.git"

# Verify
python -c "from lightning_whisper_mlx import LightningWhisperMLX; print('✓')"
```

## Important Notes for AI Assistants

1. **This is batch processing, NOT streaming** - clarify this if user asks about real-time
2. **Vocabularies are bundled and frozen** - don't suggest modifying .tiktoken files
3. **tiktoken is just the algorithm** - vocabulary data comes from bundled files
4. **Two model families** - always check which family when debugging tokenization
5. **Memory-intensive** - batch_size is a critical performance/memory trade-off
6. **Fork-specific** - newer dependencies, may differ from upstream

## Quick Reference

| Aspect | Value |
|--------|-------|
| **Processing Mode** | Batch (not streaming) |
| **Platform** | Apple Silicon (M1/M2/M3) |
| **Model Families** | English-only (*.en), Multilingual |
| **Vocabularies** | gpt2.tiktoken (50,256), multilingual.tiktoken (50,257) |
| **Special Tokens** | 1,607 (generated in code) |
| **Default Batch Size** | 12 |
| **Framework** | MLX (Apple) |
| **Python** | >=3.12 |
| **Package Manager** | UV (recommended) or pip |
