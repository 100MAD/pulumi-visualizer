"""Replace Pulumi secret values before they leave the process.

A secret in a checkpoint is an object whose sigil key maps to the secret
signature, usually alongside a ciphertext field. Output-value wrappers use the
same sigil key and a `secret` flag. Ciphertext is never returned.
"""

SIG_KEY = "4dabf18193072939515e22adb298388d"
SECRET_SIG = "1b47061264138c4ac30d75fd1eb44270"

REDACTED = {"secret": True}


def redact(value):
    if isinstance(value, list):
        return [redact(item) for item in value]
    if not isinstance(value, dict):
        return value
    if SIG_KEY in value:
        if (
            value.get(SIG_KEY) == SECRET_SIG
            or value.get("secret") is True
            or "ciphertext" in value
        ):
            return dict(REDACTED)
        if "value" in value:
            return redact(value.get("value"))
        return {key: redact(item) for key, item in value.items() if key != SIG_KEY}
    return {key: redact(item) for key, item in value.items()}


def redact_properties(props, secret_keys=None):
    if not isinstance(props, dict):
        props = {}
    cleaned = redact(props)
    if not isinstance(cleaned, dict):
        return {}
    for key in secret_keys or []:
        if isinstance(key, str) and key in cleaned:
            cleaned[key] = dict(REDACTED)
    return cleaned


def redact_config(config):
    if not isinstance(config, dict):
        return {}
    cleaned = {}
    for key, raw in config.items():
        if not isinstance(key, str):
            continue
        if isinstance(raw, str):
            cleaned[key] = {"value": raw, "secret": False}
            continue
        if not isinstance(raw, dict):
            cleaned[key] = {"value": None, "secret": False}
            continue
        if raw.get("secret") is True or "ciphertext" in raw or SIG_KEY in raw:
            secret_value = raw.get("string", raw.get("value"))
            if raw.get("secret") is True or _is_secret_blob(secret_value) or "ciphertext" in raw:
                cleaned[key] = dict(REDACTED)
                continue
        value = raw.get("string", raw.get("value"))
        if isinstance(value, str):
            cleaned[key] = {"value": value, "secret": False}
        else:
            cleaned[key] = {"value": redact(value), "secret": False}
    return cleaned


def _is_secret_blob(value):
    return isinstance(value, dict) and (
        value.get(SIG_KEY) == SECRET_SIG or value.get("secret") is True or "ciphertext" in value
    )
