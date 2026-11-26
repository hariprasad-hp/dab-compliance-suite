"""Unit tests for DAB operation validators, install payloads, and conformance cases."""

import json
import unittest

import dab_tester  # imported before conformance to initialize DAB_VERSION cleanly
import conformance
import dab.content
import dab.health_check
import dab.input
import dab.applications
import dab.operations
import dab.voice
from result_json import TestResult
from util.config_loader import build_incorrect_format_body, build_install_from_app_store_body
from util.enforcement_manager import EnforcementManager


def _make_result(topic, request="{}", response="{}"):
    return TestResult("TestId", "dev1", topic, request, "UNKNOWN", response, [])


class DabConformanceOperationsTests(unittest.TestCase):
    def setUp(self):
        em = EnforcementManager()
        em.supported_operations = set()
        em.supported_keys = set()

    def test_conformance_removes_readonly_screensaver_min_timeout_set(self):
        """Ensure read-only screenSaverMinTimeout is not targeted by system/settings/set."""
        set_payloads = [
            tc[1] for tc in conformance.CONFORMANCE_TEST_CASE
            if tc[0] == "system/settings/set" and isinstance(tc[1], str)
        ]
        self.assertFalse(any("screenSaverMinTimeout" in p for p in set_payloads))
        self.assertTrue(any('"screenSaverTimeout": 300' in p for p in set_payloads))

    def test_operations_health_keylist_and_content_validators(self):
        """Verify operations/list self-exclusion, healthy=True, key rules, and entryId cache."""
        self_op = '{"status": 200, "operations": ["operations/list", "device/info"]}'
        self.assertFalse(dab.operations.list(_make_result("operations/list", response=self_op), 20, 200))
        ok_op = '{"status": 200, "operations": ["device/info"]}'
        self.assertTrue(dab.operations.list(_make_result("operations/list", response=ok_op), 20, 200))

        unhealthy = '{"status": 200, "healthy": false, "message": "err"}'
        self.assertFalse(dab.health_check.get(_make_result("health-check/get", response=unhealthy), 20, 2000))
        healthy = '{"status": 200, "healthy": true}'
        self.assertTrue(dab.health_check.get(_make_result("health-check/get", response=healthy), 20, 2000))

        empty_key = '{"status": 200, "keyCodes": ["KEY_HOME", ""]}'
        self.assertFalse(dab.input.list(_make_result("input/key/list", response=empty_key), 20, 200))
        partner_keys = '{"status": 200, "keyCodes": ["KEY_HOME", "KEY_SUBTITLE", "KEY_CUSTOM_YOUTUBE"]}'
        res_keys = _make_result("input/key/list", response=partner_keys)
        self.assertTrue(dab.input.list(res_keys, 20, 200))
        self.assertTrue(any("[WARN]" in ln and "KEY_SUBTITLE" in ln for ln in res_keys.logs))

        search_resp = json.dumps({
            "status": 200,
            "entries": [{
                "entryId": "real-device-entry-42",
                "title": "Home",
                "appId": "YouTube",
                "poster": "data:image/png;base64,iVBORw0KGgo=",
                "categories": ["Movies"],
            }],
        })
        self.assertTrue(dab.content.search(_make_result("content/search", response=search_resp), 20, 200))
        self.assertEqual(dab.content.get_open_entry_id(), "real-device-entry-42")

        voice_disabled = '{"status": 200, "voiceSystems": [{"name": "GoogleAssistant", "enabled": false}]}'
        res_voice = _make_result("voice/list", response=voice_disabled)
        self.assertTrue(dab.voice.list(res_voice, 20, 200))
        self.assertTrue(any("enabled=false" in ln for ln in res_voice.logs))

        # Whitespace in appId, keyCode, voiceSystem.name, operation, or content appId MUST fail
        bad_app = '{"status": 200, "applications": [{"appId": "Prime Video", "friendlyName": "Prime Video"}]}'
        self.assertFalse(dab.applications.list(_make_result("applications/list", response=bad_app), 20, 250))
        good_app = '{"status": 200, "applications": [{"appId": "PrimeVideo", "friendlyName": "Prime Video"}]}'
        self.assertTrue(dab.applications.list(_make_result("applications/list", response=good_app), 20, 250))
        bad_key_ws = '{"status": 200, "keyCodes": ["KEY HOME"]}'
        self.assertFalse(dab.input.list(_make_result("input/key/list", response=bad_key_ws), 20, 200))
        bad_voice_ws = '{"status": 200, "voiceSystems": [{"name": "Google Assistant", "enabled": true}]}'
        self.assertFalse(dab.voice.list(_make_result("voice/list", response=bad_voice_ws), 20, 200))
        bad_op_ws = '{"status": 200, "operations": ["device/ info"]}'
        self.assertFalse(dab.operations.list(_make_result("operations/list", response=bad_op_ws), 20, 200))

    def test_negative_install_format_timeout_is_bounded(self):
        """Verify negative install format helper uses bounded seconds timeout."""
        payload = build_incorrect_format_body()
        self.assertEqual(payload["format"], "txt")
        self.assertEqual(payload["timeout"], 10)

    def test_valid_dab_topics_excludes_non_spec_setup_skip(self):
        """Ensure valid_dab_topics.json contains only official DAB 2.0/2.1 topics."""
        with open("valid_dab_topics.json", "r", encoding="utf-8") as f:
            topics = json.load(f)
        self.assertNotIn("system/setup/skip", topics)
        self.assertEqual(set(topics), set(dab.operations.DAB_21_OPERATIONS) | {"operations/list"})



if __name__ == "__main__":
    unittest.main()
