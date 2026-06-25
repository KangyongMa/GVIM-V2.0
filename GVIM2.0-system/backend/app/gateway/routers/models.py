from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel, Field
import os
from pathlib import Path
from dotenv import set_key

from app.gateway.deps import get_config
from deerflow.config.app_config import AppConfig, reload_app_config
from deerflow.config.extensions_config import get_extensions_config, reload_extensions_config

router = APIRouter(prefix="/api", tags=["models"])


class ModelResponse(BaseModel):
    """Response model for model information."""

    name: str = Field(..., description="Unique identifier for the model")
    model: str = Field(..., description="Actual provider model identifier")
    display_name: str | None = Field(None, description="Human-readable name")
    description: str | None = Field(None, description="Model description")
    supports_thinking: bool = Field(default=False, description="Whether model supports thinking mode")
    supports_reasoning_effort: bool = Field(default=False, description="Whether model supports reasoning effort")
    supports_vision: bool = Field(default=False, description="Whether model supports vision/image inputs")
    provider: str | None = Field(None, description="Provider identifier (e.g. google, deepseek, openai)")


class TokenUsageResponse(BaseModel):
    """Token usage display configuration."""

    enabled: bool = Field(default=False, description="Whether token usage display is enabled")


class ModelsListResponse(BaseModel):
    """Response model for listing all models."""

    models: list[ModelResponse]
    token_usage: TokenUsageResponse


class ApiKeysResponse(BaseModel):
    """Response model for showing masked API keys."""

    keys: dict[str, str] = Field(..., description="Masked API keys dictionary")


class ApiKeysUpdateRequest(BaseModel):
    """Request model for updating API keys."""

    keys: dict[str, str] = Field(..., description="API keys dictionary to update")


def _get_provider(model: AppConfig) -> str:
    """Helper to infer provider name from model class path or config."""
    if model.model_extra and "provider" in model.model_extra:
        return str(model.model_extra["provider"])
        
    use_path = str(model.use).lower()
    if "openai" in use_path:
        base_url = str(model.model_extra.get("base_url", "")) if model.model_extra else ""
        if "dashscope" in base_url or "aliyuncs" in base_url:
            return "dashscope"
        if "bigmodel" in base_url:
            return "zhipuai"
        return "openai"
    elif "anthropic" in use_path:
        return "anthropic"
    elif "google" in use_path:
        return "google"
    elif "deepseek" in use_path:
        return "deepseek"
    elif "ollama" in use_path:
        return "ollama"
    return "default"


@router.get(
    "/models",
    response_model=ModelsListResponse,
    summary="List All Models",
    description="Retrieve a list of all available AI models configured in the system.",
)
async def list_models(config: AppConfig = Depends(get_config)) -> ModelsListResponse:
    """List all available models from configuration.

    Returns model information suitable for frontend display,
    excluding sensitive fields like API keys and internal configuration.

    Returns:
        A list of all configured models with their metadata and token usage display settings.
    """
    models = []
    for model in config.models:
        # Check standard api_key field or provider-specific api_key fields in extra attributes
        api_key_val = None
        if hasattr(model, "api_key"):
            api_key_val = getattr(model, "api_key")
        elif model.model_extra and "api_key" in model.model_extra:
            api_key_val = model.model_extra["api_key"]
            
        if not api_key_val:
            if hasattr(model, "google_api_key"):
                api_key_val = getattr(model, "google_api_key")
            elif model.model_extra and "google_api_key" in model.model_extra:
                api_key_val = model.model_extra["google_api_key"]

        if not api_key_val:
            if hasattr(model, "gemini_api_key"):
                api_key_val = getattr(model, "gemini_api_key")
            elif model.model_extra and "gemini_api_key" in model.model_extra:
                api_key_val = model.model_extra["gemini_api_key"]

        # If the API key is configured to reference an environment variable but that
        # variable resolves to an empty string "", it means the user hasn't configured it.
        # Skip this model dynamically.
        if api_key_val == "":
            continue

        supports_vision = False
        if hasattr(model, "supports_vision"):
            supports_vision = bool(getattr(model, "supports_vision"))
        elif model.model_extra and "supports_vision" in model.model_extra:
            supports_vision = bool(model.model_extra["supports_vision"])

        models.append(
            ModelResponse(
                name=model.name,
                model=model.model,
                display_name=model.display_name,
                description=model.description,
                supports_thinking=model.supports_thinking,
                supports_reasoning_effort=model.supports_reasoning_effort,
                supports_vision=supports_vision,
                provider=_get_provider(model),
            )
        )
    return ModelsListResponse(
        models=models,
        token_usage=TokenUsageResponse(enabled=config.token_usage.enabled),
    )


@router.get(
    "/models/{model_name}",
    response_model=ModelResponse,
    summary="Get Model Details",
    description="Retrieve detailed information about a specific AI model by its name.",
)
async def get_model(model_name: str, config: AppConfig = Depends(get_config)) -> ModelResponse:
    """Get a specific model by name.

    Args:
        model_name: The unique name of the model to retrieve.

    Returns:
        Model information if found.

    Raises:
        HTTPException: 404 if model not found.
    """
    model = config.get_model_config(model_name)
    if model is None:
        raise HTTPException(status_code=404, detail=f"Model '{model_name}' not found")

    supports_vision = False
    if hasattr(model, "supports_vision"):
        supports_vision = bool(getattr(model, "supports_vision"))
    elif model.model_extra and "supports_vision" in model.model_extra:
        supports_vision = bool(model.model_extra["supports_vision"])

    return ModelResponse(
        name=model.name,
        model=model.model,
        display_name=model.display_name,
        description=model.description,
        supports_thinking=model.supports_thinking,
        supports_reasoning_effort=model.supports_reasoning_effort,
        supports_vision=supports_vision,
        provider=_get_provider(model),
    )


def _mask_key(val: str | None) -> str:
    """Helper to mask an API key for safe UI display."""
    if not val:
        return ""
    val_str = str(val).strip()
    if not val_str:
        return ""
    if len(val_str) <= 8:
        return "********"
    return f"{val_str[:4]}********{val_str[-4:]}"


# Supported keys for LLMs, specialized material/chemistry compute, literature databases, and helper tools
_SUPPORTED_ENV_KEYS = [
    "DEEPSEEK_API_KEY",
    "DASHSCOPE_API_KEY",
    "GLM_API_KEY",
    "ANTHROPIC_API_KEY",
    "OPENAI_API_KEY",
    "GEMINI_API_KEY",
    "GOOGLE_API_KEY",
    "GOOGLE_AI_API_KEY",
    "MP_API_KEY",
    "MATERIALS_PROJECT_API_KEY",
    "CITRINATION_API_KEY",
    "SEMANTIC_SCHOLAR_API_KEY",
    "S2_API_KEY",
    "NCBI_API_KEY",
    "pubmed_api_key",
    "MINERU_API_TOKEN",
    "GITHUB_TOKEN",
    "HF_TOKEN",
    "HUGGING_FACE_HUB_TOKEN",
    "SERPER_API_KEY",
    "TAVILY_API_KEY",
    "JINA_API_KEY",
]


@router.get(
    "/models/config/keys",
    response_model=ApiKeysResponse,
    summary="Get Configured API Keys",
    description="Retrieve masked versions of all configured API keys for safe UI display.",
)
async def get_api_keys(config: AppConfig = Depends(get_config)) -> ApiKeysResponse:
    """Retrieve all supported environment/API keys masked for the UI."""
    config_path = AppConfig.resolve_config_path()
    dotenv_path = config_path.parent / ".env"

    masked_keys = {}
    for key in _SUPPORTED_ENV_KEYS:
        # Check current memory environment first, then fallback to .env file
        val = os.getenv(key)
        masked_keys[key] = _mask_key(val)

    return ApiKeysResponse(keys=masked_keys)


@router.put(
    "/models/config/keys",
    response_model=ApiKeysResponse,
    summary="Save API Keys",
    description="Save updated API keys to .env and hot-reload them into the running environment.",
)
async def update_api_keys(request: ApiKeysUpdateRequest, config: AppConfig = Depends(get_config)) -> ApiKeysResponse:
    """Save API keys to .env and hot-reload them into memory."""
    config_path = AppConfig.resolve_config_path()
    dotenv_path = config_path.parent / ".env"

    # Ensure .env file exists
    if not dotenv_path.exists():
        try:
            dotenv_path.touch()
        except Exception as e:
            raise HTTPException(status_code=500, detail=f"Failed to create .env file: {str(e)}")

    updated_keys = {}
    for key, val in request.keys.items():
        if key not in _SUPPORTED_ENV_KEYS:
            continue

        val_str = val.strip()

        # If it is a masked value (contains '********'), it means the user didn't modify it. Preserve it.
        if "********" in val_str:
            continue

        # If the input is empty, the user wants to clear the key
        if not val_str:
            set_key(str(dotenv_path), key, "")
            os.environ.pop(key, None)
        else:
            set_key(str(dotenv_path), key, val_str)
            os.environ[key] = val_str

    compat_pairs = [
        ("MP_API_KEY", "MATERIALS_PROJECT_API_KEY"),
        ("SEMANTIC_SCHOLAR_API_KEY", "S2_API_KEY"),
        ("GEMINI_API_KEY", "GOOGLE_AI_API_KEY"),
        ("GEMINI_API_KEY", "GOOGLE_API_KEY"),
        ("HF_TOKEN", "HUGGING_FACE_HUB_TOKEN"),
    ]

    for primary, compat in compat_pairs:
        # Check if the primary key was updated in the request (and is not masked/skipped)
        if primary in request.keys and "********" not in request.keys[primary].strip():
            val = request.keys[primary].strip()
            set_key(str(dotenv_path), compat, val)
            if val:
                os.environ[compat] = val
            else:
                os.environ.pop(compat, None)
        # Check conversely if the compat key was updated
        elif compat in request.keys and "********" not in request.keys[compat].strip():
            val = request.keys[compat].strip()
            set_key(str(dotenv_path), primary, val)
            if val:
                os.environ[primary] = val
            else:
                os.environ.pop(primary, None)

    # Perform native hot-reloading for main LLM configs and extension MCP configs
    try:
        reload_app_config()
        reload_extensions_config()
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Configuration saved but failed to hot-reload: {str(e)}")

    # Return the newly updated masked keys list
    return await get_api_keys(config)

