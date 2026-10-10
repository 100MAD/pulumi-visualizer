from django.urls import path

from . import api_views

app_name = "pulumi_state"

urlpatterns = [
    path("backends/", api_views.backends, name="backends"),
    path("backends/<str:backend>/projects/", api_views.projects, name="projects"),
    path(
        "backends/<str:backend>/projects/<str:project>/stacks/",
        api_views.stacks,
        name="stacks",
    ),
    path(
        "backends/<str:backend>/projects/<str:project>/stacks/<str:stack>/",
        api_views.stack,
        name="stack",
    ),
    path(
        "backends/<str:backend>/projects/<str:project>/stacks/<str:stack>/resources/",
        api_views.resources,
        name="resources",
    ),
    path(
        "backends/<str:backend>/projects/<str:project>/stacks/<str:stack>/resources/detail/",
        api_views.resource_detail,
        name="resource_detail",
    ),
    path(
        "backends/<str:backend>/projects/<str:project>/stacks/<str:stack>/updates/diff/",
        api_views.update_diff,
        name="update_diff",
    ),
    path(
        "backends/<str:backend>/projects/<str:project>/stacks/<str:stack>/updates/",
        api_views.updates,
        name="updates",
    ),
]
