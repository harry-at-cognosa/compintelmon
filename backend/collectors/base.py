"""
Collection engine base: result type, registry, config interpolation, hashing.
"""
import hashlib
import json
import re
from dataclasses import dataclass, field
from typing import Any, Callable, Coroutine


@dataclass
class CollectionResult:
    status: str  # "ok", "error", "no_change", "skipped"
    items: list[dict] = field(default_factory=list)
    content_hash: str = ""
    error: str | None = None
    raw_content: str = ""


# Registry: tool name -> async collect function
# Each collector registers itself at import time
CollectorFunc = Callable[[dict], Coroutine[Any, Any, CollectionResult]]
COLLECTOR_REGISTRY: dict[str, CollectorFunc] = {}


def register_collector(tool_name: str):
    """Decorator to register a collector function."""
    def decorator(func: CollectorFunc) -> CollectorFunc:
        COLLECTOR_REGISTRY[tool_name] = func
        return func
    return decorator


def compute_content_hash(content: str) -> str:
    """SHA-256 hash of content for change detection."""
    return hashlib.sha256(content.encode("utf-8")).hexdigest()


def interpolate_config(
    collection_config: dict,
    user_inputs: dict,
    subject_metadata: dict | None = None,
) -> dict:
    """
    Walk collection_config and replace {variable} placeholders in string values
    using user_inputs and subject_metadata.

    Returns a new dict with interpolated values. Missing keys are left as-is.
    """
    context = {**(subject_metadata or {}), **user_inputs}
    return _interpolate_dict(collection_config, context)


def _interpolate_dict(obj: Any, context: dict) -> Any:
    if isinstance(obj, str):
        return _interpolate_string(obj, context)
    if isinstance(obj, dict):
        return {k: _interpolate_dict(v, context) for k, v in obj.items()}
    if isinstance(obj, list):
        return [_interpolate_dict(item, context) for item in obj]
    return obj


def _interpolate_string(template: str, context: dict) -> str:
    """Replace {key} placeholders. Leave unresolved placeholders as-is."""
    def replacer(match: re.Match) -> str:
        key = match.group(1)
        value = context.get(key)
        if value is None:
            return match.group(0)  # leave as-is
        return str(value)

    return re.sub(r"\{(\w+)\}", replacer, template)


def resolve_url(config: dict) -> str | None:
    """Extract the resolved URL from an interpolated config."""
    url = config.get("url_template") or config.get("url")
    if url and "{" in url:
        return None  # unresolved placeholder
    return url
