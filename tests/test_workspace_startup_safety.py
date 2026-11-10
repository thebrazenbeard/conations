"""Source-only guard against concealed editor startup execution."""

import json
from pathlib import Path
import re
import unittest

ROOT = Path(__file__).resolve().parents[1]


def read_workspace_json(path):
    source = path.read_text(encoding="utf-8-sig")
    return json.loads(re.sub(r",\s*(?=[}\]])", "", source))


def task_variants(task):
    yield task
    for platform in ("windows", "linux", "osx"):
        override = task.get(platform)
        if isinstance(override, dict):
            yield override


class WorkspaceStartupSafetyTests(unittest.TestCase):
    def test_no_folder_open_tasks(self):
        config = read_workspace_json(ROOT / ".vscode" / "tasks.json")
        for task in config.get("tasks", []):
            for variant in task_variants(task):
                self.assertNotEqual(
                    variant.get("runOptions", {}).get("runOn"),
                    "folderOpen",
                    "tracked workspace tasks must not run on folder open",
                )
                command = str(variant.get("command", ""))
                args = variant.get("args", [])
                combined = " ".join([command, *map(str, args if isinstance(args, list) else [args])])
                if re.search(r"(?i)\b(node|python|pwsh|powershell|cmd)\b", combined):
                    self.assertNotRegex(combined, r"(?i)\.(ttf|otf|woff2?)\b")

    def test_workspace_does_not_enable_automatic_tasks(self):
        settings = read_workspace_json(ROOT / ".vscode" / "settings.json")
        self.assertEqual(settings.get("task.allowAutomaticTasks"), "off")
        self.assertNotIn("tasks", settings, "no embedded startup tasks")

    def test_disguised_executable_not_tracked(self):
        self.assertFalse(
            (ROOT / "public" / "fonts" / "fa-solid-600.ttf").exists(),
            "disguised executable must not be present in checkout",
        )
        signatures = {
            ".ttf": (b"\x00\x01\x00\x00", b"true", b"ttcf"),
            ".otf": (b"OTTO",), ".woff": (b"wOFF",), ".woff2": (b"wOF2",),
        }
        for asset in (ROOT / "public" / "fonts").rglob("*"):
            if asset.is_file() and asset.suffix.lower() in signatures:
                self.assertIn(asset.read_bytes()[:4], signatures[asset.suffix.lower()], str(asset))

    def test_platform_override_and_bom_examples(self):
        sample = {"command": "echo safe", "windows": {"runOptions": {"runOn": "folderOpen"}}}
        self.assertTrue(any(x.get("runOptions", {}).get("runOn") == "folderOpen"
                            for x in task_variants(sample)))
        self.assertEqual(json.loads(b'\xef\xbb\xbf{"tasks":[]}'.decode("utf-8-sig")), {"tasks": []})


if __name__ == "__main__":
    unittest.main()
