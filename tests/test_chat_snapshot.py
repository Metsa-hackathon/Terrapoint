import base64
import copy
import json
import os
import unittest
from unittest.mock import patch

from fastapi.testclient import TestClient

from api import index as api


SNAPSHOT_KEY = base64.urlsafe_b64encode(b"k" * 32).decode()


def analysis_data():
    return {
        "kataster": {
            "number": "78404:409:0113",
            "pindala_ha": 21.65,
            "geometry": {"type": "Polygon", "coordinates": []},
        },
        "mets": {"eraldised": [{"eraldis_nr": 1}], "vanus": 81},
        "vaartus": {"base_value_eur": 350_000},
        "map_layers": {"kaitsealad": {"features": []}},
        "meta": {
            "partial": False,
            "unavailable_sources": [],
            "ai_analysis_available": True,
        },
        "spatial_status": {
            "natura_2000": {"intersects": False, "sources_complete": True},
            "kaitseala": {"intersects": False, "sources_complete": True},
            "sood": {"intersects": False, "sources_complete": True},
        },
    }


class ChatSnapshotTests(unittest.TestCase):
    def snapshot_env(self):
        return patch.dict(
            os.environ,
            {
                "TERRAPOINT_CHAT_SNAPSHOT_KEY_B64": SNAPSHOT_KEY,
                "OPENCODE_ZEN_API_KEY": "",
            },
            clear=False,
        )

    def test_snapshot_round_trip_authenticates_projected_search_data(self):
        data = analysis_data()

        with self.snapshot_env():
            token, expires_at = api._issue_chat_snapshot(data, now=1_000)
            payload = api._verify_chat_snapshot_for_data(
                token,
                data,
                "78404:409:0113",
                now=1_100,
            )

        self.assertEqual(expires_at, 2_800)
        self.assertEqual(payload["kataster_nr"], "78404:409:0113")
        self.assertEqual(payload["evidence_sha256"], api._chat_evidence_digest(data))
        self.assertNotIn("geometry", api._chat_data_projection(data)["kataster"])
        self.assertNotIn("map_layers", api._chat_data_projection(data))

    def test_vercel_requires_a_dedicated_snapshot_key(self):
        with patch.dict(
            os.environ,
            {
                "VERCEL": "1",
                "TERRAPOINT_CHAT_SNAPSHOT_KEY_B64": "",
                "OPENCODE_ZEN_API_KEY": "provider-secret-must-not-sign",
            },
            clear=False,
        ):
            self.assertIsNone(api._chat_snapshot_signing_key())

    def test_snapshot_rejects_modified_client_facts(self):
        data = analysis_data()
        modified = copy.deepcopy(data)
        modified["vaartus"]["base_value_eur"] = 999_999_999

        with self.snapshot_env():
            token, _ = api._issue_chat_snapshot(data, now=1_000)
            with self.assertRaises(api.ChatSnapshotError) as raised:
                api._verify_chat_snapshot_for_data(
                    token,
                    modified,
                    "78404:409:0113",
                    now=1_100,
                )

        self.assertEqual(raised.exception.code, "CHAT_SNAPSHOT_INVALID")

    def test_snapshot_rejects_tampering_expiry_and_wrong_parcel(self):
        data = analysis_data()

        with self.snapshot_env():
            token, _ = api._issue_chat_snapshot(data, now=1_000)
            with self.assertRaises(api.ChatSnapshotError) as tampered:
                api._verify_chat_snapshot_for_data(
                    token[:-1] + ("A" if token[-1] != "A" else "B"),
                    data,
                    "78404:409:0113",
                    now=1_100,
                )
            with self.assertRaises(api.ChatSnapshotError) as expired:
                api._verify_chat_snapshot_for_data(
                    token,
                    data,
                    "78404:409:0113",
                    now=2_801,
                )
            with self.assertRaises(api.ChatSnapshotError) as wrong_parcel:
                api._verify_chat_snapshot_for_data(
                    token,
                    data,
                    "17501:002:0490",
                    now=1_100,
                )

        self.assertEqual(tampered.exception.code, "CHAT_SNAPSHOT_INVALID")
        self.assertEqual(expired.exception.code, "CHAT_SNAPSHOT_EXPIRED")
        self.assertEqual(wrong_parcel.exception.code, "CHAT_SNAPSHOT_INVALID")

    def test_attaching_snapshot_does_not_mutate_cached_search_data(self):
        data = analysis_data()

        with self.snapshot_env():
            response_data = api._attach_chat_snapshot(data, now=1_000)

        self.assertNotIn("chat_snapshot", data)
        self.assertIn("chat_snapshot", response_data)
        self.assertEqual(response_data["chat_snapshot_expires_at"], 2_800)
        self.assertEqual(response_data["chat_snapshot_ttl_seconds"], api.CHAT_SNAPSHOT_TTL_SECONDS)
        self.assertNotIn("chat_snapshot_ttl_seconds", api._chat_data_projection(response_data))

    def test_prompt_copy_change_does_not_invalidate_signed_evidence(self):
        data = analysis_data()

        with self.snapshot_env():
            token, _ = api._issue_chat_snapshot(data, now=1_000)
            with patch("api.index.build_system_prompt", return_value="new prompt wording"):
                payload = api._verify_chat_snapshot_for_data(
                    token,
                    data,
                    "78404:409:0113",
                    now=1_100,
                )

        self.assertEqual(payload["kataster_nr"], "78404:409:0113")

    def test_browser_integral_number_serialization_keeps_snapshot_valid(self):
        data = analysis_data()
        data["mets"]["pindala_ha"] = 1.0
        browser_data = copy.deepcopy(data)
        browser_data["mets"]["pindala_ha"] = 1

        with self.snapshot_env():
            token, _ = api._issue_chat_snapshot(data, now=1_000)
            payload = api._verify_chat_snapshot_for_data(
                token,
                browser_data,
                "78404:409:0113",
                now=1_100,
            )

        self.assertEqual(payload["kataster_nr"], "78404:409:0113")

    def test_chat_rejects_forged_data_before_provider_configuration(self):
        data = analysis_data()
        modified = copy.deepcopy(data)
        modified["vaartus"]["base_value_eur"] = 999_999_999

        with self.snapshot_env():
            token, _ = api._issue_chat_snapshot(data, now=api.time.time())
            response = TestClient(api.app).post("/api/chat", json={
                "kataster_nr": "78404:409:0113",
                "message": "Analüüsi kinnistut",
                "snapshot": token,
                "data": modified,
            })

        self.assertEqual(response.status_code, 400)
        self.assertEqual(response.json()["code"], "CHAT_SNAPSHOT_INVALID")

    def test_old_browser_can_send_snapshot_nested_in_data_during_rollout(self):
        data = analysis_data()

        with self.snapshot_env():
            token, expires_at = api._issue_chat_snapshot(data)
            old_browser_data = copy.deepcopy(data)
            old_browser_data["chat_snapshot"] = token
            old_browser_data["chat_snapshot_expires_at"] = expires_at
            response = TestClient(api.app).post("/api/chat", json={
                "kataster_nr": "78404:409:0113",
                "message": "Analüüsi kinnistut",
                "data": old_browser_data,
            })

        self.assertEqual(response.status_code, 500)
        self.assertIn("AI teenus ei ole seadistatud", response.json()["error"])

    def test_pre_snapshot_browser_is_rejected_with_research_instruction(self):
        data = analysis_data()

        with self.snapshot_env():
            response = TestClient(api.app).post("/api/chat", json={
                "kataster_nr": "78404:409:0113",
                "message": "Analüüsi kinnistut",
                "data": data,
            })

        self.assertEqual(response.status_code, 400)
        self.assertEqual(response.json()["code"], "CHAT_SNAPSHOT_INVALID")
        self.assertIn("Otsi kinnistu uuesti", response.json()["error"])

    def test_chat_rejects_non_json_cross_site_request_before_snapshot_work(self):
        with self.snapshot_env():
            response = TestClient(api.app).post(
                "/api/chat",
                content=json.dumps({"kataster_nr": "78404:409:0113"}),
                headers={"Content-Type": "text/plain", "Origin": "https://evil.example"},
            )

        self.assertEqual(response.status_code, 415)
        self.assertEqual(response.json()["code"], "UNSUPPORTED_MEDIA_TYPE")

    def test_chat_rejects_non_ascii_snapshot_as_invalid_input(self):
        data = analysis_data()

        with self.snapshot_env():
            response = TestClient(api.app).post("/api/chat", json={
                "kataster_nr": "78404:409:0113",
                "message": "Analüüsi kinnistut",
                "snapshot": "tp1.kkkkkkkkkkkk.õ.invalid",
                "data": data,
            })

        self.assertEqual(response.status_code, 400)
        self.assertEqual(response.json()["code"], "CHAT_SNAPSHOT_INVALID")

    def test_vercel_proxy_replaces_upstream_snapshot_with_local_signature(self):
        data = analysis_data()
        data["chat_snapshot"] = "upstream-token"

        class UpstreamResponse:
            status_code = 200
            content = api.orjson.dumps(data)

        with self.snapshot_env():
            response = api._search_proxy_response(UpstreamResponse(), "78404:409:0113")
            body = api.orjson.loads(response.body)
            api._verify_chat_snapshot_for_data(
                body["chat_snapshot"],
                body,
                "78404:409:0113",
            )

        self.assertNotEqual(body["chat_snapshot"], "upstream-token")
        self.assertEqual(response.headers["cache-control"], "private, no-store")

    def test_vercel_proxy_rejects_upstream_parcel_mismatch(self):
        data = analysis_data()
        data["kataster"]["number"] = "17501:002:0490"

        class UpstreamResponse:
            status_code = 200
            content = api.orjson.dumps(data)

        with self.snapshot_env():
            response = api._search_proxy_response(UpstreamResponse(), "78404:409:0113")

        self.assertEqual(response.status_code, 502)
        self.assertEqual(api.orjson.loads(response.body)["code"], "UPSTREAM_SCHEMA")

    def test_vercel_proxy_rejects_whitespace_variant_parcel_number(self):
        data = analysis_data()
        data["kataster"]["number"] = " 78404:409:0113 "

        class UpstreamResponse:
            status_code = 200
            content = api.orjson.dumps(data)

        with self.snapshot_env():
            response = api._search_proxy_response(UpstreamResponse(), "78404:409:0113")

        self.assertEqual(response.status_code, 502)

    def test_vercel_proxy_does_not_sign_missing_canonical_spatial_status(self):
        data = analysis_data()
        data.pop("spatial_status")

        class UpstreamResponse:
            status_code = 200
            content = api.orjson.dumps(data)

        with self.snapshot_env():
            response = api._search_proxy_response(UpstreamResponse(), "78404:409:0113")
            body = api.orjson.loads(response.body)

        self.assertEqual(response.status_code, 200)
        self.assertNotIn("chat_snapshot", body)
        self.assertNotIn("chat_snapshot_expires_at", body)
        self.assertFalse(body["meta"]["ai_analysis_available"])

    def test_vercel_proxy_disables_ai_when_dedicated_key_is_missing(self):
        data = analysis_data()

        class UpstreamResponse:
            status_code = 200
            content = api.orjson.dumps(data)

        with patch.dict(
            os.environ,
            {
                "VERCEL": "1",
                "TERRAPOINT_CHAT_SNAPSHOT_KEY_B64": "",
                "OPENCODE_ZEN_API_KEY": "provider-secret-must-not-sign",
            },
            clear=False,
        ):
            response = api._search_proxy_response(UpstreamResponse(), "78404:409:0113")
            body = api.orjson.loads(response.body)

        self.assertEqual(response.status_code, 200)
        self.assertNotIn("chat_snapshot", body)
        self.assertFalse(body["meta"]["ai_analysis_available"])


if __name__ == "__main__":
    unittest.main()
