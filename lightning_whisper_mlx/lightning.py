from .transcribe import transcribe_audio, ModelHolder
from huggingface_hub import hf_hub_download 

models = {
    "tiny": {
        "base": "mlx-community/whisper-tiny", 
        "4bit": "mlx-community/whisper-tiny-mlx-4bit", 
        "8bit": "mlx-community/whisper-tiny-mlx-8bit"
    }, 
    "small": {
        "base": "mlx-community/whisper-small-mlx", 
        "4bit": "mlx-community/whisper-small-mlx-4bit", 
        "8bit": "mlx-community/whisper-small-mlx-8bit"
    },
    "distil-small.en": {
        "base": "mustafaaljadery/distil-whisper-mlx", 
    },
    "base": {
        "base" : "mlx-community/whisper-base-mlx", 
        "4bit" : "mlx-community/whisper-base-mlx-4bit",
        "8bit" : "mlx-community/whisper-base-mlx-8bit"
    },
    "medium": {
        "base": "mlx-community/whisper-medium-mlx",
        "4bit": "mlx-community/whisper-medium-mlx-4bit", 
        "8bit": "mlx-community/whisper-medium-mlx-8bit"
    }, 
    "distil-medium.en": {
        "base": "mustafaaljadery/distil-whisper-mlx", 
    }, 
    "large": {
        "base": "mlx-community/whisper-large-mlx", 
        "4bit": "mlx-community/whisper-large-mlx-4bit", 
        "8bit": "mlx-community/whisper-large-mlx-8bit", 
    },
    "large-v2": {
        "base": "mlx-community/whisper-large-v2-mlx",
        "4bit": "mlx-community/whisper-large-v2-mlx-4bit",
        "8bit": "mlx-community/whisper-large-v2-mlx-8bit", 
    },
    "distil-large-v2": {
        "base": "mustafaaljadery/distil-whisper-mlx",
    },
    "large-v3": {
        "base": "mlx-community/whisper-large-v3-mlx",
        "4bit": "mlx-community/whisper-large-v3-mlx-4bit",
        "8bit": "mlx-community/whisper-large-v3-mlx-8bit", 
    },
    "distil-large-v3": {
        "base": "mustafaaljadery/distil-whisper-mlx",
    },
}

class LightningWhisperMLX():
    def __init__(self, model, batch_size = 12, quant=None):
        if quant and (quant != "4bit" and quant !="8bit"):
            raise ValueError("Quantization must be `4bit` or `8bit`")

        if model not in models:
            raise ValueError("Please select a valid model")

        self.name = model
        self.batch_size = batch_size

        repo_id = ""

        if quant and "distil" not in model:
            repo_id = models[model][quant]
        else:
            repo_id = models[model]['base']

        if quant and "distil" in model:
            if quant == "4bit":
                self.name += "-4-bit"
            else:
                self.name += "-8-bit"

        if "distil" in model:
            filename1 = f"./mlx_models/{self.name}/weights.npz"
            filename2 = f"./mlx_models/{self.name}/config.json"
            local_dir = "./"
        else:
            filename1 = "weights.npz"
            filename2 = "config.json"
            local_dir = f"./mlx_models/{self.name}"

        hf_hub_download(repo_id=repo_id, filename=filename1, local_dir=local_dir)
        hf_hub_download(repo_id=repo_id, filename=filename2, local_dir=local_dir)

    def transcribe(self, audio_path, language=None):
        result = transcribe_audio(audio_path, path_or_hf_repo=f'./mlx_models/{self.name}', language=language, batch_size=self.batch_size)
        return result

    # Model cache management methods
    @staticmethod
    def set_model_cache_size(size: int):
        """
        Configure how many models to keep cached in memory.

        By default, only 1 model is cached. Increase this if you need to switch between
        multiple models without reloading them each time.

        Example:
            # Cache 2 models for faster switching
            LightningWhisperMLX.set_model_cache_size(2)

            # Now both models stay in memory
            whisper_tiny = LightningWhisperMLX(model="tiny.en")
            whisper_base = LightningWhisperMLX(model="base")

        Args:
            size: Maximum number of models to cache (must be >= 1)
        """
        ModelHolder.set_cache_size(size)

    @staticmethod
    def get_model_cache_size() -> int:
        """Get the current maximum cache size."""
        return ModelHolder.get_cache_size()

    @staticmethod
    def get_cached_model_count() -> int:
        """Get the number of currently cached models."""
        return ModelHolder.get_cached_count()

    @staticmethod
    def clear_model_cache():
        """
        Clear all cached models from memory.

        Use this to free up memory when models are no longer needed.
        """
        ModelHolder.clear_cache()

    @staticmethod
    def unload_model(model_path: str):
        """
        Manually unload a specific model from cache.

        Use this when you know a model won't be needed for an extended period.
        The model will be automatically reloaded on next use.

        Example:
            # Load and use a model
            whisper = LightningWhisperMLX(model="distil-small.en")
            result = whisper.transcribe("audio.mp3")

            # Unload when done for a while
            LightningWhisperMLX.unload_model("./mlx_models/distil-small.en")

            # Later use will automatically reload
            result2 = whisper.transcribe("audio2.mp3")

        Args:
            model_path: Path to the model directory (e.g., "./mlx_models/distil-small.en")

        Returns:
            bool: True if model was unloaded, False if not found in cache
        """
        return ModelHolder.unload_model(model_path)

    @staticmethod
    def get_cache_info() -> dict:
        """
        Get detailed information about cached models.

        Returns:
            Dictionary with:
            - max_size: Maximum cache size
            - current_size: Number of currently cached models
            - models: List of cached model details (path, dtype, last access time)
        """
        return ModelHolder.get_cache_info()