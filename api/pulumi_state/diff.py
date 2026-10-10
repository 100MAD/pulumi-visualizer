"""Compare two Pulumi deployments and return a redacted property diff.

The file backend stores a checkpoint beside each history record. An update's
diff is that checkpoint compared with the previous update's checkpoint.
"""

from pulumi_state.redact import REDACTED, SIG_KEY, redact_properties
from pulumi_state.state import is_stack_resource, urn_name

_MISSING = object()
_OP_ORDER = {"create": 0, "update": 1, "delete": 2}


def diff_deployments(before, after):
    previous = _by_urn(before)
    current = _by_urn(after)
    labels = _user_labels(before)
    labels.update(_user_labels(after))
    changes = []
    for urn in set(previous) | set(current):
        old = previous.get(urn)
        new = current.get(urn)
        if old is None:
            changes.append(_change("create", None, new, labels))
        elif new is None:
            changes.append(_change("delete", old, None, labels))
        else:
            change = _change("update", old, new, labels)
            if change["inputs"] or change["outputs"] or "before_id" in change:
                changes.append(change)
    changes.sort(key=lambda row: (_OP_ORDER[row["op"]], row["type"], row["name"], row["urn"]))
    return changes


def _by_urn(deployment):
    resources = deployment.get("resources") if isinstance(deployment, dict) else None
    if not isinstance(resources, list):
        return {}
    found = {}
    for resource in resources:
        if isinstance(resource, dict) and isinstance(resource.get("urn"), str):
            found[resource["urn"]] = resource
    return found


def _change(op, before, after, labels):
    resource = after or before
    urn = resource.get("urn") or ""
    entry = {
        "op": op,
        "urn": urn,
        "name": urn_name(urn),
        "type": resource.get("type") if isinstance(resource.get("type"), str) else "",
        "stack": is_stack_resource(resource),
        "inputs": _properties(op, _props(before, "inputs"), _props(after, "inputs"), None, None, labels),
        "outputs": _properties(
            op,
            _props(before, "outputs"),
            _props(after, "outputs"),
            _secret_keys(before),
            _secret_keys(after),
            labels,
        ),
    }
    before_id = _text_id(before)
    after_id = _text_id(after)
    if before_id != after_id and op == "update":
        entry["before_id"] = before_id
        entry["after_id"] = after_id
    elif after_id or before_id:
        entry["id"] = after_id or before_id
    return entry


def _props(resource, field):
    if not isinstance(resource, dict):
        return {}
    value = resource.get(field)
    return value if isinstance(value, dict) else {}


def _secret_keys(resource):
    if not isinstance(resource, dict):
        return None
    return resource.get("additionalSecretOutputs")


def _text_id(resource):
    if not isinstance(resource, dict) or not isinstance(resource.get("id"), str):
        return ""
    return resource["id"]


def _properties(op, before, after, before_secrets, after_secrets, labels):
    before_view = redact_properties(before, before_secrets)
    after_view = redact_properties(after, after_secrets)
    rows = []
    for key in sorted(set(before) | set(after)):
        old = before.get(key, _MISSING)
        new = after.get(key, _MISSING)
        if op == "create" or old is _MISSING:
            rows.append({"key": key, "op": "add", "after": _present(key, after_view.get(key), labels)})
        elif op == "delete" or new is _MISSING:
            rows.append({"key": key, "op": "remove", "before": _present(key, before_view.get(key), labels)})
        elif _material(old) != _material(new):
            before_shown = before_view.get(key)
            after_shown = after_view.get(key)
            # File-backend checkpoints re-encrypt secrets on every update, so a
            # secret-to-secret replace is not a visible state change.
            if before_shown == REDACTED and after_shown == REDACTED:
                continue
            rows.append(
                {
                    "key": key,
                    "op": "replace",
                    "before": _present(key, before_shown, labels),
                    "after": _present(key, after_shown, labels),
                }
            )
    return rows


def _present(key, value, labels):
    if key != "users" or not isinstance(value, list) or not labels:
        return value
    if not value or not all(_id_token(item) for item in value):
        return value
    if not any(str(item) in labels for item in value):
        return value
    return [labels.get(str(item), str(item)) for item in value]


def _id_token(value):
    return isinstance(value, int) or (isinstance(value, str) and value.isdigit())


def _user_labels(deployment):
    labels = {}
    resources = deployment.get("resources") if isinstance(deployment, dict) else None
    if not isinstance(resources, list):
        return labels
    for resource in resources:
        if not isinstance(resource, dict):
            continue
        kind = resource.get("type") if isinstance(resource.get("type"), str) else ""
        if not kind.endswith("user:User"):
            continue
        name = _display_name(resource)
        if not name:
            continue
        for token in (resource.get("id"), _props(resource, "outputs").get("userId")):
            if _id_token(token):
                labels[str(token)] = name
    return labels


def _display_name(resource):
    for source in (_props(resource, "outputs"), _props(resource, "inputs")):
        name = source.get("name")
        if isinstance(name, str) and name.strip():
            return name.strip()
    return ""


def _material(value):
    if isinstance(value, list):
        return ["list", [_material(item) for item in value]]
    if isinstance(value, dict):
        if SIG_KEY in value or "ciphertext" in value or value.get("secret") is True:
            return ("secret", value.get("ciphertext"))
        return {key: _material(item) for key, item in value.items()}
    return value
