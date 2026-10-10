"""Read Pulumi DIY state from S3 and return redacted summaries."""

from pulumi_state.config import NotFound, public_backend, require_backend
from pulumi_state.diff import diff_deployments
from pulumi_state.redact import redact_config, redact_properties
from pulumi_state.s3 import client_for, get_json, list_objects
from pulumi_state.s3 import NotFound as MissingObject
from pulumi_state.state import (
    HISTORY_LIMIT,
    BadName,
    deployment_from_checkpoint,
    history_prefix,
    is_stack_resource,
    iter_resources,
    locks_prefix,
    project_names,
    project_prefix,
    resource_count,
    sort_history_keys,
    stack_key,
    stack_names,
    stacks_prefix,
    summarize_history,
    type_counts,
    urn_name,
    validate_segment,
    version_from_key,
)


def list_backends():
    from pulumi_state.config import configured_backends

    return {"backends": [public_backend(backend) for backend in configured_backends()]}


def list_projects(backend_name):
    backend = require_backend(backend_name)
    client = client_for(backend)
    root = stacks_prefix(backend)
    _keys, prefixes = list_objects(client, backend["bucket"], root, delimiter="/")
    projects = []
    for name in project_names(root, prefixes):
        project_root = project_prefix(backend, name)
        keys, _prefixes = list_objects(client, backend["bucket"], project_root, delimiter="/")
        projects.append({"name": name, "stack_count": len(stack_names(project_root, keys))})
    return {"projects": projects}


def list_stacks(backend_name, project):
    backend = require_backend(backend_name)
    validate_segment(project)
    client = client_for(backend)
    root = project_prefix(backend, project)
    keys, _prefixes = list_objects(client, backend["bucket"], root, delimiter="/")
    stacks = []
    for name in stack_names(root, keys):
        try:
            deployment = _deployment(client, backend, project, name)
        except NotFound:
            continue
        latest = _latest_history(client, backend, project, name)
        updated = None
        if latest:
            updated = latest.get("end_time") or latest.get("start_time")
        stacks.append(
            {
                "name": name,
                "resource_count": resource_count(deployment),
                "last_update": _update_summary(latest),
                "updated_at": updated,
            }
        )
    return {"stacks": stacks}


def get_stack(backend_name, project, stack):
    backend = require_backend(backend_name)
    validate_segment(project)
    validate_segment(stack)
    client = client_for(backend)
    deployment = _deployment(client, backend, project, stack)
    latest = _latest_history(client, backend, project, stack)
    manifest = deployment.get("manifest") if isinstance(deployment.get("manifest"), dict) else {}
    lock_keys, _prefixes = list_objects(
        client, backend["bucket"], locks_prefix(backend, project, stack)
    )
    return {
        "backend": backend["name"],
        "bucket": backend["bucket"],
        "project": project,
        "stack": stack,
        "resource_count": resource_count(deployment),
        "outputs": _stack_outputs(deployment),
        "types": type_counts(deployment),
        "last_update": _update_summary(latest),
        "config": latest.get("config") if latest else {},
        "manifest": {
            "time": manifest.get("time") if isinstance(manifest.get("time"), str) else None,
            "version": manifest.get("version") if isinstance(manifest.get("version"), str) else None,
        },
        "locked": bool(lock_keys),
    }


def list_resources(backend_name, project, stack):
    backend = require_backend(backend_name)
    validate_segment(project)
    validate_segment(stack)
    client = client_for(backend)
    deployment = _deployment(client, backend, project, stack)
    resources = [
        _summarize_resource(resource)
        for resource in iter_resources(deployment)
        if not is_stack_resource(resource)
    ]
    return {"resources": resources}


def get_resource(backend_name, project, stack, urn):
    if not isinstance(urn, str) or not urn:
        raise BadName("urn is required")
    backend = require_backend(backend_name)
    validate_segment(project)
    validate_segment(stack)
    client = client_for(backend)
    deployment = _deployment(client, backend, project, stack)
    for resource in iter_resources(deployment):
        if resource.get("urn") == urn:
            return _detail_resource(resource)
    raise NotFound("resource not found")


def list_updates(backend_name, project, stack):
    backend = require_backend(backend_name)
    validate_segment(project)
    validate_segment(stack)
    client = client_for(backend)
    updates = []
    for key, doc, version in _history_docs(client, backend, project, stack, HISTORY_LIMIT):
        if _is_checkpoint_doc(doc):
            continue
        summary = summarize_history(doc, version)
        if summary:
            summary["id"] = _update_id(key)
            updates.append(summary)
    return {"updates": updates}


def get_update_diff(backend_name, project, stack, update_id):
    if not isinstance(update_id, str) or not update_id.endswith(".json"):
        raise BadName()
    if update_id.endswith(".checkpoint.json"):
        raise BadName()
    validate_segment(update_id)
    backend = require_backend(backend_name)
    validate_segment(project)
    validate_segment(stack)
    client = client_for(backend)
    keys, _prefixes = list_objects(client, backend["bucket"], history_prefix(backend, project, stack))
    history_keys = _update_keys(keys)
    current_key = next((key for key in history_keys if _update_id(key) == update_id), None)
    if current_key is None:
        raise NotFound("update not found")
    try:
        history = get_json(client, backend["bucket"], current_key)
    except MissingObject:
        raise NotFound("update not found") from None
    summary = summarize_history(history, version_from_key(current_key)) or {}
    current = _checkpoint_deployment(client, backend, current_key, history)
    index = history_keys.index(current_key)
    previous_key = history_keys[index + 1] if index + 1 < len(history_keys) else None
    previous_doc = None
    if previous_key is not None:
        try:
            previous_doc = get_json(client, backend["bucket"], previous_key)
        except MissingObject:
            previous_doc = None
    previous = (
        _checkpoint_deployment(client, backend, previous_key, previous_doc)
        if previous_key is not None
        else {}
    )
    available = current is not None and previous is not None
    return {
        "id": update_id,
        "version": summary.get("version"),
        "kind": summary.get("kind") or "",
        "result": summary.get("result") or "",
        "message": summary.get("message") or "",
        "start_time": summary.get("start_time"),
        "end_time": summary.get("end_time"),
        "available": available,
        "changes": diff_deployments(previous, current) if available else [],
    }


def _deployment(client, backend, project, stack):
    try:
        doc = get_json(client, backend["bucket"], stack_key(backend, project, stack))
    except MissingObject:
        raise NotFound("stack not found") from None
    return deployment_from_checkpoint(doc)


def _history_docs(client, backend, project, stack, limit):
    keys, _prefixes = list_objects(client, backend["bucket"], history_prefix(backend, project, stack))
    docs = []
    for key in _update_keys(keys)[:limit]:
        try:
            doc = get_json(client, backend["bucket"], key)
        except MissingObject:
            continue
        docs.append((key, doc, version_from_key(key)))
    return docs


def _update_keys(keys):
    return [
        key
        for key in sort_history_keys(keys)
        if not _update_id(key).endswith(".checkpoint.json")
    ]


def _update_id(key):
    return key.rsplit("/", 1)[-1]


def _is_checkpoint_doc(doc):
    return isinstance(doc, dict) and isinstance(doc.get("checkpoint"), dict) and "kind" not in doc


def _checkpoint_deployment(client, backend, history_key, history_doc):
    name = _update_id(history_key)
    if name.endswith(".history.json"):
        checkpoint_key = history_key[: -len(name)] + name[: -len(".history.json")] + ".checkpoint.json"
        try:
            return deployment_from_checkpoint(get_json(client, backend["bucket"], checkpoint_key))
        except MissingObject:
            pass
    if isinstance(history_doc, dict) and isinstance(history_doc.get("deployment"), dict):
        return deployment_from_checkpoint(history_doc["deployment"])
    return None


def _latest_history(client, backend, project, stack):
    docs = _history_docs(client, backend, project, stack, 1)
    if not docs:
        return None
    _key, doc, version = docs[0]
    summary = summarize_history(doc, version)
    if summary is None:
        return None
    summary["config"] = redact_config(doc.get("config"))
    return summary


def _update_summary(latest):
    if not latest:
        return None
    return {key: value for key, value in latest.items() if key != "config"}


def _stack_outputs(deployment):
    for resource in iter_resources(deployment):
        if is_stack_resource(resource):
            return redact_properties(
                resource.get("outputs") or {},
                resource.get("additionalSecretOutputs"),
            )
    return {}


def _summarize_resource(resource):
    urn = resource.get("urn") or ""
    dependencies = resource.get("dependencies") or []
    if not isinstance(dependencies, list):
        dependencies = []
    provider = resource.get("provider") if isinstance(resource.get("provider"), str) else ""
    modified = resource.get("modified") if isinstance(resource.get("modified"), str) else None
    return {
        "urn": urn,
        "name": urn_name(urn),
        "type": resource.get("type") if isinstance(resource.get("type"), str) else "",
        "parent": resource.get("parent") if isinstance(resource.get("parent"), str) else "",
        "provider": provider,
        "modified": modified,
        "id": resource.get("id") if isinstance(resource.get("id"), str) else "",
        "protect": bool(resource.get("protect")),
        "dependencies": [item for item in dependencies if isinstance(item, str)],
    }


def _detail_resource(resource):
    summary = _summarize_resource(resource)
    created = resource.get("created") if isinstance(resource.get("created"), str) else None
    summary["created"] = created
    summary["inputs"] = redact_properties(resource.get("inputs") or {})
    summary["outputs"] = redact_properties(
        resource.get("outputs") or {},
        resource.get("additionalSecretOutputs"),
    )
    return summary
