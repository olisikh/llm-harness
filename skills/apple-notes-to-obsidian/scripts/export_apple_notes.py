#!/usr/bin/env python3
"""Export Apple Notes into an Obsidian vault with safety triage."""

from __future__ import annotations

import argparse
import datetime as dt
import html
from html.parser import HTMLParser
import json
from pathlib import Path
import re
import subprocess
import sys
import tempfile
from typing import Iterable


DEFAULT_VAULT = Path("~/notes").expanduser()
REVIEW_ROUTE = Path("40 Reference/Apple Notes Import Review")

SENSITIVE_PATTERNS = {
    "credentials": re.compile(
        r"\b(password|passphrase|passwd|pwd|2fa|otp|backup code|recovery code|api key|access token|"
        r"secret key|private key|seed phrase|mnemonic|ssh-rsa|begin (rsa|open)? ?private key)\b",
        re.I,
    ),
    "identity": re.compile(
        r"\b(passport|bsn|ssn|social security|national id|identity card|driver'?s license|"
        r"residence permit|digid|burgerservicenummer)\b",
        re.I,
    ),
    "finance": re.compile(
        r"\b(iban|credit card|card number|bank account|tax return|payslip|pay slip|salary|"
        r"mortgage statement|loan agreement|insurance policy)\b",
        re.I,
    ),
    "health_or_legal": re.compile(
        r"\b(diagnosis|prescription|lab result|therapy|medical record|lawsuit|legal dispute|"
        r"confidential|secret|private and confidential)\b",
        re.I,
    ),
}

IGNORE_PATTERNS = [
    re.compile(r"\b(shopping list|groceries|grocery|packing list|todo|to do|errands?)\b", re.I),
    re.compile(r"\b(verification code|login code|sms code)\b", re.I),
]

ROUTES = [
    (
        Path("20 Learning/Algorithms"),
        "algorithm study",
        re.compile(r"\b(algorithm|leetcode|data structure|binary tree|graph|dynamic programming|dp|lca|bst)\b", re.I),
    ),
    (
        Path("20 Learning/Kubernetes"),
        "kubernetes learning",
        re.compile(r"\b(kubernetes|kubectl|k8s|helm|cka|kuberstronaut|operator|ingress|cluster)\b", re.I),
    ),
    (
        Path("20 Learning/Nix"),
        "nix learning",
        re.compile(r"\b(nix|nixos|nix-darwin|flake|derivation|home manager|overlay)\b", re.I),
    ),
    (
        Path("10 Work"),
        "work",
        re.compile(r"\b(job|interview|work|company|resume|cv|aws summit|meeting|standup|reflek|sebastian)\b", re.I),
    ),
    (
        Path("30 Personal/Netherlands"),
        "netherlands personal knowledge",
        re.compile(r"\b(netherlands|nederland|dutch|citizenship|gemeente|housing|buying a house|mortgage|ind)\b", re.I),
    ),
    (
        Path("20 Learning"),
        "learning",
        re.compile(r"\b(book|course|study|learn|research|lecture|notes|ddia|data-intensive)\b", re.I),
    ),
    (
        Path("40 Reference"),
        "reference",
        re.compile(r"\b(command|snippet|setup|config|checklist|template|plugin|tool|reference)\b", re.I),
    ),
    (
        Path("30 Personal"),
        "personal",
        re.compile(r"\b(personal|plan|routine|idea|home|family|travel)\b", re.I),
    ),
]


JXA_EXPORTER = r"""
const Notes = Application("Notes");

function safeString(value) {
  try {
    if (value === undefined || value === null) return "";
    return String(value);
  } catch (e) {
    return "";
  }
}

function safeDate(value) {
  try {
    if (value instanceof Date) return value.toISOString();
    return safeString(value);
  } catch (e) {
    return "";
  }
}

function collectFolder(accountName, folder, path, rows) {
  const folderName = safeString(folder.name());
  const currentPath = path.concat([folderName]);

  try {
    const notes = folder.notes();
    for (let i = 0; i < notes.length; i++) {
      const note = notes[i];
      rows.push({
        id: safeString(note.id()),
        account: accountName,
        folder_path: currentPath.join("/"),
        title: safeString(note.name()),
        body_html: safeString(note.body()),
        created: safeDate(note.creationDate()),
        modified: safeDate(note.modificationDate())
      });
    }
  } catch (e) {}

  try {
    const folders = folder.folders();
    for (let j = 0; j < folders.length; j++) {
      collectFolder(accountName, folders[j], currentPath, rows);
    }
  } catch (e) {}
}

const rows = [];
const accounts = Notes.accounts();
for (let a = 0; a < accounts.length; a++) {
  const account = accounts[a];
  const accountName = safeString(account.name());
  const folders = account.folders();
  for (let f = 0; f < folders.length; f++) {
    collectFolder(accountName, folders[f], [], rows);
  }
}
JSON.stringify(rows);
"""


class MarkdownHTMLParser(HTMLParser):
    def __init__(self) -> None:
        super().__init__()
        self.parts: list[str] = []
        self.link_stack: list[str] = []

    def handle_starttag(self, tag: str, attrs: list[tuple[str, str | None]]) -> None:
        attrs_dict = {key.lower(): value or "" for key, value in attrs}
        if tag in {"p", "div"}:
            self._newline()
        elif tag == "br":
            self.parts.append("\n")
        elif tag == "li":
            self._newline()
            self.parts.append("- ")
        elif tag in {"h1", "h2", "h3"}:
            self._newline()
            self.parts.append("#" * int(tag[1]) + " ")
        elif tag == "a":
            self.link_stack.append(attrs_dict.get("href", ""))

    def handle_endtag(self, tag: str) -> None:
        if tag in {"p", "div", "li", "h1", "h2", "h3"}:
            self._newline()
        elif tag == "a" and self.link_stack:
            href = self.link_stack.pop()
            if href:
                self.parts.append(f" ({href})")

    def handle_data(self, data: str) -> None:
        text = html.unescape(data)
        if text.strip():
            self.parts.append(re.sub(r"[ \t\r\f\v]+", " ", text))

    def _newline(self) -> None:
        if self.parts and not self.parts[-1].endswith("\n"):
            self.parts.append("\n")

    def markdown(self) -> str:
        text = "".join(self.parts)
        text = re.sub(r"\n{3,}", "\n\n", text)
        text = re.sub(r"[ \t]+\n", "\n", text)
        return text.strip()


def html_to_markdown(raw_html: str) -> str:
    parser = MarkdownHTMLParser()
    parser.feed(raw_html or "")
    return parser.markdown()


def run_jxa_export() -> list[dict[str, str]]:
    with tempfile.NamedTemporaryFile("w", suffix=".js", delete=False) as handle:
        handle.write(JXA_EXPORTER)
        script_path = handle.name
    try:
        result = subprocess.run(
            ["osascript", "-l", "JavaScript", script_path],
            check=False,
            capture_output=True,
            text=True,
        )
    finally:
        Path(script_path).unlink(missing_ok=True)

    if result.returncode != 0:
        message = result.stderr.strip() or result.stdout.strip()
        raise RuntimeError(
            "Apple Notes export failed. Grant the running terminal or host app Automation access to Notes. "
            f"osascript said: {message}"
        )

    try:
        data = json.loads(result.stdout)
    except json.JSONDecodeError as exc:
        raise RuntimeError(f"Apple Notes returned invalid JSON: {exc}") from exc
    if not isinstance(data, list):
        raise RuntimeError("Apple Notes export did not return a list.")
    return data


def existing_apple_ids(vault: Path) -> set[str]:
    ids: set[str] = set()
    if not vault.exists():
        return ids
    pattern = re.compile(r'^apple_note_id:\s*"?([^"\n]+)"?\s*$', re.M)
    for path in vault.rglob("*.md"):
        try:
            text = path.read_text(errors="ignore")
        except OSError:
            continue
        match = pattern.search(text)
        if match:
            ids.add(match.group(1).strip())
    return ids


def combined_text(note: dict[str, str], markdown: str) -> str:
    return "\n".join(
        [
            note.get("title", ""),
            note.get("folder_path", ""),
            note.get("account", ""),
            markdown,
        ]
    )


def classify(note: dict[str, str], markdown: str, seen_ids: set[str]) -> tuple[str, Path | None, str, list[str]]:
    note_id = note.get("id", "").strip()
    title = note.get("title", "").strip()
    text = combined_text(note, markdown)
    categories = [name for name, pattern in SENSITIVE_PATTERNS.items() if pattern.search(text)]
    if categories:
        return "sensitive", None, "sensitive: " + ", ".join(categories), categories
    if note_id and note_id in seen_ids:
        return "duplicate", None, "already imported", []
    if not markdown.strip() or len(markdown.strip()) < 20 or title.lower() in {"new note", "untitled"}:
        return "ignore", None, "empty or scratch note", []
    if any(pattern.search(text) for pattern in IGNORE_PATTERNS):
        return "ignore", None, "temporary list or login snippet", []
    for route, reason, pattern in ROUTES:
        if pattern.search(text):
            return "import", route, reason, []
    return "review", REVIEW_ROUTE, "low-confidence safe note", []


def slugify(title: str) -> str:
    cleaned = re.sub(r'[\\/:*?"<>|#\^\[\]\n\r\t]+', " ", title).strip()
    cleaned = re.sub(r"\s+", " ", cleaned)
    if not cleaned:
        cleaned = "Apple Note"
    return cleaned[:90].rstrip(". ")


def unique_path(directory: Path, title: str) -> Path:
    base = slugify(title)
    candidate = directory / f"{base}.md"
    counter = 2
    while candidate.exists():
        candidate = directory / f"{base} {counter}.md"
        counter += 1
    return candidate


def yaml_string(value: str) -> str:
    return json.dumps(value or "", ensure_ascii=False)


def render_markdown(note: dict[str, str], body: str, review: bool) -> str:
    tags = ["imported/apple-notes"]
    if review:
        tags.append("review/apple-notes")
    imported = dt.datetime.now(dt.timezone.utc).isoformat(timespec="seconds")
    tag_lines = "\n".join(f"  - {tag}" for tag in tags)
    frontmatter = "\n".join(
        [
            "---",
            "source: apple-notes",
            f"apple_note_id: {yaml_string(note.get('id', ''))}",
            f"apple_account: {yaml_string(note.get('account', ''))}",
            f"apple_folder: {yaml_string(note.get('folder_path', ''))}",
            f"created: {yaml_string(note.get('created', ''))}",
            f"modified: {yaml_string(note.get('modified', ''))}",
            f"imported: {yaml_string(imported)}",
            "tags:",
            tag_lines,
            "---",
            "",
        ]
    )
    title = note.get("title", "").strip() or "Apple Note"
    return f"{frontmatter}# {title}\n\n{body.strip()}\n"


def filter_notes(
    notes: Iterable[dict[str, str]], account: str | None, folder_contains: str | None
) -> list[dict[str, str]]:
    filtered: list[dict[str, str]] = []
    for note in notes:
        if account and account.lower() not in note.get("account", "").lower():
            continue
        if folder_contains and folder_contains.lower() not in note.get("folder_path", "").lower():
            continue
        filtered.append(note)
    return filtered


def write_report(report_path: Path, rows: list[dict[str, str]], write_enabled: bool) -> None:
    counts: dict[str, int] = {}
    for row in rows:
        counts[row["status"]] = counts.get(row["status"], 0) + 1
    lines = [
        "# Apple Notes Import Report",
        "",
        f"- Mode: {'write' if write_enabled else 'dry-run'}",
        f"- Generated: {dt.datetime.now(dt.timezone.utc).isoformat(timespec='seconds')}",
        "",
        "## Counts",
        "",
    ]
    for key in sorted(counts):
        lines.append(f"- {key}: {counts[key]}")
    lines.extend(["", "## Notes", ""])
    for row in rows:
        target = row.get("target") or "-"
        lines.append(f"- `{row['status']}` {row['title']} -> {target} ({row['reason']})")
        if row.get("folder"):
            lines.append(f"  - Apple folder: {row['folder']}")
    report_path.parent.mkdir(parents=True, exist_ok=True)
    report_path.write_text("\n".join(lines) + "\n")


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--vault", type=Path, default=DEFAULT_VAULT, help="Obsidian vault path. Default: ~/notes")
    parser.add_argument("--write", action="store_true", help="Write safe classified notes to the vault.")
    parser.add_argument("--report", type=Path, default=Path("/tmp/apple-notes-import-report.md"))
    parser.add_argument("--account", help="Only export accounts whose name contains this text.")
    parser.add_argument("--folder-contains", help="Only export Apple Notes folders whose path contains this text.")
    parser.add_argument("--limit", type=int, help="Limit notes after filtering, useful for testing.")
    return parser.parse_args()


def main() -> int:
    args = parse_args()
    vault = args.vault.expanduser().resolve()
    notes = run_jxa_export()
    filtered = filter_notes(notes, args.account, args.folder_contains)
    if args.limit is not None:
        filtered = filtered[: args.limit]

    seen_ids = existing_apple_ids(vault)
    report_rows: list[dict[str, str]] = []
    for note in filtered:
        markdown = html_to_markdown(note.get("body_html", ""))
        status, route, reason, _categories = classify(note, markdown, seen_ids)
        title = note.get("title", "").strip() or "Untitled"
        target = ""
        if status in {"import", "review"} and route is not None:
            directory = vault / route
            target_path = unique_path(directory, title)
            target = str(target_path.relative_to(vault))
            if args.write:
                directory.mkdir(parents=True, exist_ok=True)
                target_path.write_text(render_markdown(note, markdown, review=(status == "review")))
                if note.get("id"):
                    seen_ids.add(note["id"])
        report_rows.append(
            {
                "status": status,
                "title": title,
                "target": target,
                "reason": reason,
                "folder": note.get("folder_path", ""),
            }
        )

    write_report(args.report.expanduser(), report_rows, args.write)
    print(f"Notes scanned: {len(filtered)}")
    print(f"Report: {args.report.expanduser()}")
    if not args.write:
        print("Dry run only. Re-run with --write to import safe notes.")
    return 0


if __name__ == "__main__":
    try:
        raise SystemExit(main())
    except RuntimeError as exc:
        print(f"error: {exc}", file=sys.stderr)
        raise SystemExit(1)
