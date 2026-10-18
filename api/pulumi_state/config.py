"""Pulumi DIY backend settings.

Prefer discrete env vars (see settings / env.example): non-secret connection
fields in the AppDefinition, `AWS_ACCESS_KEY_ID` / `AWS_SECRET_ACCESS_KEY`
from Vault. Optional `PULUMI_STATE_BACKENDS` JSON remains for local/multi-backend.
Credentials stay in this process and are never copied into API responses.
"""

import json

from pulumi_state.state import BadName, validate_segment

ADDRESSING_STYLES = {"auto", "path", "virtual"}


class BackendConfigError(Exception):
    status = 500


class NotFound(Exception):
    status = 404


def _blank(value):
    if value is None:
        return None
    text = str(value).strip()
    return text or None


def normalize_backend(raw):
    if not isinstance(raw, dict):
        raise BackendConfigError("PULUMI_STATE_BACKENDS entries must be objects")
    try:
        name = validate_segment(raw.get("name"))
    except BadName:
        raise BackendConfigError("PULUMI_STATE_BACKENDS entry has an invalid name") from None
    bucket = raw.get("bucket")
    if not isinstance(bucket, str) or not bucket.strip() or "/" in bucket.strip():
        raise BackendConfigError("PULUMI_STATE_BACKENDS entry has an invalid bucket")
    prefix = raw.get("prefix") or ""
    if not isinstance(prefix, str):
        raise BackendConfigError("PULUMI_STATE_BACKENDS entry has an invalid prefix")
    segments = [part for part in prefix.strip("/").split("/") if part != ""]
    if any(part == ".." for part in segments):
        raise BackendConfigError("PULUMI_STATE_BACKENDS entry has an invalid prefix")
    endpoint = _blank(raw.get("endpoint_url"))
    addressing = raw.get("addressing_style")
    if addressing in (None, ""):
        addressing = "path" if endpoint else "auto"
    if addressing not in ADDRESSING_STYLES:
        raise BackendConfigError("PULUMI_STATE_BACKENDS entry has an invalid addressing_style")
    return {
        "name": name,
        "bucket": bucket.strip(),
        "prefix": "/".join(segments),
        "endpoint_url": endpoint,
        "region": _blank(raw.get("region")) or "us-east-1",
        "access_key_id": _blank(raw.get("access_key_id")),
        "secret_access_key": _blank(raw.get("secret_access_key")),
        "addressing_style": addressing,
    }


def _backend_from_rustfs_env():
    """Single backend from RUSTFS_* / PULUMI_BACKEND_* / AWS_* env (prod path)."""
    from django.conf import settings

    bucket = _blank(getattr(settings, "RUSTFS_BUCKET", ""))
    if not bucket:
        return None
    return normalize_backend(
        {
            "name": _blank(getattr(settings, "PULUMI_BACKEND_NAME", "")) or "homelab",
            "bucket": bucket,
            "prefix": getattr(settings, "RUSTFS_PREFIX", "") or "",
            "endpoint_url": getattr(settings, "RUSTFS_ENDPOINT_URL", None),
            "region": getattr(settings, "RUSTFS_REGION", None) or "us-east-1",
            "access_key_id": getattr(settings, "AWS_ACCESS_KEY_ID", None),
            "secret_access_key": getattr(settings, "AWS_SECRET_ACCESS_KEY", None),
            "addressing_style": getattr(settings, "RUSTFS_ADDRESSING_STYLE", None) or "path",
        }
    )


def configured_backends():
    from django.conf import settings

    raw = getattr(settings, "PULUMI_STATE_BACKENDS", "")
    if raw is None or raw == "" or raw == []:
        env_backend = _backend_from_rustfs_env()
        return [env_backend] if env_backend else []
    if isinstance(raw, str):
        try:
            raw = json.loads(raw)
        except json.JSONDecodeError:
            raise BackendConfigError("PULUMI_STATE_BACKENDS is not valid JSON") from None
    if not isinstance(raw, list):
        raise BackendConfigError("PULUMI_STATE_BACKENDS must be a JSON list")
    backends = [normalize_backend(item) for item in raw]
    names = [backend["name"] for backend in backends]
    if len(names) != len(set(names)):
        raise BackendConfigError("PULUMI_STATE_BACKENDS contains a duplicate name")
    return backends


def public_backend(backend):
    return {
        "name": backend["name"],
        "bucket": backend["bucket"],
        "prefix": backend["prefix"],
    }


def require_backend(name):
    validate_segment(name)
    for backend in configured_backends():
        if backend["name"] == name:
            return backend
    raise NotFound("backend not found")
