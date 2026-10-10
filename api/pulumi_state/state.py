"""Parse Pulumi file-backend checkpoints and history files."""

from datetime import datetime, timezone
from urllib.parse import quote, unquote

STACK_TYPE = "pulumi:pulumi:Stack"
HISTORY_LIMIT = 30


class BadName(Exception):
    status = 400

    def __init__(self, message="invalid name"):
        super().__init__(message)


def validate_segment(value):
    if not isinstance(value, str) or value == "" or value != value.strip():
        raise BadName()
    if value in {".", ".."} or "/" in value or "\\" in value or "\x00" in value:
        raise BadName()
    return value


def escape_segment(value):
    return quote(validate_segment(value), safe="")


def unescape_segment(segment):
    return validate_segment(unquote(segment))


def s3_key(*parts):
    bits = []
    for part in parts:
        if part is None:
            continue
        text = str(part).strip("/")
        if text:
            bits.append(text)
    return "/".join(bits)


def backend_root(backend):
    return s3_key(backend.get("prefix") or "")


def stacks_prefix(backend):
    return s3_key(backend_root(backend), ".pulumi/stacks") + "/"


def stack_key(backend, project, stack):
    return s3_key(
        stacks_prefix(backend),
        escape_segment(project),
        escape_segment(stack) + ".json",
    )


def project_prefix(backend, project):
    return s3_key(stacks_prefix(backend), escape_segment(project)) + "/"


def history_prefix(backend, project, stack):
    return (
        s3_key(
            backend_root(backend),
            ".pulumi/history",
            escape_segment(project),
            escape_segment(stack),
        )
        + "/"
    )


def locks_prefix(backend, project, stack):
    return (
        s3_key(
            backend_root(backend),
            ".pulumi/locks",
            escape_segment(project),
            escape_segment(stack),
        )
        + "/"
    )


def deployment_from_checkpoint(doc):
    if not isinstance(doc, dict):
        return {}
    node = doc
    checkpoint = node.get("checkpoint")
    if isinstance(checkpoint, dict):
        node = checkpoint
    latest = node.get("latest")
    if isinstance(latest, dict):
        return latest
    deployment = node.get("deployment")
    if isinstance(deployment, dict):
        if isinstance(deployment.get("latest"), dict):
            return deployment["latest"]
        return deployment
    if isinstance(node.get("resources"), list):
        return node
    return {}


def iter_resources(deployment):
    resources = deployment.get("resources") if isinstance(deployment, dict) else None
    if not isinstance(resources, list):
        return
    for resource in resources:
        if isinstance(resource, dict) and isinstance(resource.get("urn"), str):
            yield resource


def is_stack_resource(resource):
    return resource.get("type") == STACK_TYPE


def urn_name(urn):
    parts = urn.split("::")
    if len(parts) >= 4:
        return "::".join(parts[3:])
    return urn


def resource_count(deployment):
    return sum(1 for resource in iter_resources(deployment) if not is_stack_resource(resource))


def type_counts(deployment):
    counts = {}
    for resource in iter_resources(deployment):
        if is_stack_resource(resource):
            continue
        kind = resource.get("type") if isinstance(resource.get("type"), str) else ""
        kind = kind or "unknown"
        counts[kind] = counts.get(kind, 0) + 1
    rows = [{"type": kind, "count": count} for kind, count in counts.items()]
    rows.sort(key=lambda row: (-row["count"], row["type"]))
    return rows


def project_names(stacks_root, prefixes):
    names = []
    for prefix in prefixes:
        if not prefix.startswith(stacks_root) or not prefix.endswith("/"):
            continue
        segment = prefix[len(stacks_root) : -1]
        if segment == "" or "/" in segment:
            continue
        try:
            names.append(unescape_segment(segment))
        except BadName:
            continue
    return sorted(set(names))


def stack_names(project_root, keys):
    names = []
    for key in keys:
        if not key.startswith(project_root):
            continue
        relative = key[len(project_root) :]
        if "/" in relative or not relative.endswith(".json"):
            continue
        try:
            names.append(unescape_segment(relative[: -len(".json")]))
        except BadName:
            continue
    return sorted(set(names))


def version_from_key(key):
    name = key.rsplit("/", 1)[-1]
    if not name.endswith(".json"):
        return None
    stem = name[: -len(".json")]
    if stem.isdigit():
        return int(stem)
    return None


def sort_history_keys(keys):
    def sort_key(key):
        version = version_from_key(key)
        return (version is not None, version or 0, key)

    usable = [key for key in keys if key.rsplit("/", 1)[-1].endswith(".json")]
    return sorted(usable, key=sort_key, reverse=True)


def to_iso(value):
    if value is None or value == "":
        return None
    if isinstance(value, str):
        return value
    if isinstance(value, bool) or not isinstance(value, (int, float)):
        return None
    timestamp = float(value)
    if timestamp > 10**16:
        timestamp /= 1e9
    elif timestamp > 10**14:
        timestamp /= 1e6
    elif timestamp > 10**11:
        timestamp /= 1e3
    try:
        return datetime.fromtimestamp(timestamp, tz=timezone.utc).isoformat()
    except (OverflowError, OSError, ValueError):
        return None


def summarize_history(doc, version_from_name):
    if not isinstance(doc, dict):
        return None
    version = doc.get("version")
    if not isinstance(version, int) or isinstance(version, bool):
        version = version_from_name
    changes = doc.get("resourceChanges")
    if not isinstance(changes, dict):
        changes = {}
    return {
        "version": version,
        "kind": doc.get("kind") if isinstance(doc.get("kind"), str) else "",
        "result": doc.get("result") if isinstance(doc.get("result"), str) else "",
        "message": doc.get("message") if isinstance(doc.get("message"), str) else "",
        "start_time": to_iso(doc.get("startTime")),
        "end_time": to_iso(doc.get("endTime")),
        "resource_changes": {str(key): value for key, value in changes.items()},
    }
