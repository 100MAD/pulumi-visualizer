"""OIDC helpers: discovery, auth URL, code exchange, and user provisioning."""

from __future__ import annotations

import base64
import json
import secrets
from typing import Any
from urllib.parse import urlencode, urljoin

import requests
from django.conf import settings
from django.contrib.auth import get_user_model
from rest_framework.authtoken.models import Token

_discovery_cache: dict[str, Any] | None = None


class OIDCError(Exception):
    """Raised when the identity provider returns an error or is misconfigured."""


def oidc_enabled() -> bool:
    if not settings.OIDC_CLIENT_ID:
        return False
    if settings.OIDC_ISSUER or settings.OIDC_DISCOVERY_URL:
        return True
    return bool(
        settings.OIDC_AUTH_ENDPOINT
        and settings.OIDC_TOKEN_ENDPOINT
        and settings.OIDC_USERINFO_ENDPOINT
    )


def oidc_config_public() -> dict[str, Any]:
    enabled = oidc_enabled()
    return {
        "oidc_enabled": enabled,
        "oidc_label": settings.OIDC_LABEL if enabled else "",
        "password_login": settings.OIDC_PASSWORD_LOGIN or not enabled,
    }


def _issuer_base() -> str:
    return settings.OIDC_ISSUER.rstrip("/") + "/"


def discovery() -> dict[str, Any]:
    """Return IdP endpoints from explicit config or OpenID discovery."""
    global _discovery_cache
    if _discovery_cache is not None:
        return _discovery_cache

    if (
        settings.OIDC_AUTH_ENDPOINT
        and settings.OIDC_TOKEN_ENDPOINT
        and settings.OIDC_USERINFO_ENDPOINT
    ):
        _discovery_cache = {
            "authorization_endpoint": settings.OIDC_AUTH_ENDPOINT,
            "token_endpoint": settings.OIDC_TOKEN_ENDPOINT,
            "userinfo_endpoint": settings.OIDC_USERINFO_ENDPOINT,
        }
        return _discovery_cache

    if not (settings.OIDC_ISSUER or settings.OIDC_DISCOVERY_URL):
        raise OIDCError(
            "OIDC is missing endpoints: set OIDC_AUTH_ENDPOINT / "
            "OIDC_TOKEN_ENDPOINT / OIDC_USERINFO_ENDPOINT, or OIDC_ISSUER"
        )

    url = settings.OIDC_DISCOVERY_URL or urljoin(
        _issuer_base(), ".well-known/openid-configuration"
    )
    try:
        response = requests.get(url, timeout=15)
        response.raise_for_status()
    except requests.RequestException as exc:
        raise OIDCError(f"Failed to fetch OIDC discovery document: {exc}") from exc

    data = response.json()
    for key in ("authorization_endpoint", "token_endpoint"):
        if key not in data:
            raise OIDCError(f"OIDC discovery document missing {key}")
    _discovery_cache = data
    return data


def clear_discovery_cache() -> None:
    global _discovery_cache
    _discovery_cache = None


def build_authorize_url(*, redirect_uri: str, state: str, nonce: str) -> str:
    meta = discovery()
    params = {
        "response_type": "code",
        "client_id": settings.OIDC_CLIENT_ID,
        "redirect_uri": redirect_uri,
        "scope": settings.OIDC_SCOPES,
        "state": state,
        "nonce": nonce,
    }
    return f"{meta['authorization_endpoint']}?{urlencode(params)}"


def exchange_code(*, code: str, redirect_uri: str) -> dict[str, Any]:
    meta = discovery()
    data = {
        "grant_type": "authorization_code",
        "code": code,
        "redirect_uri": redirect_uri,
        "client_id": settings.OIDC_CLIENT_ID,
        "client_secret": settings.OIDC_CLIENT_SECRET,
    }
    try:
        response = requests.post(
            meta["token_endpoint"],
            data=data,
            headers={"Accept": "application/json"},
            timeout=15,
        )
    except requests.RequestException as exc:
        raise OIDCError(f"Token exchange failed: {exc}") from exc

    if response.status_code >= 400:
        raise OIDCError(f"Token exchange rejected ({response.status_code})")

    tokens = response.json()
    if "access_token" not in tokens and "id_token" not in tokens:
        raise OIDCError("Token response missing access_token and id_token")
    return tokens


def fetch_userinfo(access_token: str) -> dict[str, Any]:
    meta = discovery()
    endpoint = meta.get("userinfo_endpoint")
    if not endpoint:
        raise OIDCError("OIDC configuration missing userinfo_endpoint")
    try:
        response = requests.get(
            endpoint,
            headers={"Authorization": f"Bearer {access_token}"},
            timeout=15,
        )
        response.raise_for_status()
    except requests.RequestException as exc:
        raise OIDCError(f"Failed to fetch userinfo: {exc}") from exc
    return response.json()


def claims_from_tokens(tokens: dict[str, Any]) -> dict[str, Any]:
    """Prefer userinfo; fall back to a decoded (unverified) id_token payload."""
    access = tokens.get("access_token")
    if access:
        try:
            return fetch_userinfo(access)
        except OIDCError:
            pass

    id_token = tokens.get("id_token")
    if not id_token:
        raise OIDCError("No user claims available from token response")

    # Decode payload without verification — the token was just issued over TLS
    # to our confidential client. Full JWT verification would need JWKS.
    try:
        payload = id_token.split(".")[1]
        padding = "=" * (-len(payload) % 4)
        return json.loads(base64.urlsafe_b64decode(payload + padding))
    except (IndexError, ValueError, json.JSONDecodeError) as exc:
        raise OIDCError("Could not decode id_token") from exc


def groups_from_claims(claims: dict[str, Any]) -> set[str]:
    raw = claims.get(settings.OIDC_GROUPS_CLAIM)
    if raw is None:
        return set()
    if isinstance(raw, str):
        return {raw.strip()} if raw.strip() else set()
    if isinstance(raw, (list, tuple, set)):
        return {str(item).strip() for item in raw if str(item).strip()}
    return set()


def assert_allowed_groups(claims: dict[str, Any]) -> None:
    """Require membership in at least one configured group (if any)."""
    allowed = settings.OIDC_ALLOWED_GROUPS
    if not allowed:
        return
    member = groups_from_claims(claims)
    if member.intersection(allowed):
        return
    raise OIDCError("Your account is not in an allowed group")


def username_from_claims(claims: dict[str, Any]) -> str:
    for key in ("preferred_username", "nickname", "email", "name", "sub"):
        value = claims.get(key)
        if isinstance(value, str) and value.strip():
            # Django usernames are limited; keep a stable, safe form.
            return value.strip()[:150]
    raise OIDCError("OIDC claims did not include a usable username")


def provision_user(claims: dict[str, Any]):
    User = get_user_model()
    username = username_from_claims(claims)
    email = claims.get("email") if isinstance(claims.get("email"), str) else ""
    email = email[:254]
    given = str(claims.get("given_name") or "")[:150]
    family = str(claims.get("family_name") or "")[:150]

    user, created = User.objects.get_or_create(
        username=username,
        defaults={
            "email": email,
            "first_name": given,
            "last_name": family,
        },
    )
    if created:
        user.set_unusable_password()
        user.save(update_fields=["password"])
    else:
        update_fields = []
        if email and user.email != email:
            user.email = email
            update_fields.append("email")
        if given and user.first_name != given:
            user.first_name = given
            update_fields.append("first_name")
        if family and user.last_name != family:
            user.last_name = family
            update_fields.append("last_name")
        if update_fields:
            user.save(update_fields=update_fields)

    token, _ = Token.objects.get_or_create(user=user)
    return user, token


def new_state() -> str:
    return secrets.token_urlsafe(32)


def redirect_uri_for(request) -> str:
    configured = settings.OIDC_REDIRECT_URI
    if configured:
        return configured
    return request.build_absolute_uri("/api/auth/oidc/callback/")
