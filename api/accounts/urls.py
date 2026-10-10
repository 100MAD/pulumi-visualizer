from django.urls import path

from . import views

urlpatterns = [
    path("config/", views.auth_config, name="auth_config"),
    path("token/", views.PasswordLoginView.as_view(), name="api_token"),
    path("me/", views.me, name="api_me"),
    path("oidc/login/", views.oidc_login, name="oidc_login"),
    path("oidc/callback/", views.oidc_callback, name="oidc_callback"),
]
