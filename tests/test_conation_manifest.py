"""Read-only conation evidence export must not become volition authority."""

import json
import hashlib
import tempfile
import unittest
from pathlib import Path

from conation_manifest import ManifestError, build_manifest


class ConationManifestTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        self.root = Path(self.temp.name)
        self.folder = self.root / "events" / "2026-09-04"
        self.folder.mkdir(parents=True)
        self.event = self.folder / "test-direction.md"
        self.event.write_text(
            "# Experimental direction\n\n"
            "Observed/recorded: 2026-09-04\n"
            "Event: ADD\n"
            "Subject: Private exploratory direction\n"
            "Current status: PRESENT / EXPLORATORY\n\n"
            "## Provenance\n\n2026-09-04 conversation\n",
            encoding="utf-8",
        )
        self.index = self.root / "EVENT_INDEX.md"
        self.index.write_text(
            "# Index\n[one](./events/2026-09-04/test-direction.md)\n",
            encoding="utf-8",
        )

    def test_manifest_defaults_to_history_only_and_no_sensitive_free_text(self):
        result = build_manifest(self.root)
        self.assertEqual("conations.history.v1", result["schema"])
        self.assertEqual("history_only", result["currentness"])
        self.assertEqual("none", result["effect_authority"])
        self.assertEqual("fresh_reappraisal_required", result["activation"])
        self.assertEqual(1, len(result["events"]))
        event = result["events"][0]
        self.assertEqual("ADD", event["event_type"])
        self.assertEqual("PRESENT / EXPLORATORY", event["recorded_status"])
        self.assertEqual("historical_only", event["status_currentness"])
        self.assertEqual(64, len(event["content_sha256"]))
        self.assertNotIn("subject", event)
        self.assertNotIn("magnitude", event)
        self.assertNotIn("confidence", event)
        self.assertNotIn("drive_kind", event)
        self.assertNotIn("consent", event)
        self.assertNotIn("Private exploratory direction", json.dumps(result))

    def test_sensitive_subject_requires_explicit_opt_in(self):
        result = build_manifest(self.root, include_subject=True)
        self.assertEqual("Private exploratory direction", result["events"][0]["subject"])
        self.assertEqual("history_only", result["currentness"])

    def test_digest_binds_original_crlf_bytes_not_normalized_text(self):
        raw = self.event.read_bytes().replace(b"\n", b"\r\n")
        self.event.write_bytes(raw)
        result = build_manifest(self.root)
        self.assertEqual(
            hashlib.sha256(raw).hexdigest(), result["events"][0]["content_sha256"]
        )

    def test_unindexed_event_fails_closed(self):
        self.index.write_text("# Index\n", encoding="utf-8")
        with self.assertRaisesRegex(ManifestError, "not indexed"):
            build_manifest(self.root)

    def test_bogus_index_link_fails_closed(self):
        self.index.write_text(
            "[bad](./events/2026-09-04/not-here.md)\n",
            encoding="utf-8",
        )
        with self.assertRaises(ManifestError):
            build_manifest(self.root)

    def test_fenced_only_path_is_not_an_index_link(self):
        self.index.write_text(
            "# Index\n```text\n(events/2026-09-04/test-direction.md)\n```\n",
            encoding="utf-8",
        )
        with self.assertRaisesRegex(ManifestError, "not indexed"):
            build_manifest(self.root)

    def test_fenced_markdown_link_is_not_index_membership(self):
        self.index.write_text(
            "~~~markdown\n[example](./events/2026-09-04/test-direction.md)\n~~~\n",
            encoding="utf-8",
        )
        with self.assertRaisesRegex(ManifestError, "not indexed"):
            build_manifest(self.root)

    def test_inline_code_and_html_comment_links_do_not_count(self):
        self.index.write_text(
            "`[example](./events/2026-09-04/test-direction.md)`\n"
            "<!-- [fake](./events/2026-09-04/test-direction.md) -->\n"
            "<!--\n[hidden](./events/2026-09-04/test-direction.md)\n-->\n",
            encoding="utf-8",
        )
        with self.assertRaisesRegex(ManifestError, "not indexed"):
            build_manifest(self.root)

    def test_real_markdown_link_is_counted_while_code_examples_are_ignored(self):
        self.index.write_text(
            "```markdown\n[fake](./events/2026-09-04/missing.md)\n```\n"
            "[actual](./events/2026-09-04/test-direction.md)\n",
            encoding="utf-8",
        )
        result = build_manifest(self.root)
        self.assertEqual(1, len(result["events"]))

    def test_image_or_blockquote_does_not_count_as_index(self):
        self.index.write_text(
            "![image](./events/2026-09-04/test-direction.md)\n"
            "> [quoted](./events/2026-09-04/test-direction.md)\n",
            encoding="utf-8",
        )
        with self.assertRaisesRegex(ManifestError, "not indexed"):
            build_manifest(self.root)

    def test_header_duplication_rejected(self):
        original = self.event.read_text(encoding="utf-8")
        self.event.write_text(original.replace("Event: ADD", "Event: ADD\nEvent: REVOKE"), encoding="utf-8")
        with self.assertRaisesRegex(ManifestError, "duplicate"):
            build_manifest(self.root)

    def test_unrecognized_lifecycle_kind_rejected(self):
        original = self.event.read_text(encoding="utf-8")
        self.event.write_text(original.replace("Event: ADD", "Event: EXECUTE"), encoding="utf-8")
        with self.assertRaisesRegex(ManifestError, "event type"):
            build_manifest(self.root)

    def test_symlink_event_cannot_hash_outside_repository(self):
        outer = self.root / "outside.md"
        outer.write_text("hidden content", encoding="utf-8")
        self.event.unlink()
        self.event.symlink_to(outer)
        with self.assertRaisesRegex(ManifestError, "symlink"):
            build_manifest(self.root)

    def test_symlink_directory_does_not_silently_omit_external_events(self):
        other = self.root / "other-events"
        other.mkdir()
        (self.root / "events" / "2026-09-05").symlink_to(other, target_is_directory=True)
        with self.assertRaisesRegex(ManifestError, "symlink"):
            build_manifest(self.root)


if __name__ == "__main__":
    unittest.main()
