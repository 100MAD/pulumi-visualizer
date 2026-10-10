# Pulumi visualizer

Read-only browser for Pulumi DIY state stored in S3-compatible buckets (including RustFS). The page polls every 5 seconds. The API reads the bucket; the browser never receives credentials or secret values.

The interface uses the same dark theme as the ChatOps dashboard: indigo primary, slate surfaces, and the same cards, tables, and drawer.

## Run locally

```bash
cp env.example .env   # then set PULUMI_STATE_BACKENDS
cd api
python3 -m venv .venv
.venv/bin/pip install -r requirements.txt
.venv/bin/python manage.py migrate
.venv/bin/python manage.py createsuperuser
.venv/bin/python manage.py runserver 127.0.0.1:8000
```

In another shell:

```bash
cd frontend && npm install && npm run dev
```

Open http://127.0.0.1:5173/ and sign in with the user you created. The dev server proxies `/api` to Django.

```bash
cd api && .venv/bin/python manage.py test pulumi_state accounts
```

## OIDC / SSO

Set `OIDC_CLIENT_ID` and `OIDC_CLIENT_SECRET`, plus either `OIDC_ISSUER` or the explicit endpoint trio (`OIDC_AUTH_ENDPOINT`, `OIDC_TOKEN_ENDPOINT`, `OIDC_USERINFO_ENDPOINT`). Optional `OIDC_ALLOWED_GROUPS` (comma-separated) requires membership in at least one listed group from the `groups` claim.

Register this redirect URI at the IdP (must match `OIDC_REDIRECT_URI`):

```text
http://127.0.0.1:5173/api/auth/oidc/callback/
```

In Authentik, enable a Group Membership property mapping on the provider so `groups` appears in userinfo. Set `OIDC_PASSWORD_LOGIN=false` to require SSO.

## Health probes

Unauthenticated endpoints for Kubernetes / load balancers:

- `GET /health/live/` — process up (liveness)
- `GET /health/ready/` — database reachable (readiness); returns `503` when not

See `api/pulumi_state/README.md` for the backend layout, redaction rules, and routes.
