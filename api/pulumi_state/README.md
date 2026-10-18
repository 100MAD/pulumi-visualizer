# Pulumi state

Read-only view of Pulumi DIY (S3) state. The Stacks page polls `/api/pulumi/` every 5 seconds. This app reads the bucket itself; the browser never receives credentials, ciphertext, or the secrets-provider block.

## Configuration

**Production (preferred):** set non-secret fields as env and mount keys from Vault:

| Env | Example |
|-----|---------|
| `PULUMI_BACKEND_NAME` | `homelab` |
| `RUSTFS_BUCKET` | `pulumi-state` |
| `RUSTFS_PREFIX` | _(empty)_ |
| `RUSTFS_ENDPOINT_URL` | `http://rustfs:9000` |
| `RUSTFS_REGION` | `us-east-1` |
| `RUSTFS_ADDRESSING_STYLE` | `path` |
| `AWS_ACCESS_KEY_ID` | _(Vault)_ |
| `AWS_SECRET_ACCESS_KEY` | _(Vault)_ |

**Local / multi-backend:** optional `PULUMI_STATE_BACKENDS` JSON list (wins when set):

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

`addressing_style` defaults to `path` when an endpoint is set. Leave both JSON and `RUSTFS_BUCKET` empty for an empty Stacks page. API responses include `name`, `bucket`, and `prefix` only.

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
