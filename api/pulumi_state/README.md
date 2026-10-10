# Pulumi state

Read-only view of Pulumi DIY (S3) state. The Stacks page polls `/api/pulumi/` every 5 seconds. This app reads the bucket itself; the browser never receives credentials, ciphertext, or the secrets-provider block.

## Configuration

`PULUMI_STATE_BACKENDS` is a JSON list:

```json
[
  {
    "name": "homelab",
    "bucket": "pulumi-state",
    "prefix": "",
    "endpoint_url": "https://s3.example",
    "region": "us-east-1",
    "access_key_id": "your-access-key",
    "secret_access_key": "your-secret-key",
    "addressing_style": "path"
  }
]
```

`addressing_style` is `path` when `endpoint_url` is set and omitted, and `auto` otherwise. Leave the variable empty to show an empty Stacks page. API responses include `name`, `bucket`, and `prefix` only.

Objects are read from the file-backend layout:

- `.pulumi/stacks/<project>/<stack>.json` — current checkpoint
- `.pulumi/history/<project>/<stack>/<version>.json` — update history (latest 30)
- `.pulumi/locks/<project>/<stack>/` — lock indicator

There are no models and no migrations.

## API

Token auth (password or OIDC). All routes are under `/api/pulumi/`. Auth endpoints live under `/api/auth/` (`config/`, `token/`, `me/`, `oidc/login/`, `oidc/callback/`).

- `GET backends/`
- `GET backends/<backend>/projects/`
- `GET backends/<backend>/projects/<project>/stacks/`
- `GET backends/<backend>/projects/<project>/stacks/<stack>/`
- `GET .../resources/`
- `GET .../resources/detail/?urn=`
- `GET .../updates/`
- `GET .../updates/diff/?id=<history-file>` compares that update's checkpoint with the previous one. Checkpoint snapshots (`*.checkpoint.json`) are not listed as updates.

Secret property values (the Pulumi sigil object, secret output wrappers, `additionalSecretOutputs`, and history config entries with `secret: true`) are replaced with `{"secret": true}`. `secrets_providers` and each history entry's `environment` map are dropped. Values are not decrypted.

```bash
python manage.py test pulumi_state
```
