from unittest.mock import patch

from django.contrib.auth import get_user_model
from django.test import Client, TestCase, override_settings
from rest_framework.authtoken.models import Token
from rest_framework.test import APIClient

from accounts import oidc


DISCOVERY = {
    "authorization_endpoint": "https://idp.example/authorize",
    "token_endpoint": "https://idp.example/token",
    "userinfo_endpoint": "https://idp.example/userinfo",
}

OIDC_SETTINGS = {
    "OIDC_CLIENT_ID": "pulumi-viz",
    "OIDC_CLIENT_SECRET": "secret",
    "OIDC_ISSUER": "https://idp.example/application/o/pulumi-viz/",
    "OIDC_DISCOVERY_URL": "",
    "OIDC_AUTH_ENDPOINT": "",
    "OIDC_TOKEN_ENDPOINT": "",
    "OIDC_USERINFO_ENDPOINT": "",
    "OIDC_SCOPES": "openid profile email",
    "OIDC_LABEL": "Sign in with Authentik",
    "OIDC_REDIRECT_URI": "http://127.0.0.1:5173/api/auth/oidc/callback/",
    "OIDC_PASSWORD_LOGIN": True,
    "OIDC_ALLOWED_GROUPS": set(),
    "OIDC_GROUPS_CLAIM": "groups",
    "FRONTEND_URL": "http://127.0.0.1:5173",
}


@override_settings(**OIDC_SETTINGS)
class AuthConfigTests(TestCase):
    def setUp(self):
        oidc.clear_discovery_cache()
        self.client = APIClient()

    def test_config_when_enabled(self):
        response = self.client.get("/api/auth/config/")
        self.assertEqual(response.status_code, 200)
        self.assertEqual(
            response.json(),
            {
                "oidc_enabled": True,
                "oidc_label": "Sign in with Authentik",
                "password_login": True,
            },
        )

    @override_settings(OIDC_CLIENT_ID="")
    def test_config_when_disabled(self):
        response = self.client.get("/api/auth/config/")
        self.assertEqual(response.status_code, 200)
        body = response.json()
        self.assertFalse(body["oidc_enabled"])
        self.assertTrue(body["password_login"])


@override_settings(**OIDC_SETTINGS)
class OIDCFlowTests(TestCase):
    def setUp(self):
        oidc.clear_discovery_cache()
        self.client = Client()

    @patch("accounts.oidc.discovery", return_value=DISCOVERY)
    def test_login_redirects_to_idp(self, _discovery):
        response = self.client.get("/api/auth/oidc/login/")
        self.assertEqual(response.status_code, 302)
        self.assertTrue(response["Location"].startswith("https://idp.example/authorize?"))
        self.assertIn("client_id=pulumi-viz", response["Location"])
        self.assertIn("state=", response["Location"])
        self.assertTrue(self.client.session.get("oidc_state"))

    @patch("accounts.oidc.discovery", return_value=DISCOVERY)
    @patch("accounts.oidc.exchange_code")
    @patch("accounts.oidc.claims_from_tokens")
    def test_callback_issues_token(self, claims, exchange, _discovery):
        exchange.return_value = {"access_token": "at"}
        claims.return_value = {
            "preferred_username": "ada",
            "email": "ada@example.com",
            "given_name": "Ada",
            "family_name": "Lovelace",
        }

        session = self.client.session
        session["oidc_state"] = "state-abc"
        session["oidc_redirect_uri"] = OIDC_SETTINGS["OIDC_REDIRECT_URI"]
        session.save()

        response = self.client.get(
            "/api/auth/oidc/callback/",
            {"code": "auth-code", "state": "state-abc"},
        )
        self.assertEqual(response.status_code, 302)
        location = response["Location"]
        self.assertTrue(location.startswith("http://127.0.0.1:5173/#oidc="))
        self.assertIn("token=", location)
        self.assertIn("username=ada", location)

        user = get_user_model().objects.get(username="ada")
        self.assertEqual(user.email, "ada@example.com")
        self.assertFalse(user.has_usable_password())
        self.assertTrue(Token.objects.filter(user=user).exists())

    def test_callback_rejects_bad_state(self):
        session = self.client.session
        session["oidc_state"] = "expected"
        session.save()
        response = self.client.get(
            "/api/auth/oidc/callback/",
            {"code": "auth-code", "state": "wrong"},
        )
        self.assertEqual(response.status_code, 302)
        self.assertIn("#oidc=", response["Location"])
        self.assertIn("auth_error=", response["Location"])


@override_settings(**{**OIDC_SETTINGS, "OIDC_PASSWORD_LOGIN": False})
class PasswordLoginGateTests(TestCase):
    def setUp(self):
        self.client = APIClient()
        user = get_user_model().objects.create_user("bob", password="secret")
        self.user = user

    def test_password_login_blocked_when_disabled(self):
        response = self.client.post(
            "/api/auth/token/",
            {"username": "bob", "password": "secret"},
            format="json",
        )
        self.assertEqual(response.status_code, 403)


class UsernameFromClaimsTests(TestCase):
    def test_prefers_preferred_username(self):
        self.assertEqual(
            oidc.username_from_claims({"preferred_username": "ada", "email": "a@b.c"}),
            "ada",
        )

    def test_falls_back_to_sub(self):
        self.assertEqual(oidc.username_from_claims({"sub": "oidc|123"}), "oidc|123")


class AllowedGroupsTests(TestCase):
    @override_settings(OIDC_ALLOWED_GROUPS=set(), OIDC_GROUPS_CLAIM="groups")
    def test_no_allowlist_passes(self):
        oidc.assert_allowed_groups({"groups": []})

    @override_settings(
        OIDC_ALLOWED_GROUPS={"zarrino-infra"},
        OIDC_GROUPS_CLAIM="groups",
    )
    def test_matching_group_passes(self):
        oidc.assert_allowed_groups({"groups": ["zarrino-infra", "other"]})

    @override_settings(
        OIDC_ALLOWED_GROUPS={"zarrino-infra"},
        OIDC_GROUPS_CLAIM="groups",
    )
    def test_missing_group_raises(self):
        with self.assertRaises(oidc.OIDCError):
            oidc.assert_allowed_groups({"groups": ["unrelated"]})


@override_settings(
    OIDC_CLIENT_ID="pulumi-viz",
    OIDC_CLIENT_SECRET="secret",
    OIDC_ISSUER="",
    OIDC_DISCOVERY_URL="",
    OIDC_AUTH_ENDPOINT="https://idp.example/authorize",
    OIDC_TOKEN_ENDPOINT="https://idp.example/token",
    OIDC_USERINFO_ENDPOINT="https://idp.example/userinfo",
)
class ExplicitEndpointTests(TestCase):
    def setUp(self):
        oidc.clear_discovery_cache()

    def test_discovery_uses_explicit_endpoints(self):
        meta = oidc.discovery()
        self.assertEqual(meta["authorization_endpoint"], "https://idp.example/authorize")
        self.assertEqual(meta["token_endpoint"], "https://idp.example/token")
        self.assertEqual(meta["userinfo_endpoint"], "https://idp.example/userinfo")

    def test_enabled_without_issuer(self):
        self.assertTrue(oidc.oidc_enabled())


@override_settings(**{**OIDC_SETTINGS, "OIDC_ALLOWED_GROUPS": {"zarrino-infra"}})
class OIDCGroupGateFlowTests(TestCase):
    def setUp(self):
        oidc.clear_discovery_cache()
        self.client = Client()

    @patch("accounts.oidc.discovery", return_value=DISCOVERY)
    @patch("accounts.oidc.exchange_code", return_value={"access_token": "at"})
    @patch(
        "accounts.oidc.claims_from_tokens",
        return_value={"preferred_username": "ada", "groups": ["unrelated"]},
    )
    def test_callback_rejects_disallowed_group(self, *_mocks):
        session = self.client.session
        session["oidc_state"] = "state-abc"
        session["oidc_redirect_uri"] = OIDC_SETTINGS["OIDC_REDIRECT_URI"]
        session.save()
        response = self.client.get(
            "/api/auth/oidc/callback/",
            {"code": "auth-code", "state": "state-abc"},
        )
        self.assertEqual(response.status_code, 302)
        self.assertIn("auth_error=", response["Location"])
        self.assertFalse(get_user_model().objects.filter(username="ada").exists())

