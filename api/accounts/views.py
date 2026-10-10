from urllib.parse import urlencode

from django.conf import settings
from django.http import HttpResponseBadRequest, HttpResponseRedirect
from django.views.decorators.http import require_GET
from rest_framework.authtoken.views import ObtainAuthToken
from rest_framework.decorators import api_view, permission_classes
from rest_framework.permissions import AllowAny, IsAuthenticated
from rest_framework.response import Response

from . import oidc


@api_view(["GET"])
@permission_classes([IsAuthenticated])
def me(request):
    return Response({"username": request.user.username})


@api_view(["GET"])
@permission_classes([AllowAny])
def auth_config(request):
    return Response(oidc.oidc_config_public())


class PasswordLoginView(ObtainAuthToken):
    """Username/password token login — disabled when OIDC_PASSWORD_LOGIN is false."""

    def post(self, request, *args, **kwargs):
        if oidc.oidc_enabled() and not settings.OIDC_PASSWORD_LOGIN:
            return Response(
                {"detail": "Password login is disabled. Use SSO."},
                status=403,
            )
        return super().post(request, *args, **kwargs)


@require_GET
def oidc_login(request):
    if not oidc.oidc_enabled():
        return HttpResponseBadRequest("OIDC is not configured")

    state = oidc.new_state()
    nonce = oidc.new_state()
    redirect_uri = oidc.redirect_uri_for(request)
    request.session["oidc_state"] = state
    request.session["oidc_nonce"] = nonce
    request.session["oidc_redirect_uri"] = redirect_uri

    try:
        url = oidc.build_authorize_url(
            redirect_uri=redirect_uri, state=state, nonce=nonce
        )
    except oidc.OIDCError as exc:
        return HttpResponseBadRequest(str(exc))
    return HttpResponseRedirect(url)


@require_GET
def oidc_callback(request):
    if not oidc.oidc_enabled():
        return HttpResponseBadRequest("OIDC is not configured")

    error = request.GET.get("error")
    if error:
        desc = request.GET.get("error_description") or error
        return _frontend_error(desc)

    state = request.GET.get("state")
    code = request.GET.get("code")
    expected = request.session.pop("oidc_state", None)
    redirect_uri = request.session.pop("oidc_redirect_uri", None) or oidc.redirect_uri_for(
        request
    )
    request.session.pop("oidc_nonce", None)

    if not code or not state or not expected or state != expected:
        return _frontend_error("Invalid OIDC state")

    try:
        tokens = oidc.exchange_code(code=code, redirect_uri=redirect_uri)
        claims = oidc.claims_from_tokens(tokens)
        oidc.assert_allowed_groups(claims)
        user, token = oidc.provision_user(claims)
    except oidc.OIDCError as exc:
        return _frontend_error(str(exc))

    # Put credentials in the hash so they are not sent to the frontend origin
    # as a query string (access logs / Referer).
    params = urlencode({"token": token.key, "username": user.username})
    return HttpResponseRedirect(f"{settings.FRONTEND_URL.rstrip('/')}/#oidc={params}")


def _frontend_error(message: str):
    params = urlencode({"auth_error": message})
    return HttpResponseRedirect(f"{settings.FRONTEND_URL.rstrip('/')}/#oidc={params}")
