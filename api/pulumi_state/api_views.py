from rest_framework.decorators import api_view, permission_classes
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response

from pulumi_state.config import BackendConfigError, NotFound
from pulumi_state.s3 import NotFound as MissingObject
from pulumi_state.s3 import StorageError
from pulumi_state.service import (
    get_resource,
    get_stack,
    get_update_diff,
    list_backends,
    list_projects,
    list_resources,
    list_stacks,
    list_updates,
)
from pulumi_state.state import BadName


def _respond(fn):
    try:
        return Response(fn())
    except (BadName, NotFound, MissingObject, StorageError, BackendConfigError) as exc:
        return Response({"error": str(exc)}, status=exc.status)


@api_view(["GET"])
@permission_classes([IsAuthenticated])
def backends(request):
    return _respond(list_backends)


@api_view(["GET"])
@permission_classes([IsAuthenticated])
def projects(request, backend):
    return _respond(lambda: list_projects(backend))


@api_view(["GET"])
@permission_classes([IsAuthenticated])
def stacks(request, backend, project):
    return _respond(lambda: list_stacks(backend, project))


@api_view(["GET"])
@permission_classes([IsAuthenticated])
def stack(request, backend, project, stack):
    return _respond(lambda: get_stack(backend, project, stack))


@api_view(["GET"])
@permission_classes([IsAuthenticated])
def resources(request, backend, project, stack):
    return _respond(lambda: list_resources(backend, project, stack))


@api_view(["GET"])
@permission_classes([IsAuthenticated])
def resource_detail(request, backend, project, stack):
    urn = request.query_params.get("urn", "")
    return _respond(lambda: get_resource(backend, project, stack, urn))


@api_view(["GET"])
@permission_classes([IsAuthenticated])
def updates(request, backend, project, stack):
    return _respond(lambda: list_updates(backend, project, stack))


@api_view(["GET"])
@permission_classes([IsAuthenticated])
def update_diff(request, backend, project, stack):
    update_id = request.query_params.get("id", "")
    return _respond(lambda: get_update_diff(backend, project, stack, update_id))
