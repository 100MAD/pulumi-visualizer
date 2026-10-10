from django.contrib import admin
from django.urls import include, path

from . import health

urlpatterns = [
    path("admin/", admin.site.urls),
    path("health/live/", health.liveness, name="health_live"),
    path("health/ready/", health.readiness, name="health_ready"),
    path("api/auth/", include("accounts.urls")),
    path("api/pulumi/", include("pulumi_state.urls")),
]
