import unittest
from unittest.mock import patch

from tools.zotero_bridge import (
    ZoteroClient,
    infer_review_status,
    replace_review_status_tags,
    review_status_tag,
)


class ZoteroBridgePublicTest(unittest.TestCase):
    def test_review_status_helpers_are_public_safe(self):
        self.assertEqual(review_status_tag("approved"), "rw/status/approved")
        self.assertEqual(infer_review_status({"human_review": "approved"}), "approved")
        tags = replace_review_status_tags([{"tag": "rw/status/candidate"}, {"tag": "topic/demo"}], "approved")
        self.assertEqual([item["tag"] for item in tags], ["topic/demo", "rw/status/approved"])

    def test_create_collection_failure_includes_failed_detail(self):
        class FakeResponse:
            def __enter__(self):
                return self

            def __exit__(self, exc_type, exc, tb):
                return False

            def read(self):
                return b'{"failed":{"0":{"message":"Duplicate collection"}}}'

        client = ZoteroClient(library_id="123", library_type="users", api_key="secret")

        with patch("urllib.request.urlopen", return_value=FakeResponse()):
            with self.assertRaisesRegex(ValueError, "Duplicate collection"):
                client.create_collection("Research_Pilot")

    def test_create_collection_rejects_successful_response_missing_key(self):
        class FakeResponse:
            def __enter__(self):
                return self

            def __exit__(self, exc_type, exc, tb):
                return False

            def read(self):
                return b'{"successful":{"0":{}}}'

        client = ZoteroClient(library_id="123", library_type="users", api_key="secret")

        with patch("urllib.request.urlopen", return_value=FakeResponse()):
            with self.assertRaisesRegex(ValueError, "Research_Pilot"):
                client.create_collection("Research_Pilot")


if __name__ == "__main__":
    unittest.main()
