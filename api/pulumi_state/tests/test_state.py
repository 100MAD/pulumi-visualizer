from django.test import SimpleTestCase

from pulumi_state.state import (
    deployment_from_checkpoint,
    project_names,
    resource_count,
    sort_history_keys,
    stack_names,
    summarize_history,
    validate_segment,
    BadName,
)

STACK = {
    "urn": "urn:pulumi:dev::pulumi-app::pulumi:pulumi:Stack::dev",
    "type": "pulumi:pulumi:Stack",
    "outputs": {"url": "https://example"},
}
BUCKET = {
    "urn": "urn:pulumi:dev::pulumi-app::aws:s3/bucket:Bucket::data",
    "type": "aws:s3/bucket:Bucket",
}


class CheckpointShapeTests(SimpleTestCase):
    def test_nested_checkpoint(self):
        deployment = deployment_from_checkpoint(
            {"version": 3, "checkpoint": {"stack": "dev", "latest": {"resources": [STACK, BUCKET]}}}
        )
        self.assertEqual(resource_count(deployment), 1)

    def test_flat_checkpoint(self):
        deployment = deployment_from_checkpoint(
            {"version": 3, "stack": "dev", "latest": {"resources": [STACK]}}
        )
        self.assertEqual(resource_count(deployment), 0)

    def test_deployment_export(self):
        deployment = deployment_from_checkpoint(
            {"version": 3, "deployment": {"resources": [STACK, BUCKET]}}
        )
        self.assertEqual(resource_count(deployment), 1)

    def test_history_summary_drops_environment_and_deployment(self):
        summary = summarize_history(
            {
                "version": 4,
                "kind": "destroy",
                "result": "succeeded",
                "message": "cleanup",
                "startTime": 1759700000,
                "endTime": 1759700300,
                "environment": {"PULUMI_CONFIG_PASSPHRASE": "do-not-leak"},
                "deployment": {"resources": [STACK]},
                "resourceChanges": {"delete": 1},
            },
            4,
        )
        self.assertEqual(summary["version"], 4)
        self.assertEqual(summary["kind"], "destroy")
        self.assertEqual(summary["resource_changes"], {"delete": 1})
        self.assertNotIn("environment", summary)
        self.assertNotIn("deployment", summary)
        self.assertNotIn("do-not-leak", str(summary))
        self.assertTrue(summary["end_time"].startswith("2025-") or "T" in summary["end_time"])

    def test_history_versions_sort_descending(self):
        keys = sort_history_keys(
            [
                ".pulumi/history/app/dev/2.json",
                ".pulumi/history/app/dev/10.json",
                ".pulumi/history/app/dev/notes.txt",
            ]
        )
        self.assertEqual(
            keys,
            [
                ".pulumi/history/app/dev/10.json",
                ".pulumi/history/app/dev/2.json",
            ],
        )

    def test_project_and_stack_names_unescape(self):
        projects = project_names(".pulumi/stacks/", [".pulumi/stacks/my%20app/"])
        self.assertEqual(projects, ["my app"])
        stacks = stack_names(".pulumi/stacks/my%20app/", [".pulumi/stacks/my%20app/dev.json"])
        self.assertEqual(stacks, ["dev"])

    def test_rejects_traversal(self):
        for value in ("..", ".", "a/b", "a\\b", "", " pad"):
            with self.assertRaises(BadName):
                validate_segment(value)
