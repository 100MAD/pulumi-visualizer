from django.test import SimpleTestCase

from pulumi_state.redact import redact, redact_config, redact_properties

SIG = "4dabf18193072939515e22adb298388d"
SECRET = "1b47061264138c4ac30d75fd1eb44270"


def secret(ciphertext="v1:ciphertext"):
    return {SIG: SECRET, "ciphertext": ciphertext}


class RedactTests(SimpleTestCase):
    def test_secret_object_drops_ciphertext(self):
        self.assertEqual(redact(secret("v1:super-secret-ciphertext")), {"secret": True})

    def test_nested_secret_in_dict_and_list(self):
        value = {"name": "web", "tokens": [secret("v1:one"), {"ok": True}]}
        self.assertEqual(
            redact(value),
            {"name": "web", "tokens": [{"secret": True}, {"ok": True}]},
        )

    def test_output_wrapper_marked_secret_drops_plaintext(self):
        wrapped = {
            SIG: "d0e6a833031e9bbcd3f4e8bde6ca49a4",
            "secret": True,
            "value": "plaintext-should-not-leak",
        }
        self.assertEqual(redact(wrapped), {"secret": True})

    def test_output_wrapper_unwraps_and_still_redacts(self):
        wrapped = {
            SIG: "d0e6a833031e9bbcd3f4e8bde6ca49a4",
            "secret": False,
            "value": {"password": secret("v1:inner"), "name": "ok"},
        }
        self.assertEqual(redact(wrapped), {"password": {"secret": True}, "name": "ok"})

    def test_additional_secret_outputs_redact_plaintext(self):
        cleaned = redact_properties({"token": "plain-token-value", "arn": "arn:aws"}, ["token"])
        self.assertEqual(cleaned["token"], {"secret": True})
        self.assertEqual(cleaned["arn"], "arn:aws")
        self.assertNotIn("plain-token-value", str(cleaned))

    def test_config_secret_flag_and_plain_string(self):
        cleaned = redact_config(
            {
                "aws:region": {"string": "us-east-1"},
                "db:password": {"string": "v1:hidden-password", "secret": True},
                "plain": "kept",
            }
        )
        self.assertEqual(cleaned["aws:region"], {"value": "us-east-1", "secret": False})
        self.assertEqual(cleaned["db:password"], {"secret": True})
        self.assertEqual(cleaned["plain"], {"value": "kept", "secret": False})
        self.assertNotIn("hidden-password", str(cleaned))
