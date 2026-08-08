import re
from pathlib import Path


MARKDOWN_LINK_RE = re.compile(r"(?<!!)\[[^\]]+\]\(([^)]+)\)")


def test_readme_and_document_center_have_no_broken_local_links():
    markdown_files = [Path("README.md"), *Path("docs").rglob("*.md")]
    missing: list[str] = []

    for markdown_file in markdown_files:
        text = markdown_file.read_text(encoding="utf-8")
        for raw_target in MARKDOWN_LINK_RE.findall(text):
            target = raw_target.strip().split("#", 1)[0].strip().strip("<>")
            if not target or target.startswith(("http://", "https://", "mailto:")):
                continue
            resolved = (markdown_file.parent / target).resolve()
            if not resolved.exists():
                missing.append(f"{markdown_file}: {raw_target}")

    assert missing == []
