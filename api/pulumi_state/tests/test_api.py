import hashlib
import json
from unittest.mock import patch

from django.contrib.auth import get_user_model
from django.test import TestCase, override_settings
from rest_framework.test import APIClient

from pulumi_state.s3 import clear_cache

SIG = "4dabf18193072939515e22adb298388d"
SECRET = "1b47061264138c4ac30d75fd1eb44270"
BUCKET_URN = "urn:pulumi:dev::pulumi-app::aws:s3/bucket:Bucket::data"
STACK_URN = "urn:pulumi:dev::pulumi-app::pulumi:pulumi:Stack::dev"

BACKENDS = [
    {
        "name": "homelab",
        "bucket": "pulumi-state",
        "prefix": "",
        "endpoint_url": "https://s3.example",
        "region": "us-east-1",
        "access_key_id": "AKIA-EXAMPLE",
        "secret_access_key": "secret-key-should-not-leak",
        "addressing_style": "path",
    }
]


def _secret(ciphertext):
    return {SIG: SECRET, "ciphertext": ciphertext}


CHECKPOINT = {
    "version": 3,
    "checkpoint": {
        "stack": "dev",
        "latest": {
            "manifest": {"time": "2026-10-06T08:00:00Z", "magic": "abc", "version": "v3.140.0"},
            "secrets_providers": {"type": "passphrase", "state": {"salt": "salty-key-material"}},
            "resources": [
                {
                    "urn": STACK_URN,
                    "type": "pulumi:pulumi:Stack",
                    "custom": False,
                    "outputs": {"url": "https://example", "password": _secret("v1:stack-password")},
                },
                {
                    "urn": BUCKET_URN,
                    "type": "aws:s3/bucket:Bucket",
                    "custom": True,
                    "id": "data-bucket",
                    "parent": STACK_URN,
                    "provider": "urn:pulumi:dev::pulumi-app::pulumi:providers:aws::default",
                    "modified": "2026-10-01T00:00:00Z",
                    "inputs": {"bucket": "data"},
                    "outputs": {"arn": "arn:aws:s3:::data", "token": "plain-token-value"},
                    "additionalSecretOutputs": ["token"],
                    "dependencies": [],
                },
            ],
        },
    },
}

HISTORY = {
    "version": 4,
    "kind": "destroy",
    "startTime": 1759700000,
    "endTime": 1759700300,
    "result": "succeeded",
    "message": "cleanup",
    "environment": {"PULUMI_CONFIG_PASSPHRASE": "do-not-leak"},
    "config": {
        "aws:region": {"string": "us-east-1"},
        "db:password": {"string": "v1:hidden-password", "secret": True},
    },
    "resourceChanges": {"delete": 1},
    "deployment": {"resources": CHECKPOINT["checkpoint"]["latest"]["resources"]},
}


class FakeBody:
    def __init__(self, data):
        self._data = data

    def read(self):
        return self._data


class _S3Error(Exception):
    def __init__(self, code):
        super().__init__(code)
        self.response = {"Error": {"Code": code}}


class FakeS3:
    def __init__(self, objects):
        self.objects = {}
        self.etags = {}
        self.reads = 0
        for key, value in objects.items():
            self.add(key, value)

    def add(self, key, value):
        raw = value if isinstance(value, bytes) else json.dumps(value).encode()
        self.objects[key] = raw
        self.etags[key] = '"' + hashlib.sha1(raw).hexdigest() + '"'

    def get_paginator(self, name):
        if name != "list_objects_v2":
            raise AssertionError(name)
        return self

    def paginate(self, Bucket, Prefix="", Delimiter=None):
        keys = []
        prefixes = set()
        for key in self.objects:
            if not key.startswith(Prefix):
                continue
            rest = key[len(Prefix) :]
            if Delimiter and Delimiter in rest:
                prefixes.add(Prefix + rest.split(Delimiter, 1)[0] + Delimiter)
            else:
                keys.append(key)
        return [
            {
                "Contents": [{"Key": key} for key in keys],
                "CommonPrefixes": [{"Prefix": prefix} for prefix in sorted(prefixes)],
            }
        ]

    def get_object(self, Bucket, Key, IfNoneMatch=None):
        if Key not in self.objects:
            raise _S3Error("NoSuchKey")
        etag = self.etags[Key]
        if IfNoneMatch and IfNoneMatch == etag:
            raise _S3Error("304")
        self.reads += 1
        return {"ETag": etag, "Body": FakeBody(self.objects[Key])}


def _objects():
    return {
        ".pulumi/stacks/pulumi-app/dev.json": CHECKPOINT,
        ".pulumi/history/pulumi-app/dev/4.json": HISTORY,
        ".pulumi/locks/pulumi-app/dev/lock": {"holder": "ci"},
    }


@override_settings(PULUMI_STATE_BACKENDS=BACKENDS)
class PulumiApiTests(TestCase):
    def setUp(self):
        clear_cache()
        self.fake = FakeS3(_objects())
        self.patcher = patch("pulumi_state.service.client_for", return_value=self.fake)
        self.patcher.start()
        self.addCleanup(self.patcher.stop)
        user = get_user_model().objects.create_user("op", password="secret")
        self.client = APIClient()
        self.client.force_authenticate(user)

    def test_requires_auth(self):
        client = APIClient()
        response = client.get("/api/pulumi/backends/")
        self.assertEqual(response.status_code, 401)

    def test_backends_hide_credentials(self):
        response = self.client.get("/api/pulumi/backends/")
        self.assertEqual(response.status_code, 200)
        body = response.content.decode()
        self.assertNotIn("secret-key-should-not-leak", body)
        self.assertNotIn("AKIA-EXAMPLE", body)
        self.assertEqual(
            response.json()["backends"],
            [{"name": "homelab", "bucket": "pulumi-state", "prefix": ""}],
        )

    def test_projects_and_stacks(self):
        projects = self.client.get("/api/pulumi/backends/homelab/projects/")
        self.assertEqual(projects.status_code, 200)
        self.assertEqual(projects.json()["projects"], [{"name": "pulumi-app", "stack_count": 1}])
        stacks = self.client.get("/api/pulumi/backends/homelab/projects/pulumi-app/stacks/")
        self.assertEqual(stacks.status_code, 200)
        stack = stacks.json()["stacks"][0]
        self.assertEqual(stack["name"], "dev")
        self.assertEqual(stack["resource_count"], 1)
        self.assertEqual(stack["last_update"]["kind"], "destroy")
        self.assertEqual(stack["last_update"]["version"], 4)

    def test_stack_detail_redacts_secrets(self):
        response = self.client.get("/api/pulumi/backends/homelab/projects/pulumi-app/stacks/dev/")
        self.assertEqual(response.status_code, 200)
        body = response.content.decode()
        for leaked in (
            "salty-key-material",
            "do-not-leak",
            "v1:stack-password",
            "v1:hidden-password",
            "plain-token-value",
            "secret-key-should-not-leak",
        ):
            self.assertNotIn(leaked, body)
        payload = response.json()
        self.assertEqual(payload["resource_count"], 1)
        self.assertEqual(payload["outputs"]["url"], "https://example")
        self.assertEqual(payload["outputs"]["password"], {"secret": True})
        self.assertEqual(payload["config"]["db:password"], {"secret": True})
        self.assertEqual(payload["config"]["aws:region"]["value"], "us-east-1")
        self.assertEqual(payload["last_update"]["result"], "succeeded")
        self.assertTrue(payload["locked"])
        self.assertNotIn("secrets_providers", payload)
        self.assertNotIn("environment", payload["last_update"])

    def test_resource_detail_redacts_additional_secret_outputs(self):
        response = self.client.get(
            "/api/pulumi/backends/homelab/projects/pulumi-app/stacks/dev/resources/detail/",
            {"urn": BUCKET_URN},
        )
        self.assertEqual(response.status_code, 200)
        body = response.content.decode()
        self.assertNotIn("plain-token-value", body)
        payload = response.json()
        self.assertEqual(payload["name"], "data")
        self.assertEqual(payload["outputs"]["token"], {"secret": True})
        self.assertEqual(payload["outputs"]["arn"], "arn:aws:s3:::data")
        self.assertEqual(payload["inputs"]["bucket"], "data")

    def test_resources_list_omits_stack_resource_and_properties(self):
        response = self.client.get(
            "/api/pulumi/backends/homelab/projects/pulumi-app/stacks/dev/resources/"
        )
        self.assertEqual(response.status_code, 200)
        resources = response.json()["resources"]
        self.assertEqual(len(resources), 1)
        self.assertEqual(resources[0]["urn"], BUCKET_URN)
        self.assertNotIn("inputs", resources[0])
        self.assertNotIn("outputs", resources[0])

    def test_updates_are_capped_and_drop_environment(self):
        for version in range(1, 32):
            self.fake.add(
                ".pulumi/history/pulumi-app/dev/%d.json" % version,
                {
                    "version": version,
                    "kind": "destroy" if version == 4 else "update",
                    "result": "succeeded",
                    "environment": {"PULUMI_CONFIG_PASSPHRASE": "do-not-leak"},
                    "deployment": {"resources": [{"token": "plain-token-value"}]},
                    "config": {"db:password": {"string": "v1:hidden-password", "secret": True}},
                },
            )
        clear_cache()
        response = self.client.get(
            "/api/pulumi/backends/homelab/projects/pulumi-app/stacks/dev/updates/"
        )
        self.assertEqual(response.status_code, 200)
        updates = response.json()["updates"]
        self.assertEqual(len(updates), 30)
        self.assertEqual(updates[0]["version"], 31)
        body = response.content.decode()
        self.assertNotIn("do-not-leak", body)
        self.assertNotIn("plain-token-value", body)
        self.assertNotIn("hidden-password", body)

    def test_update_diff_compares_checkpoints_and_redacts(self):
        deleted_urn = "urn:pulumi:dev::pulumi-app::aws:s3/bucket:Bucket::old"
        created_urn = "urn:pulumi:dev::pulumi-app::aws:s3/bucket:Bucket::new"
        before = {
            "version": 3,
            "checkpoint": {
                "latest": {
                    "secrets_providers": {"state": {"salt": "do-not-leak-salt"}},
                    "resources": [
                        {"urn": STACK_URN, "type": "pulumi:pulumi:Stack", "outputs": {"url": "https://example"}},
                        {
                            "urn": BUCKET_URN,
                            "type": "aws:s3/bucket:Bucket",
                            "id": "data-bucket",
                            "inputs": {"bucket": "data"},
                            "outputs": {"arn": "arn:old", "token": _secret("cipher-old")},
                        },
                        {
                            "urn": deleted_urn,
                            "type": "aws:s3/bucket:Bucket",
                            "id": "old",
                            "inputs": {"bucket": "old"},
                            "outputs": {"arn": "arn:old-bucket"},
                        },
                    ],
                }
            },
        }
        after = {
            "version": 3,
            "checkpoint": {
                "latest": {
                    "resources": [
                        {"urn": STACK_URN, "type": "pulumi:pulumi:Stack", "outputs": {"url": "https://example"}},
                        {
                            "urn": BUCKET_URN,
                            "type": "aws:s3/bucket:Bucket",
                            "id": "data-bucket",
                            "inputs": {"bucket": "data", "tags": {"env": "prod"}},
                            "outputs": {"arn": "arn:new", "token": _secret("cipher-new")},
                            "additionalSecretOutputs": ["token"],
                        },
                        {
                            "urn": created_urn,
                            "type": "aws:s3/bucket:Bucket",
                            "id": "new",
                            "inputs": {"bucket": "new"},
                            "outputs": {"arn": "arn:new-bucket"},
                        },
                    ],
                }
            },
        }
        self.fake.add(
            ".pulumi/history/pulumi-app/dev/dev-2.history.json",
            {
                "version": 0,
                "kind": "update",
                "result": "succeeded",
                "message": "second",
                "environment": {"PULUMI_CONFIG_PASSPHRASE": "do-not-leak"},
                "resourceChanges": {"create": 1, "update": 1, "delete": 1},
            },
        )
        self.fake.add(".pulumi/history/pulumi-app/dev/dev-2.checkpoint.json", after)
        self.fake.add(
            ".pulumi/history/pulumi-app/dev/dev-1.history.json",
            {"version": 0, "kind": "update", "result": "succeeded", "message": "first"},
        )
        self.fake.add(".pulumi/history/pulumi-app/dev/dev-1.checkpoint.json", before)
        clear_cache()

        listing = self.client.get(
            "/api/pulumi/backends/homelab/projects/pulumi-app/stacks/dev/updates/"
        )
        self.assertEqual(listing.status_code, 200)
        ids = [row["id"] for row in listing.json()["updates"]]
        self.assertIn("dev-2.history.json", ids)
        self.assertNotIn("dev-2.checkpoint.json", ids)
        listed = listing.content.decode()
        self.assertNotIn("do-not-leak", listed)
        self.assertNotIn("cipher-new", listed)

        response = self.client.get(
            "/api/pulumi/backends/homelab/projects/pulumi-app/stacks/dev/updates/diff/",
            {"id": "dev-2.history.json"},
        )
        self.assertEqual(response.status_code, 200)
        body = response.content.decode()
        self.assertNotIn("cipher-old", body)
        self.assertNotIn("cipher-new", body)
        self.assertNotIn("do-not-leak", body)
        self.assertNotIn("do-not-leak-salt", body)
        changes = {row["urn"]: row for row in response.json()["changes"]}
        self.assertEqual(changes[created_urn]["op"], "create")
        self.assertEqual(changes[deleted_urn]["op"], "delete")
        self.assertEqual(changes[BUCKET_URN]["op"], "update")
        self.assertNotIn(STACK_URN, changes)
        self.assertNotIn("token", [row["key"] for row in changes[BUCKET_URN]["outputs"]])
        arn = next(row for row in changes[BUCKET_URN]["outputs"] if row["key"] == "arn")
        self.assertEqual(arn, {"key": "arn", "op": "replace", "before": "arn:old", "after": "arn:new"})
        tags = next(row for row in changes[BUCKET_URN]["inputs"] if row["key"] == "tags")
        self.assertEqual(tags, {"key": "tags", "op": "add", "after": {"env": "prod"}})
        missing = self.client.get(
            "/api/pulumi/backends/homelab/projects/pulumi-app/stacks/dev/updates/diff/",
            {"id": "missing.history.json"},
        )
        self.assertEqual(missing.status_code, 404)
        bad = self.client.get(
            "/api/pulumi/backends/homelab/projects/pulumi-app/stacks/dev/updates/diff/",
            {"id": "../secret.json"},
        )
        self.assertEqual(bad.status_code, 400)

    def test_unchanged_object_uses_etag(self):
        url = "/api/pulumi/backends/homelab/projects/pulumi-app/stacks/dev/"
        first = self.client.get(url)
        self.assertEqual(first.status_code, 200)
        reads = self.fake.reads
        self.assertGreater(reads, 0)
        second = self.client.get(url)
        self.assertEqual(second.status_code, 200)
        self.assertEqual(self.fake.reads, reads)
        self.assertEqual(second.json()["outputs"]["url"], "https://example")

    def test_unknown_backend_and_bad_names(self):
        missing = self.client.get("/api/pulumi/backends/other/projects/")
        self.assertEqual(missing.status_code, 404)
        traversal = self.client.get("/api/pulumi/backends/%2e%2e/projects/")
        self.assertEqual(traversal.status_code, 400)
        missing_stack = self.client.get(
            "/api/pulumi/backends/homelab/projects/pulumi-app/stacks/missing/"
        )
        self.assertEqual(missing_stack.status_code, 404)
        missing_urn = self.client.get(
            "/api/pulumi/backends/homelab/projects/pulumi-app/stacks/dev/resources/detail/"
        )
        self.assertEqual(missing_urn.status_code, 400)


@override_settings(PULUMI_STATE_BACKENDS="{")
class InvalidConfigTests(TestCase):
    def setUp(self):
        user = get_user_model().objects.create_user("op", password="secret")
        self.client = APIClient()
        self.client.force_authenticate(user)

    def test_invalid_json_does_not_echo_the_setting(self):
        response = self.client.get("/api/pulumi/backends/")
        self.assertEqual(response.status_code, 500)
        self.assertEqual(response.json()["error"], "PULUMI_STATE_BACKENDS is not valid JSON")


@override_settings(
    PULUMI_STATE_BACKENDS="",
    PULUMI_BACKEND_NAME="homelab",
    RUSTFS_BUCKET="pulumi-state",
    RUSTFS_PREFIX="",
    RUSTFS_ENDPOINT_URL="http://rustfs:9000",
    RUSTFS_REGION="us-east-1",
    RUSTFS_ADDRESSING_STYLE="path",
    AWS_ACCESS_KEY_ID="from-vault-ak",
    AWS_SECRET_ACCESS_KEY="from-vault-sk",
)
class RustfsEnvBackendTests(TestCase):
    def setUp(self):
        user = get_user_model().objects.create_user("op", password="secret")
        self.client = APIClient()
        self.client.force_authenticate(user)

    def test_backends_from_rustfs_env(self):
        response = self.client.get("/api/pulumi/backends/")
        self.assertEqual(response.status_code, 200)
        self.assertEqual(
            response.json(),
            {"backends": [{"name": "homelab", "bucket": "pulumi-state", "prefix": ""}]},
        )
        # credentials must not leak into the public listing
        body = json.dumps(response.json())
        self.assertNotIn("from-vault-ak", body)
        self.assertNotIn("from-vault-sk", body)
