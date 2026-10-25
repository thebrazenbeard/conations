"""Read-only, deliberately non-authoritative exports of dated conation evidence.

This is a repository-index validator, not a desire detector or runtime bridge.
It cannot grant consent, tasks, permissions, or volition activation.
"""

from __future__ import annotations

import argparse
import hashlib
import json
import re
import sys
from datetime import date
from pathlib import Path


EVENT_KINDS = frozenset({"ADD", "REVISE", "CONTRADICT", "REVOKE", "COMPLETE", "REVIEW"})
EVENT_PATH = re.compile(r"^events/(?P<day>\d{4}-\d{2}-\d{2})/[a-z0-9][a-z0-9-]*\.md$")
INDEX_LINK = re.compile(
    r"(?<!!)\[[^\[\]\n]+\]\((?:\./)?"
    r"(?P<path>events/\d{4}-\d{2}-\d{2}/[a-z0-9][a-z0-9-]*\.md)\)"
)
FENCE_OPEN = re.compile(r"^[ ]{0,3}(?P<marks>`{3,}|~{3,})(?P<info>.*)$")
FENCE_CLOSE = re.compile(r"^[ ]{0,3}(?P<marks>`+|~+)[ \t]*$")
BLOCKQUOTE = re.compile(r"^[ ]{0,3}(?:[-+*][ \t]+)?>")
FIELDS = {"Observed/recorded", "Event", "Subject", "Current status"}


class ManifestError(ValueError):
    """The repository history cannot be faithfully indexed from this checkout."""


def _index_links(text: str) -> set[str]:
    """Recognize bounded Markdown links, never prose path mentions or code.

    This is intentionally narrower than CommonMark: the event index uses plain
    inline links and should not depend on a complex, ambiguous parser.
    """
    links: set[str] = set()
    fence_mark: str | None = None
    fence_size = 0
    in_comment = False
    inline_ticks = 0

    for line in text.splitlines():
        if fence_mark is not None:
            close = FENCE_CLOSE.fullmatch(line)
            if (close and close["marks"][0] == fence_mark
                    and len(close["marks"]) >= fence_size):
                fence_mark = None
                fence_size = 0
            continue
        if not in_comment and not inline_ticks:
            opener = FENCE_OPEN.fullmatch(line)
            if opener and (opener["marks"][0] != "`" or "`" not in opener["info"]):
                fence_mark = opener["marks"][0]
                fence_size = len(opener["marks"])
                continue
        skip_line = bool(BLOCKQUOTE.match(line)) or line.startswith(("    ", "\t"))
        if skip_line and not (in_comment or inline_ticks):
            continue

        # Preserve character offsets while masking HTML comments and code spans.
        visible = list(line)
        pos = 0
        while pos < len(line):
            if in_comment:
                end = line.find("-->", pos)
                stop = len(line) if end < 0 else end + 3
                visible[pos:stop] = " " * (stop - pos)
                pos = stop
                if end >= 0:
                    in_comment = False
                continue
            if inline_ticks:
                if line[pos] == "`":
                    stop = pos
                    while stop < len(line) and line[stop] == "`":
                        stop += 1
                    if stop - pos == inline_ticks:
                        inline_ticks = 0
                else:
                    stop = pos + 1
                visible[pos:stop] = " " * (stop - pos)
                pos = stop
                continue
            if line.startswith("<!--", pos):
                in_comment = True
                continue
            if line[pos] == "`":
                stop = pos
                while stop < len(line) and line[stop] == "`":
                    stop += 1
                inline_ticks = stop - pos
                visible[pos:stop] = " " * (stop - pos)
                pos = stop
                continue
            pos += 1
        if not skip_line:
            for match in INDEX_LINK.finditer("".join(visible)):
                links.add(match["path"])
    return links


def _read_regular(path: Path) -> tuple[str, bytes]:
    if path.is_symlink():
        raise ManifestError(f"symlink is not allowed: {path}")
    if not path.is_file():
        raise ManifestError(f"missing regular file: {path}")
    try:
        raw = path.read_bytes()
        return raw.decode("utf-8"), raw
    except UnicodeError as exc:
        raise ManifestError(f"invalid UTF-8: {path}") from exc


def _header_fields(text: str, path: str) -> dict[str, str]:
    fields: dict[str, str] = {}
    for line in text.splitlines():
        if line.startswith("## "):
            break
        if ":" not in line:
            continue
        key, value = line.split(":", 1)
        if key not in FIELDS:
            continue
        if key in fields:
            raise ManifestError(f"duplicate {key!r} in {path}")
        fields[key] = value.strip()
    missing = FIELDS - fields.keys()
    if missing or any(not fields[k] for k in FIELDS):
        raise ManifestError(f"missing required event fields in {path}: {sorted(missing)}")
    if not re.search(r"(?m)^## Provenance\s*$", text):
        raise ManifestError(f"missing provenance section in {path}")
    if fields["Event"] not in EVENT_KINDS:
        raise ManifestError(f"unsupported event type in {path}: {fields['Event']!r}")
    return fields


def build_manifest(root: Path, *, include_subject: bool = False) -> dict[str, object]:
    """Validate index coverage and return explicitly historical evidence metadata.

    Free-text subjects are omitted unless the caller asks for them. This does
    not establish that a subject is safe to export to any remote provider.
    """
    root = Path(root).resolve()
    event_root = root / "events"
    if event_root.is_symlink():
        raise ManifestError(f"symlink is not allowed: {event_root}")
    if not event_root.is_dir():
        raise ManifestError(f"missing event directory: {event_root}")
    for candidate in event_root.rglob("*"):
        if candidate.is_symlink():
            raise ManifestError(f"symlink is not allowed: {candidate}")
    index, _ = _read_regular(root / "EVENT_INDEX.md")
    links = _index_links(index)
    events: list[dict[str, str]] = []
    found: set[str] = set()
    for file in sorted(event_root.rglob("*.md")):
        path = file.relative_to(root).as_posix()
        match = EVENT_PATH.fullmatch(path)
        if match is None:
            raise ManifestError(f"unexpected event file path: {path}")
        try:
            date.fromisoformat(match["day"])
        except ValueError as exc:
            raise ManifestError(f"invalid event date: {path}") from exc
        content, raw = _read_regular(file)
        fields = _header_fields(content, path)
        if not fields["Observed/recorded"].startswith(match["day"]):
            raise ManifestError(f"event date disagrees with observed/recorded: {path}")
        entry = {
            "path": path,
            "event_date": match["day"],
            "event_type": fields["Event"],
            "recorded_status": fields["Current status"],
            "content_sha256": hashlib.sha256(raw).hexdigest(),
            "status_currentness": "historical_only",
        }
        if include_subject:
            entry["subject"] = fields["Subject"]
        events.append(entry)
        found.add(path)
    missing = found - links
    if missing:
        raise ManifestError(f"event not indexed: {sorted(missing)}")
    stale = links - found
    if stale:
        raise ManifestError(f"index links without event files: {sorted(stale)}")
    return {
        "schema": "conations.history.v1",
        "currentness": "history_only",
        "effect_authority": "none",
        "activation": "fresh_reappraisal_required",
        "events": events,
    }


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("action", choices=("check", "export"))
    parser.add_argument("--root", type=Path, default=Path(__file__).resolve().parent)
    parser.add_argument(
        "--include-subject", action="store_true",
        help="Explicitly include source subject text in an export (local stdout only).",
    )
    args = parser.parse_args(argv)
    if args.include_subject and args.action != "export":
        parser.error("--include-subject requires export")
    try:
        manifest = build_manifest(args.root, include_subject=args.include_subject)
    except ManifestError as exc:
        print(f"Conation history index INVALID: {exc}", file=sys.stderr)
        return 2
    if args.action == "check":
        print(f"Conation history index valid: {len(manifest['events'])} event(s); no currentness inferred")
    else:
        print(json.dumps(manifest, indent=2, ensure_ascii=False))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
