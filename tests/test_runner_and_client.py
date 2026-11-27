"""Unit tests for MQTTv5 client, Stage-1 device_info, status checks, and clean JSON."""

import json
import tempfile
import unittest
from pathlib import Path
from unittest.mock import MagicMock, patch

import dab_tester
import dab.input
from dab_client import DabClient
from result_json import TestResult
from util.enforcement_manager import EnforcementManager


class DabRunnerAndClientTests(unittest.TestCase):
    def setUp(self):
        em = EnforcementManager()
        em.supported_operations = set()
        em.supported_keys = set()
        dab_tester.DAB_VERSION = "2.0"
        dab_tester._INTERACTIVE_ACK_ENABLED = False
        dab_tester._SESSION_ITEM_ACKS.clear()

    def test_detect_dab_version_and_stage1_device_info_capture(self):
        """Verify DAB version array parsing AND Stage-1 device_info capture before tests run."""
        with patch("dab_tester.DabClient") as mock_client_cls:
            client = MagicMock()
            client.last_error_code.return_value = 200
            client.response.side_effect = [
                json.dumps({"status": 200, "versions": ["2.0", "2.1"]}),
                json.dumps({"status": 200, "manufacturer": "skyworth", "model": "gambit", "deviceId": "gambit-5716"}),
            ]
            mock_client_cls.return_value = client
            tester = dab_tester.DabTester("localhost")
            tester.detect_dab_version("gambit-5716")
            info = tester._capture_initial_device_info("gambit-5716")
            self.assertEqual(tester.dab_version, "2.1")
            self.assertEqual(info["manufacturer"], "skyworth")
            self.assertEqual(tester.device_info["deviceId"], "gambit-5716")

    def test_status_code_validation_and_request_space_rejection(self):
        """Verify strict status validation (200/400/500/501 + required error) and appId space check."""
        with patch("dab_tester.DabClient") as mock_client_cls:
            client = MagicMock()
            mock_client_cls.return_value = client
            tester = dab_tester.DabTester("localhost", override_dab_version="2.1")
            tester._preflight_before_each_test_or_raise = MagicMock()
            tester.return_to_home_after_test = MagicMock()
            EnforcementManager().add_supported_operations(["input/key-press", "applications/get-state"])

            neg_case = ("input/key-press", '{"keyCode": "invalid"}', dab.input.key_press, 1000, "BadKey", "2.0", True)
            pos_case = ("input/key-press", '{"keyCode": "KEY_HOME"}', dab.input.key_press, 1000, "Home", "2.0", False)
            EnforcementManager().add_supported_keys(["KEY_HOME"])

            # String status "200" or unknown status 201 must FAIL
            client.last_error_code.return_value = -2
            client.response.return_value = '{"status": "200"}'
            self.assertEqual(tester.Execute("dev1", pos_case).test_result, "FAILED")
            client.last_error_code.return_value = 201
            client.response.return_value = '{"status": 201}'
            self.assertEqual(tester.Execute("dev1", pos_case).test_result, "FAILED")

            # 400/500/501 without non-empty 'error' string must FAIL per DAB §4.2
            client.last_error_code.return_value = 400
            client.response.return_value = '{"status": 400}'
            self.assertEqual(tester.Execute("dev1", neg_case).test_result, "FAILED")
            client.last_error_code.return_value = 500
            client.response.return_value = '{"status": 500}'
            self.assertEqual(tester.Execute("dev1", pos_case).test_result, "FAILED")

            # Valid 400 with error string passes negative test and logs latency
            client.last_error_code.return_value = 400
            client.response.return_value = '{"status": 400, "error": "Unsupported keyCode"}'
            res_400_ok = tester.Execute("dev1", neg_case)
            self.assertEqual(res_400_ok.test_result, "PASS")
            self.assertTrue(any("input/key-press Latency, Expected: 1000 ms" in ln for ln in res_400_ok.logs))

            bad_appid_case = ("applications/get-state", '{"appId": "Prime Video"}', dab.input.key_press, 200, "SpaceAppId", "2.0", False)
            self.assertEqual(tester.Execute("dev1", bad_appid_case).test_result, "FAILED")

    def test_clean_ack_map_no_duplicate_status_in_outcome_and_oversized_omission(self):
        """Verify flat operation_not_supported_ack map, no duplicate status in outcome, and >4KB omission."""
        with tempfile.TemporaryDirectory() as tmpdir:
            out_json = str(Path(tmpdir) / "conformance.json")
            small_resp = json.dumps({"status": 200, "keyCodes": ["KEY_HOME", "KEY_BACK"]})
            tr_small = TestResult(
                "InputKeyListConformance",
                "gambit-5716",
                "input/key/list",
                '{"id": "req1"}',
                "FAILED",
                small_resp,
                [
                    "input/key/list Latency, Expected: 200 ms, Actual: 245 ms",
                    "input/key/list took more time than expected.",
                    "[FAILED] Non-compliant key entry",
                ],
            )
            tr_small.test_result = "FAILED"

            langs = [f"en-{i:03d}" for i in range(600)]
            large_resp = json.dumps({"status": 200, "language": langs, "memc": False})
            tr_large = TestResult(
                "SystemSettingsListConformance",
                "gambit-5716",
                "system/settings/list",
                "{}",
                "PASS",
                large_resp,
                ["system/settings/list Latency, Expected: 200 ms, Actual: 95 ms"],
            )
            tr_large.test_result = "PASS"
            dab_tester._format_response_for_logs(tr_large, "system/settings/list", json.loads(large_resp))

            with patch.dict("os.environ", {"DAB_FORCE_INTERACTIVE": "1", "DAB_NON_INTERACTIVE": "0"}), patch(
                "builtins.input",
                side_effect=["60Hz panel without MEMC hardware"],
            ):
                dab_tester.AcknowledgeUnsupported(tr_large, "system/settings/list", ["memc (false)"])

            with patch("dab_tester.DabClient"):
                tester = dab_tester.DabTester("localhost", override_dab_version="2.1")
                tester.device_info = {"manufacturer": "skyworth", "deviceId": "gambit-5716"}
                tester.write_test_result_json("conformance", [tr_small, tr_large], out_json)

            written = json.loads(Path(out_json).read_text(encoding="utf-8"))
            self.assertEqual(written["device_info"]["manufacturer"], "skyworth")
            self.assertEqual(
                written["operation_not_supported_ack"],
                {"system/settings/list": {"memc": "60Hz panel without MEMC hardware"}},
            )
            e_small = written["test_result_list"][0]
            self.assertNotIn("status", e_small["outcome"])
            self.assertEqual(e_small["outcome"]["latency"], {"expected_ms": 200, "actual_ms": 245, "passed": False})
            self.assertIn("Latency 245 ms exceeded expected 200 ms", e_small["outcome"]["reason"])

            e_large = written["test_result_list"][1]
            self.assertTrue(e_large["response"]["omitted"])
            self.assertIn("language[600]", e_large["response"]["reason"])

    def test_dab_client_multichunk_logs_and_metrics_lock_safety(self):
        """Verify multi-chunk log collection holds lock until remainingChunks=0 and metrics stays safe."""
        with patch("dab_client.mqtt.Client") as mock_mqtt_cls:
            mock_mqtt = MagicMock()
            mock_mqtt_cls.return_value = mock_mqtt
            dc = DabClient()

            msg_chunk1 = MagicMock()
            msg_chunk1.payload = json.dumps({"status": 200, "remainingChunks": 1, "logArchive": "YWI="}).encode()
            dc._DabClient__on_message(mock_mqtt, None, msg_chunk1)
            self.assertTrue(dc._DabClient__lock.locked())

            msg_chunk2 = MagicMock()
            msg_chunk2.payload = json.dumps({"status": 200, "remainingChunks": 0, "logArchive": "Y2Q="}).encode()
            dc._DabClient__on_message(mock_mqtt, None, msg_chunk2)
            self.assertFalse(dc._DabClient__lock.locked())
            self.assertIsNotNone(dc.get_response_chunk())
            self.assertIsNotNone(dc.get_response_chunk())

            dc._DabClient__metrics_count = 10
            metric_msg = MagicMock()
            metric_msg.payload = b'{"cpu": 10}'
            dc._DabClient__on_message_metrics(mock_mqtt, None, metric_msg)
            dc._DabClient__on_message_metrics(mock_mqtt, None, metric_msg)
            self.assertTrue(dc.last_metrics_state())


if __name__ == "__main__":
    unittest.main()
