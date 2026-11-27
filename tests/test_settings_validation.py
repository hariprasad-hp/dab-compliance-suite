"""Unit tests for partner-safe DAB 2.0/2.1 system settings and schema validation."""

import json
import unittest
from unittest.mock import MagicMock

import dab_tester
import dab.system
from dab_checker import DabChecker
from result_json import TestResult
from util.enforcement_manager import EnforcementManager, ValidateCode


def _make_result(topic, request="{}", response="{}"):
    return TestResult("TestId", "dev1", topic, request, "UNKNOWN", response, [])


class DabSettingsValidationTests(unittest.TestCase):
    def setUp(self):
        em = EnforcementManager()
        em.supported_operations = set()
        em.supported_keys = set()
        em.supported_voice_assistants = set()
        em.supported_settings = None
        em.has_checked_settings = False
        dab_tester.DAB_VERSION = "2.0"

    def test_settings_list_partner_safe_omissions_custom_names_and_type_checks(self):
        """Allow omitted settings, 3P option names, and extra keys with warnings; fail bad types."""
        dab_tester.DAB_VERSION = "2.0"
        partial_20 = json.dumps({"status": 200, "language": ["en-US"], "pictureMode": ["Cinema", "Normal"]})
        res_20 = _make_result("system/settings/list", response=partial_20)
        self.assertTrue(dab.system.settings_list(res_20, 50, 200))
        self.assertTrue(any("omitted" in ln or "unsupported" in ln.lower() for ln in res_20.logs))
        self.assertTrue(any("[WARN]" in ln and "Cinema" in ln for ln in res_20.logs))

        dab_tester.DAB_VERSION = "2.1"
        partner_21_obj = {
            "status": 200,
            "language": ["en-US"],
            "audioOutputSource": ["HDMI", "SPDIF"],
            "timeZone": ["America/Los_Angeles", "UTC"],
            "screenSaver": True,
            "screenSaverMinTimeout": 30,
            "customPartnerSetting": True,
        }
        res_21 = _make_result("system/settings/list", response=json.dumps(partner_21_obj))
        self.assertTrue(dab.system.settings_list(res_21, 50, 200))
        self.assertTrue(any("customPartnerSetting" in ln for ln in res_21.logs))

        # Invalid data types or out-of-spec minTimeout (>60) still fail
        bad_21 = dict(partner_21_obj, screenSaverMinTimeout=120)
        self.assertFalse(dab.system.settings_list(_make_result("system/settings/list", response=json.dumps(bad_21)), 50, 200))
        bad_tz = dict(partner_21_obj, timeZone=True)
        self.assertFalse(dab.system.settings_list(_make_result("system/settings/list", response=json.dumps(bad_tz)), 50, 200))

    def test_settings_get_self_consistency_and_extra_key_warning(self):
        """Enforce self-consistency against settings/list while warning (not failing) on extra keys."""
        dab_tester.DAB_VERSION = "2.1"
        EnforcementManager().set_supported_settings({
            "status": 200,
            "language": ["en-US", "fr-FR"],
            "pictureMode": ["Cinema", "Vivid"],
            "brightness": {"min": 0, "max": 100},
            "screenSaver": True,
            "screenSaverMinTimeout": 10,
        })
        valid_get = {
            "status": 200,
            "language": "en-US",
            "pictureMode": "Cinema",
            "brightness": 50,
            "screenSaver": True,
            "screenSaverTimeout": 300,
            "screenSaverMinTimeout": 10,
        }
        res_ok = _make_result("system/settings/get", response=json.dumps(valid_get))
        self.assertTrue(dab.system.settings_get(res_ok, 50, 750))
        self.assertTrue(any("[WARN]" in ln and "screenSaverMinTimeout" in ln for ln in res_ok.logs))

        # Out-of-range brightness or value missing from device's own settings/list options must fail
        out_of_range = dict(valid_get, brightness=150)
        self.assertFalse(dab.system.settings_get(_make_result("system/settings/get", response=json.dumps(out_of_range)), 50, 750))
        unlisted_opt = dict(valid_get, pictureMode="Standard")
        self.assertFalse(dab.system.settings_get(_make_result("system/settings/get", response=json.dumps(unlisted_opt)), 50, 750))

    def test_settings_set_requires_echoed_key_and_screensaver_timeout_precheck(self):
        """Verify settings/set requires echoed key and derives screenSaverTimeout support."""
        self.assertFalse(
            dab.system.settings_set(
                _make_result("system/settings/set", request='{"mute": false}', response='{"status": 200}'),
                50,
                3000,
            )
        )
        self.assertFalse(
            dab.system.settings_set(
                _make_result("system/settings/set", request='{"mute": false}', response='{"status": 200, "mute": true}'),
                50,
                3000,
            )
        )
        self.assertTrue(
            dab.system.settings_set(
                _make_result("system/settings/set", request='{"mute": false}', response='{"status": 200, "mute": false}'),
                50,
                3000,
            )
        )

        EnforcementManager().set_supported_settings({
            "status": 200,
            "screenSaver": True,
            "screenSaverMinTimeout": 15,
            "audioVolume": {"min": 50, "max": 50},
        })
        dummy_tester = MagicMock()
        dummy_tester.execute_cmd = MagicMock(return_value=0)
        checker = DabChecker(dummy_tester)
        vc, _ = checker.precheck("dev1", "system/settings/set", '{"screenSaverTimeout": 300}')
        self.assertEqual(vc, ValidateCode.SUPPORT)
        vc_fixed_vol, _ = checker.precheck("dev1", "system/settings/set", '{"audioVolume": 50}')
        self.assertEqual(vc_fixed_vol, ValidateCode.UNSUPPORT)


if __name__ == "__main__":
    unittest.main()
