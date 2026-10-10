"""Direct S3 reads for Pulumi DIY checkpoints.

An in-process ETag cache skips re-parsing an object that has not changed.
Conditional GETs are still issued on every read.
"""

import json
import logging
import threading

logger = logging.getLogger(__name__)

_CACHE = {}
_CACHE_ORDER = []
_CACHE_MAX = 256
_LOCK = threading.Lock()


class StorageError(Exception):
    status = 502

    def __init__(self, message="object store read failed"):
        super().__init__(message)


class NotFound(Exception):
    status = 404

    def __init__(self, message="object not found"):
        super().__init__(message)


def clear_cache():
    with _LOCK:
        _CACHE.clear()
        _CACHE_ORDER.clear()


def _remember(cache_key, etag, doc):
    with _LOCK:
        if cache_key in _CACHE:
            _CACHE_ORDER.remove(cache_key)
        _CACHE[cache_key] = (etag, doc)
        _CACHE_ORDER.append(cache_key)
        while len(_CACHE_ORDER) > _CACHE_MAX:
            oldest = _CACHE_ORDER.pop(0)
            _CACHE.pop(oldest, None)


def _cached(cache_key):
    with _LOCK:
        return _CACHE.get(cache_key)


def _code(exc):
    response = getattr(exc, "response", None)
    if isinstance(response, dict):
        return str((response.get("Error") or {}).get("Code") or "")
    return ""


def _not_modified(exc):
    return _code(exc) in {"304", "NotModified"}


def _missing(exc):
    return _code(exc) in {"404", "NoSuchKey", "NotFound"}


def client_for(backend):
    import boto3
    from botocore.config import Config

    config = Config(
        s3={"addressing_style": backend["addressing_style"]},
        retries={"max_attempts": 3, "mode": "standard"},
    )
    return boto3.client(
        "s3",
        endpoint_url=backend["endpoint_url"],
        region_name=backend["region"],
        aws_access_key_id=backend["access_key_id"],
        aws_secret_access_key=backend["secret_access_key"],
        config=config,
    )


def list_objects(client, bucket, prefix, delimiter=None):
    try:
        paginator = client.get_paginator("list_objects_v2")
        kwargs = {"Bucket": bucket, "Prefix": prefix}
        if delimiter:
            kwargs["Delimiter"] = delimiter
        keys = []
        prefixes = []
        for page in paginator.paginate(**kwargs):
            for obj in page.get("Contents") or []:
                key = obj.get("Key")
                if isinstance(key, str):
                    keys.append(key)
            for common in page.get("CommonPrefixes") or []:
                child = common.get("Prefix")
                if isinstance(child, str):
                    prefixes.append(child)
        return keys, prefixes
    except Exception as exc:
        logger.warning(
            "pulumi s3 list failed bucket=%s prefix=%s code=%s",
            bucket,
            prefix,
            _code(exc),
        )
        raise StorageError() from None


def get_json(client, bucket, key):
    cache_key = (bucket, key)
    cached = _cached(cache_key)
    etag = cached[0] if cached else None
    try:
        kwargs = {"Bucket": bucket, "Key": key}
        if etag:
            kwargs["IfNoneMatch"] = etag
        response = client.get_object(**kwargs)
    except Exception as exc:
        if _not_modified(exc) and cached is not None:
            return cached[1]
        if _missing(exc):
            raise NotFound() from None
        logger.warning(
            "pulumi s3 get failed bucket=%s key=%s code=%s",
            bucket,
            key,
            _code(exc),
        )
        raise StorageError() from None
    body = response["Body"].read()
    try:
        parsed = json.loads(body)
    except (json.JSONDecodeError, UnicodeDecodeError, TypeError):
        raise StorageError("state object is not valid JSON") from None
    if not isinstance(parsed, dict):
        raise StorageError("state object is not valid JSON")
    _remember(cache_key, response.get("ETag"), parsed)
    return parsed
