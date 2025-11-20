# Copyright © 2023 Apple Inc.

import os
import hashlib
from functools import lru_cache
from subprocess import CalledProcessError, run
from typing import Optional, Union

import mlx.core as mx
import numpy as np

# hard-coded audio hyperparameters
SAMPLE_RATE = 16000
N_FFT = 400
HOP_LENGTH = 160
CHUNK_LENGTH = 30
N_SAMPLES = CHUNK_LENGTH * SAMPLE_RATE  
N_FRAMES = N_SAMPLES // HOP_LENGTH  

N_SAMPLES_PER_TOKEN = HOP_LENGTH * 2  # the initial convolutions has stride 2
FRAMES_PER_SECOND = SAMPLE_RATE // HOP_LENGTH  # 10ms per audio frame
TOKENS_PER_SECOND = SAMPLE_RATE // N_SAMPLES_PER_TOKEN  # 20ms per audio token


def save_processed_audio(audio_data: mx.array, cache_dir: str, filename: str) -> str:
    """
    Save processed audio data to cache directory for faster reloading.

    Parameters
    ----------
    audio_data: mx.array
        The processed audio waveform to cache
    cache_dir: str
        Directory to save cached audio (can be relative or absolute)
    filename: str
        Name for the cached file

    Returns
    -------
    str: Path to the saved cache file
    """
    # Create cache directory if it doesn't exist
    os.makedirs(cache_dir, exist_ok=True)

    # Generate cache filename - allow user-specified paths for flexibility
    cache_path = os.path.join(cache_dir, filename)

    # Save the processed audio as numpy array
    np.save(cache_path, np.array(audio_data))

    return cache_path


def load_audio(file: str, sr: int = SAMPLE_RATE, cache_dir: Optional[str] = None):
    """
    Open an audio file and read as mono waveform, resampling as necessary

    Parameters
    ----------
    file: str
        The audio file to open

    sr: int
        The sample rate to resample the audio if necessary

    cache_dir: Optional[str]
        Optional directory to cache processed audio for faster reloading.
        If provided, will save/load from this directory.

    Returns
    -------
    A NumPy array containing the audio waveform, in float32 dtype.
    """

    # Check cache if cache_dir is provided
    if cache_dir:
        file_hash = hashlib.md5(file.encode()).hexdigest()
        cache_filename = f"{file_hash}_{sr}.npy"
        cache_path = os.path.join(cache_dir, cache_filename)

        # Load from cache if exists
        if os.path.exists(cache_path):
            cached_audio = np.load(cache_path)
            return mx.array(cached_audio)

    # This launches a subprocess to decode audio while down-mixing
    # and resampling as necessary.  Requires the ffmpeg CLI in PATH.
    # fmt: off
    cmd = [
        "ffmpeg",
        "-nostdin",
        "-threads", "0",
        "-i", file,
        "-f", "s16le",
        "-ac", "1",
        "-acodec", "pcm_s16le",
        "-ar", str(sr),
        "-"
    ]
    # fmt: on
    try:
        out = run(cmd, capture_output=True, check=True).stdout
    except CalledProcessError as e:
        raise RuntimeError(f"Failed to load audio: {e.stderr.decode()}") from e

    audio_array = mx.array(np.frombuffer(out, np.int16)).flatten().astype(mx.float32) / 32768.0

    # Save to cache if cache_dir is provided
    if cache_dir:
        file_hash = hashlib.md5(file.encode()).hexdigest()
        cache_filename = f"{file_hash}_{sr}.npy"
        save_processed_audio(audio_array, cache_dir, cache_filename)

    return audio_array


def pad_or_trim(array, length: int = N_SAMPLES, *, axis: int = -1):
    """
    Pad or trim the audio array to N_SAMPLES, as expected by the encoder.
    """
    if array.shape[axis] > length:
        sl = [slice(None)] * array.ndim
        sl[axis] = slice(0, length)
        array = array[tuple(sl)]

    if array.shape[axis] < length:
        pad_widths = [(0, 0)] * array.ndim
        pad_widths[axis] = (0, length - array.shape[axis])
        array = mx.pad(array, pad_widths)

    return array


@lru_cache(maxsize=None)
def mel_filters(n_mels: int) -> mx.array:
    """
    load the mel filterbank matrix for projecting STFT into a Mel spectrogram.
    Allows decoupling librosa dependency; saved using:

        np.savez_compressed(
            "mel_filters.npz",
            mel_80=librosa.filters.mel(sr=16000, n_fft=400, n_mels=80),
            mel_128=librosa.filters.mel(sr=16000, n_fft=400, n_mels=128),
        )
    """
    assert n_mels in {80, 128}, f"Unsupported n_mels: {n_mels}"

    filename = os.path.join(os.path.dirname(__file__), "assets", "mel_filters.npz")
    return mx.load(filename)[f"mel_{n_mels}"]


@lru_cache(maxsize=None)
def hanning(size):
    return mx.array(np.hanning(size + 1)[:-1])


def stft(x, window, nperseg=256, noverlap=None, nfft=None, axis=-1, pad_mode="reflect"):
    if nfft is None:
        nfft = nperseg
    if noverlap is None:
        noverlap = nfft // 4

    def _pad(x, padding, pad_mode="constant"):
        if pad_mode == "constant":
            return mx.pad(x, [(padding, padding)])
        elif pad_mode == "reflect":
            prefix = x[1 : padding + 1][::-1]
            suffix = x[-(padding + 1) : -1][::-1]
            return mx.concatenate([prefix, x, suffix])
        else:
            raise ValueError(f"Invalid pad_mode {pad_mode}")

    padding = nperseg // 2
    x = _pad(x, padding, pad_mode)

    strides = [noverlap, 1]
    t = (x.size - nperseg + noverlap) // noverlap
    shape = [t, nfft]
    x = mx.as_strided(x, shape=shape, strides=strides)
    return mx.fft.rfft(x * window)


def log_mel_spectrogram(
    audio: Union[str, np.ndarray],
    n_mels: int = 80,
    padding: int = 0,
    cache_dir: Optional[str] = None,
):
    """
    Compute the log-Mel spectrogram of

    Parameters
    ----------
    audio: Union[str, np.ndarray, mx.array], shape = (*)
        The path to audio or either a NumPy or mlx array containing the audio waveform in 16 kHz

    n_mels: int
        The number of Mel-frequency filters, only 80 is supported

    padding: int
        Number of zero samples to pad to the right

    cache_dir: Optional[str]
        Optional directory for caching preprocessed audio data

    Returns
    -------
    mx.array, shape = (80, n_frames)
        An  array that contains the Mel spectrogram
    """
    device = mx.default_device()
    mx.set_default_device(mx.cpu)
    if isinstance(audio, str):
        audio = load_audio(audio, cache_dir=cache_dir)
    elif not isinstance(audio, mx.array):
        audio = mx.array(audio)

    if padding > 0:
        audio = mx.pad(audio, (0, padding))
    window = hanning(N_FFT)
    freqs = stft(audio, window, nperseg=N_FFT, noverlap=HOP_LENGTH)
    magnitudes = freqs[:-1, :].abs().square()

    filters = mel_filters(n_mels)
    mel_spec = magnitudes @ filters.T

    log_spec = mx.maximum(mel_spec, 1e-10).log10()
    log_spec = mx.maximum(log_spec, log_spec.max() - 8.0)
    log_spec = (log_spec + 4.0) / 4.0
    mx.set_default_device(device)
    return log_spec
