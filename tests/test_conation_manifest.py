"""Read-only conation evidence export must not become volition authority."""

import json
import hashlib
import io
from contextlib import redirect_stderr, redirect_stdout
import tempfile
import unittest
from pathlib import Path

from conation_manifest import ManifestError, build_manifest, main


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
        self.assertNotIn("recorded_status", event)
        self.assertEqual("historical_only", event["status_currentness"])
        self.assertEqual(64, len(event["content_sha256"]))
        self.assertNotIn("subject", event)
        self.assertNotIn("path", event)
        self.assertNotIn("magnitude", event)
        self.assertNotIn("confidence", event)
        self.assertNotIn("drive_kind", event)
        self.assertNotIn("consent", event)
        self.assertNotIn("Private exploratory direction", json.dumps(result))
        self.assertNotIn("PRESENT / EXPLORATORY", json.dumps(result))

    def test_sensitive_subject_requires_explicit_opt_in(self):
        result = build_manifest(self.root, include_subject=True)
        self.assertEqual("Private exploratory direction", result["events"][0]["subject"])
        self.assertEqual("history_only", result["currentness"])

    def test_path_is_independently_opted_in(self):
        path_only = build_manifest(self.root, include_path=True)["events"][0]
        self.assertEqual("events/2026-09-04/test-direction.md", path_only["path"])
        self.assertNotIn("subject", path_only)
        self.assertNotIn("recorded_status", path_only)
        subject_only = build_manifest(self.root, include_subject=True)["events"][0]
        self.assertNotIn("path", subject_only)

    def test_invalid_private_field_does_not_leak_via_path_opt_in_errors(self):
        private_value = "PERSONAL-FIELD-VALUE-NOT-AUTHORIZED"
        private_path = "private-relationship-direction.md"
        self.event.rename(self.folder / private_path)
        self.index.write_text(
            f"[event](./events/2026-09-04/{private_path})\n", encoding="utf-8"
        )
        path = self.folder / private_path
        path.write_text(
            path.read_text(encoding="utf-8").replace("Event: ADD", f"Event: {private_value}"),
            encoding="utf-8",
        )
        with self.assertRaisesRegex(ManifestError, "event type") as captured:
            build_manifest(self.root, include_path=True)
        self.assertNotIn(private_path, str(captured.exception))
        self.assertNotIn(private_value, str(captured.exception))
        self.assertIsNone(captured.exception.__cause__)
        self.assertIsNone(captured.exception.__context__)
        err = io.StringIO()
        with redirect_stderr(err):
            code = main(["export", "--root", str(self.root), "--include-path"])
        self.assertEqual(2, code)
        self.assertNotIn(private_path, err.getvalue())
        self.assertNotIn(private_value, err.getvalue())
        self.assertIn("event type", err.getvalue())
        with self.assertRaisesRegex(ManifestError, private_value):
            build_manifest(self.root, include_path=True, include_diagnostics=True)
        detail = io.StringIO()
        with redirect_stderr(detail):
            self.assertEqual(2, main([
                "export", "--root", str(self.root), "--include-diagnostics"
            ]))
        self.assertIn(private_value, detail.getvalue())

    def test_default_unindexed_path_error_is_redacted(self):
        private_name = "confidential-partner-decision.md"
        self.event.rename(self.folder / private_name)
        self.index.write_text("# No event link\n", encoding="utf-8")
        with self.assertRaisesRegex(ManifestError, "not indexed") as captured:
            build_manifest(self.root)
        self.assertNotIn(private_name, str(captured.exception))
        self.assertIsNone(captured.exception.__context__)
        self.assertIsNone(captured.exception.__cause__)

    def test_root_symlink_loop_does_not_leak_private_path(self):
        loop = self.root / "private-relationship-direction-loop"
        loop.symlink_to(loop)
        with self.assertRaises(ManifestError) as captured:
            build_manifest(loop)
        # Python 3.12 raises RuntimeError from resolve() for this loop, while
        # 3.13 can resolve non-strictly and later reject the missing directory.
        # Both must disclose exactly one fixed, private-data-free category.
        self.assertIn(
            str(captured.exception),
            {"repository root resolution failed", "missing event directory"},
        )
        self.assertNotIn(loop.name, str(captured.exception))
        self.assertIsNone(captured.exception.__cause__)
        self.assertIsNone(captured.exception.__context__)
        err = io.StringIO()
        with redirect_stderr(err):
            self.assertEqual(2, main(["export", "--root", str(loop)]))
        self.assertNotIn(loop.name, err.getvalue())

    def test_cli_export_options_do_not_cross_authorize_other_fields(self):
        stdout = io.StringIO()
        with redirect_stdout(stdout):
            self.assertEqual(0, main(["export", "--root", str(self.root), "--include-path"]))
        entry = json.loads(stdout.getvalue())["events"][0]
        self.assertIn("path", entry)
        self.assertNotIn("subject", entry)
        self.assertNotIn("recorded_status", entry)

    def test_local_check_keeps_detailed_diagnostics_separate_from_export(self):
        private_value = "SENSITIVE-CHECK-ONLY-FIELD"
        self.event.write_text(
            self.event.read_text(encoding="utf-8").replace("Event: ADD", f"Event: {private_value}"),
            encoding="utf-8",
        )
        checked = io.StringIO()
        with redirect_stderr(checked):
            self.assertEqual(2, main(["check", "--root", str(self.root)]))
        self.assertIn(private_value, checked.getvalue())
        projected = io.StringIO()
        with redirect_stderr(projected):
            self.assertEqual(2, main(["export", "--root", str(self.root), "--include-path"]))
        self.assertNotIn(private_value, projected.getvalue())
        self.assertIn("unsupported event type", projected.getvalue())

    def test_recorded_status_requires_explicit_opt_in(self):
        result = build_manifest(self.root, include_status=True)
        self.assertEqual("PRESENT / EXPLORATORY", result["events"][0]["recorded_status"])

    def test_cli_export_opt_in_applies_to_status_and_subject(self):
        output = io.StringIO()
        with redirect_stdout(output):
            self.assertEqual(0, main(["export", "--root", str(self.root)]))
        default = json.loads(output.getvalue())["events"][0]
        self.assertNotIn("recorded_status", default)
        self.assertNotIn("subject", default)

        output = io.StringIO()
        with redirect_stdout(output):
            self.assertEqual(0, main([
                "export", "--root", str(self.root), "--include-subject", "--include-status"
            ]))
        opted = json.loads(output.getvalue())["events"][0]
        self.assertEqual("Private exploratory direction", opted["subject"])
        self.assertEqual("PRESENT / EXPLORATORY", opted["recorded_status"])

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
        with self.assertRaisesRegex(ManifestError, "raw HTML"):
            build_manifest(self.root)

    def test_escaped_markdown_link_is_not_index_membership(self):
        self.index.write_text(
            "\\[literal](./events/2026-09-04/test-direction.md)\n",
            encoding="utf-8",
        )
        with self.assertRaisesRegex(ManifestError, "not indexed"):
            build_manifest(self.root)

    def test_html_pre_code_blocks_are_not_index_membership(self):
        self.index.write_text(
            "<pre>\n[pre](./events/2026-09-04/test-direction.md)\n</pre>\n"
            "<code>\n[code](./events/2026-09-04/test-direction.md)\n</code>\n",
            encoding="utf-8",
        )
        with self.assertRaisesRegex(ManifestError, "raw HTML"):
            build_manifest(self.root)

    def test_html_raw_and_embedded_content_never_counts_as_index_membership(self):
        for opening, closing in (
            ("<textarea>", "</textarea>"),
            ("<TeXtArEa disabled>", "</TeXtArEa>"),
            ("<xmp>", "</xmp>"),
            ("<iframe src='about:blank'>", "</iframe>"),
            ("<noembed>", "</noembed>"),
            ("<noframes>", "</noframes>"),
        ):
            with self.subTest(tag=opening):
                self.index.write_text(
                    f"{opening}\n[masked](./events/2026-09-04/test-direction.md)\n"
                    f"{closing}\n",
                    encoding="utf-8",
                )
                with self.assertRaisesRegex(ManifestError, "raw HTML"):
                    build_manifest(self.root)

    def test_html_raw_content_cannot_be_combined_with_real_index_links(self):
        self.index.write_text(
            "<textarea>\n[masked](./events/2026-09-04/missing.md)\n</textarea>\n"
            "[actual](./events/2026-09-04/test-direction.md)\n",
            encoding="utf-8",
        )
        with self.assertRaisesRegex(ManifestError, "raw HTML"):
            build_manifest(self.root)

    def test_generic_html_blocks_do_not_create_index_membership(self):
        for opening, closing in (
            ("<div>", "</div>"),
            ("<section class='content'>", "</section>"),
            ("<article>", "</article>"),
            ("<custom-box>", "</custom-box>"),
        ):
            with self.subTest(tag=opening):
                self.index.write_text(
                    f"{opening}\n[masked](./events/2026-09-04/test-direction.md)\n"
                    f"{closing}\n",
                    encoding="utf-8",
                )
                with self.assertRaisesRegex(ManifestError, "raw HTML"):
                    build_manifest(self.root)

    def test_unterminated_plaintext_block_hides_remaining_index_lines(self):
        self.index.write_text(
            "<plaintext>\n[masked](./events/2026-09-04/test-direction.md)\n",
            encoding="utf-8",
        )
        with self.assertRaisesRegex(ManifestError, "raw HTML"):
            build_manifest(self.root)

    def test_html_example_in_fence_info_does_not_hide_later_real_link(self):
        self.index.write_text(
            "~~~html <textarea>\n"
            "[masked](./events/2026-09-04/missing.md)\n~~~\n"
            "[actual](./events/2026-09-04/test-direction.md)\n",
            encoding="utf-8",
        )
        self.assertEqual(1, len(build_manifest(self.root)["events"]))

    def test_escaped_backticks_do_not_hide_later_real_link(self):
        self.index.write_text(
            "\\`not executable syntax\\`\n"
            "[actual](./events/2026-09-04/test-direction.md)\n",
            encoding="utf-8",
        )
        self.assertEqual(1, len(build_manifest(self.root)["events"]))

    def test_only_standalone_link_line_counts(self):
        self.index.write_text(
            "See [inline](./events/2026-09-04/test-direction.md) in this prose.\n",
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

    def test_existing_index_style_code_formatted_label_is_still_a_real_link(self):
        self.index.write_text(
            "[`events/2026-09-04/test-direction.md`]"
            "(./events/2026-09-04/test-direction.md)\n",
            encoding="utf-8",
        )
        self.assertEqual(1, len(build_manifest(self.root)["events"]))

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
