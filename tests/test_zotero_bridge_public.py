import unittest

from tools.zotero_bridge import (
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


if __name__ == "__main__":
    unittest.main()
