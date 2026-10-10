from django.test import SimpleTestCase

from pulumi_state.diff import diff_deployments

USER_URN = "urn:pulumi:dev::app::authentik:index/user:User::ada"
GROUP_URN = "urn:pulumi:dev::app::authentik:index/group:Group::readers"


def _user():
    return {
        "urn": USER_URN,
        "type": "authentik:index/user:User",
        "id": "207",
        "inputs": {"name": "Ada Lovelace", "username": "ada"},
        "outputs": {"name": "Ada Lovelace", "userId": "207", "username": "ada"},
    }


def _group(users):
    return {
        "urn": GROUP_URN,
        "type": "authentik:index/group:Group",
        "id": "10",
        "inputs": {"name": "readers", "users": users},
        "outputs": {"name": "readers", "users": users},
    }


class DiffDeploymentTests(SimpleTestCase):
    def test_group_user_ids_render_as_display_names(self):
        changes = diff_deployments(
            {"resources": [_user(), _group(["207"])]},
            {"resources": [_user(), _group([])]},
        )
        group = next(row for row in changes if row["urn"] == GROUP_URN)
        users = next(row for row in group["inputs"] if row["key"] == "users")
        self.assertEqual(users["before"], ["Ada Lovelace"])
        self.assertEqual(users["after"], [])

    def test_unrelated_id_lists_stay_numeric(self):
        bucket = "urn:pulumi:dev::app::aws:s3/bucket:Bucket::data"
        changes = diff_deployments(
            {"resources": [{"urn": bucket, "type": "aws:s3/bucket:Bucket", "inputs": {"ports": [207]}}]},
            {"resources": [{"urn": bucket, "type": "aws:s3/bucket:Bucket", "inputs": {"ports": [208]}}]},
        )
        ports = next(row for row in changes[0]["inputs"] if row["key"] == "ports")
        self.assertEqual(ports["before"], [207])
        self.assertEqual(ports["after"], [208])
