"""Configuration and settings management using Pydantic."""

import os
from pathlib import Path

import yaml
from pydantic import BaseModel, Field


class Settings(BaseModel):
    """Runtime settings for the copilot."""

    openai_api_key: str | None = Field(default=None)
    anthropic_api_key: str | None = Field(default=None)
    google_api_key: str | None = Field(default=None)
    allow_estimates: bool = Field(default=True)
    default_n: int = Field(default=50)
    default_workers: int = Field(default=5)
    temperature: float = Field(default=0.7)
    seed: int | None = Field(default=None)

    @classmethod
    def from_env(cls) -> "Settings":
        """Load settings from environment variables."""
        return cls(
            openai_api_key=os.getenv("OPENAI_API_KEY"),
            anthropic_api_key=os.getenv("ANTHROPIC_API_KEY"),
            google_api_key=os.getenv("GOOGLE_API_KEY"),
            allow_estimates=os.getenv("ALLOW_ESTIMATES", "true").lower() == "true",
            default_n=int(os.getenv("DEFAULT_N", "50")),
            default_workers=int(os.getenv("DEFAULT_WORKERS", "5")),
            temperature=float(os.getenv("TEMPERATURE", "0.7")),
            seed=int(os.getenv("SEED")) if os.getenv("SEED") else None,
        )


class ModelRegistry:
    """Load and manage model definitions from configs/models.yaml."""

    def __init__(self, config_path: Path):
        self.config_path = config_path
        self.models = self._load_models()

    def _load_models(self) -> dict:
        """Load model registry from YAML."""
        if not self.config_path.exists():
            return self._default_registry()

        with open(self.config_path) as f:
            return yaml.safe_load(f)

    def _default_registry(self) -> dict:
        """Default model registry with placeholders."""
        return {
            "openai": {
                "small": {
                    "id": "gpt-4o-mini",
                    "display_name": "GPT-4o Mini",
                    "pricing": {"input_per_1m": 0.15, "output_per_1m": 0.60},
                },
                "large": {
                    "id": "gpt-4o",
                    "display_name": "GPT-4o",
                    "pricing": {"input_per_1m": 2.50, "output_per_1m": 10.00},
                },
            },
            "anthropic": {
                "small": {
                    "id": "claude-3-5-haiku-20241022",
                    "display_name": "Claude 3.5 Haiku",
                    "pricing": {"input_per_1m": 1.00, "output_per_1m": 5.00},
                },
                "large": {
                    "id": "claude-3-5-sonnet-20241022",
                    "display_name": "Claude 3.5 Sonnet",
                    "pricing": {"input_per_1m": 3.00, "output_per_1m": 15.00},
                },
            },
            "google": {
                "small": {
                    "id": "gemini-2.0-flash-exp",
                    "display_name": "Gemini 2.0 Flash",
                    "pricing": {"input_per_1m": 0.075, "output_per_1m": 0.30},
                },
                "large": {
                    "id": "gemini-1.5-pro",
                    "display_name": "Gemini 1.5 Pro",
                    "pricing": {"input_per_1m": 1.25, "output_per_1m": 5.00},
                },
            },
        }

    def get_model(self, provider: str, size: str) -> dict:
        """Get model config for a provider/size combo."""
        return self.models.get(provider, {}).get(size, {})

    def get_model_id(self, provider: str, size: str) -> str:
        """Get model ID string for API calls."""
        return self.get_model(provider, size).get("id", "")

    def get_pricing(self, provider: str, size: str) -> dict:
        """Get pricing info for cost calculation."""
        return self.get_model(provider, size).get("pricing", {})
