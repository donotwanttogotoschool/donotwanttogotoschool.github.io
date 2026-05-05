#!/usr/bin/env python3

from __future__ import annotations

import html
import re
from dataclasses import dataclass
from pathlib import Path
from typing import Iterable


ROOT = Path(__file__).resolve().parent
POSTS_DIR = ROOT / "posts"
INDEX_PATH = ROOT / "index.html"
START_MARKER = "        <!-- GENERATED_JOURNAL:START -->"
END_MARKER = "        <!-- GENERATED_JOURNAL:END -->"
REFERENCE_RE = re.compile(r'^\[([^\]]+)\]:\s*(\S+)(?:\s+"([^"]+)")?\s*$')


@dataclass
class Post:
    source_path: Path
    output_path: Path
    title: str
    display_title: str
    date_label: str
    sort_key: tuple[int, int, int, str]
    project: str
    tags: str
    summary: str
    body_html: str


def main() -> None:
    sources = sorted(
        path
        for path in ROOT.glob("*.md")
        if path.name.lower() != "readme.md"
    )

    posts = [parse_post(path) for path in sources]
    posts.sort(key=lambda post: post.sort_key, reverse=True)

    for post in posts:
        post.output_path.write_text(render_post_page(post), encoding="utf-8")

    update_index(posts)
    print(f"Published {len(posts)} markdown file(s).")


def parse_post(path: Path) -> Post:
    raw_lines = path.read_text(encoding="utf-8").replace("\ufeff", "").splitlines()
    references, content_lines = extract_references(raw_lines)

    title, body_lines = extract_title(content_lines, path.stem)
    metadata, body_lines = extract_metadata(body_lines)

    date_slug, date_label, sort_key = derive_date(path.stem, title, metadata.get("date", ""))
    output_name = f"{date_slug}.html" if date_slug else f"{path.stem}.html"
    output_path = POSTS_DIR / output_name

    display_title = metadata.get("title") or strip_date_prefix(title) or title
    project = metadata.get("project", "个人日志")
    tags = metadata.get("tags", "学习 / 记录")

    body_html, first_paragraph = render_body(body_lines, references)
    summary = metadata.get("summary") or first_paragraph or "一篇新的个人日志。"
    summary = truncate(collapse_spaces(strip_markdown(summary, references)), 110)

    return Post(
        source_path=path,
        output_path=output_path,
        title=title,
        display_title=display_title,
        date_label=date_label,
        sort_key=sort_key,
        project=project,
        tags=tags,
        summary=summary,
        body_html=body_html,
    )


def extract_references(lines: list[str]) -> tuple[dict[str, tuple[str, str]], list[str]]:
    references: dict[str, tuple[str, str]] = {}
    kept_lines: list[str] = []

    for line in lines:
        match = REFERENCE_RE.match(line.strip())
        if not match:
            kept_lines.append(line)
            continue

        ref_id, url, title = match.groups()
        references[ref_id.strip().lower()] = (url.strip(), title or "")

    return references, kept_lines


def extract_title(lines: list[str], fallback: str) -> tuple[str, list[str]]:
    for index, line in enumerate(lines):
        if line.strip().startswith("# "):
            return line.strip()[2:].strip(), lines[index + 1 :]

    return fallback, lines


def extract_metadata(lines: list[str]) -> tuple[dict[str, str], list[str]]:
    metadata: dict[str, str] = {}
    remaining = list(lines)

    while remaining and not remaining[0].strip():
        remaining.pop(0)

    while remaining:
        line = remaining[0].strip()
        if not line:
            remaining.pop(0)
            break

        parsed = parse_metadata_line(line)
        if not parsed:
            break

        key, value = parsed
        metadata[key] = value
        remaining.pop(0)

    return metadata, remaining


def parse_metadata_line(line: str) -> tuple[str, str] | None:
    match = re.match(r"^(Title|Project|Tags|Summary|Date|标题|项目|标签|摘要|日期)\s*[:：]\s*(.+)$", line)
    if not match:
        return None

    key_map = {
        "Title": "title",
        "标题": "title",
        "Project": "project",
        "项目": "project",
        "Tags": "tags",
        "标签": "tags",
        "Summary": "summary",
        "摘要": "summary",
        "Date": "date",
        "日期": "date",
    }
    raw_key, raw_value = match.groups()
    return key_map[raw_key], raw_value.strip()


def derive_date(stem: str, title: str, raw_date: str) -> tuple[str, str, tuple[int, int, int, str]]:
    for candidate in (raw_date, stem, title):
        if not candidate:
            continue

        match = re.search(r"(\d{4})[年./-](\d{1,2})[月./-](\d{1,2})", candidate)
        if match:
            year, month, day = (int(part) for part in match.groups())
            return (
                f"{year:04d}-{month:02d}-{day:02d}",
                f"{year:04d}.{month:02d}.{day:02d}",
                (year, month, day, stem),
            )

    return stem, "未标注", (0, 0, 0, stem)


def strip_date_prefix(title: str) -> str:
    stripped = re.sub(r"^\s*\d{4}[年./-]\d{1,2}[月./-]\d{1,2}(?:日)?\s*[：:]\s*", "", title)
    return stripped.strip()


def render_body(lines: list[str], references: dict[str, tuple[str, str]]) -> tuple[str, str]:
    sections = split_sections(lines)
    html_sections: list[str] = []
    first_paragraph = ""

    for heading, section_lines in sections:
        blocks_html, section_first_paragraph = render_blocks(section_lines, references)
        if not blocks_html:
            continue

        parts = ["        <section>"]
        if heading:
            parts.append(f"          <h2>{render_inline(heading, references)}</h2>")
        parts.extend(indent_lines(blocks_html.splitlines(), "          "))
        parts.append("        </section>")
        html_sections.append("\n".join(parts))

        if not first_paragraph and section_first_paragraph:
            first_paragraph = section_first_paragraph

    if not html_sections:
        html_sections.append(
            "        <section>\n"
            "          <p>这篇日志还没有正文内容。</p>\n"
            "        </section>"
        )

    return "\n".join(html_sections), first_paragraph


def split_sections(lines: list[str]) -> list[tuple[str | None, list[str]]]:
    sections: list[tuple[str | None, list[str]]] = []
    current_heading: str | None = None
    current_lines: list[str] = []

    for line in lines:
        stripped = line.strip()
        if stripped.startswith("## "):
            if current_heading or has_content(current_lines):
                sections.append((current_heading, current_lines))
            current_heading = stripped[3:].strip()
            current_lines = []
            continue

        current_lines.append(line)

    if current_heading or has_content(current_lines):
        sections.append((current_heading, current_lines))

    return sections


def has_content(lines: Iterable[str]) -> bool:
    return any(line.strip() for line in lines)


def render_blocks(lines: list[str], references: dict[str, tuple[str, str]]) -> tuple[str, str]:
    blocks: list[str] = []
    first_paragraph = ""
    index = 0

    while index < len(lines):
        stripped = lines[index].strip()
        if not stripped:
            index += 1
            continue

        if stripped.startswith("### "):
            blocks.append(f"<h3>{render_inline(stripped[4:].strip(), references)}</h3>")
            index += 1
            continue

        if is_table_start(lines, index):
            table_html, index = render_table(lines, index, references)
            blocks.append(table_html)
            continue

        if is_list_item(stripped):
            list_html, list_text, index = render_list(lines, index, references)
            blocks.append(list_html)
            if not first_paragraph and list_text:
                first_paragraph = list_text
            continue

        if stripped.startswith("> "):
            quote_html, quote_text, index = render_quote(lines, index, references)
            blocks.append(quote_html)
            if not first_paragraph and quote_text:
                first_paragraph = quote_text
            continue

        paragraph_html, paragraph_text, index = render_paragraph(lines, index, references)
        blocks.append(paragraph_html)
        if not first_paragraph and paragraph_text:
            first_paragraph = paragraph_text

    return "\n".join(blocks), first_paragraph


def is_table_start(lines: list[str], index: int) -> bool:
    if index + 1 >= len(lines):
        return False

    header = lines[index].strip()
    separator = lines[index + 1].strip()
    return (
        "|" in header
        and re.match(r"^\|?(?:\s*:?-+:?\s*\|)+\s*:?-+:?\s*\|?$", separator) is not None
    )


def render_table(
    lines: list[str], index: int, references: dict[str, tuple[str, str]]
) -> tuple[str, int]:
    table_lines: list[str] = []

    while index < len(lines):
        stripped = lines[index].strip()
        if not stripped or "|" not in stripped:
            break
        table_lines.append(stripped)
        index += 1

    headers = split_table_row(table_lines[0])
    rows = [split_table_row(line) for line in table_lines[2:]]

    parts = [
        '<div class="table-scroll">',
        "  <table>",
        "    <thead>",
        "      <tr>",
    ]
    parts.extend(
        f"        <th>{render_inline(header, references)}</th>" for header in headers
    )
    parts.extend(
        [
            "      </tr>",
            "    </thead>",
            "    <tbody>",
        ]
    )

    for row in rows:
        parts.append("      <tr>")
        for cell in row:
            parts.append(f"        <td>{render_inline(cell, references)}</td>")
        parts.append("      </tr>")

    parts.extend(
        [
            "    </tbody>",
            "  </table>",
            "</div>",
        ]
    )

    return "\n".join(parts), index


def split_table_row(row: str) -> list[str]:
    trimmed = row.strip().strip("|")
    return [cell.strip() for cell in trimmed.split("|")]


def is_list_item(line: str) -> bool:
    return bool(re.match(r"^(?:[-*]\s+|\d+\.\s+)", line))


def render_list(
    lines: list[str], index: int, references: dict[str, tuple[str, str]]
) -> tuple[str, str, int]:
    ordered = bool(re.match(r"^\d+\.\s+", lines[index].strip()))
    marker_re = re.compile(r"^\d+\.\s+" if ordered else r"^[-*]\s+")
    tag = "ol" if ordered else "ul"

    items_html: list[str] = []
    item_texts: list[str] = []

    while index < len(lines):
        stripped = lines[index].strip()
        if not stripped:
            index += 1
            break
        if not marker_re.match(stripped):
            break

        current = [marker_re.sub("", stripped, count=1).strip()]
        index += 1

        while index < len(lines):
            next_line = lines[index]
            next_stripped = next_line.strip()
            if not next_stripped:
                break
            if is_list_item(next_stripped) or next_stripped.startswith("### ") or is_table_start(lines, index):
                break
            current.append(next_stripped)
            index += 1

        item_html = join_inline_lines(current, references)
        items_html.append(f"  <li>{item_html}</li>")
        item_texts.append(collapse_spaces(strip_markdown(" ".join(current), references)))

    rendered = [f"<{tag}>", *items_html, f"</{tag}>"]
    return "\n".join(rendered), "；".join(item_texts[:2]), index


def render_quote(
    lines: list[str], index: int, references: dict[str, tuple[str, str]]
) -> tuple[str, str, int]:
    quote_lines: list[str] = []

    while index < len(lines):
        stripped = lines[index].strip()
        if not stripped.startswith("> "):
            break
        quote_lines.append(stripped[2:].strip())
        index += 1

    text = join_inline_lines(quote_lines, references)
    plain = collapse_spaces(strip_markdown(" ".join(quote_lines), references))
    return f"<blockquote><p>{text}</p></blockquote>", plain, index


def render_paragraph(
    lines: list[str], index: int, references: dict[str, tuple[str, str]]
) -> tuple[str, str, int]:
    paragraph_lines: list[str] = []

    while index < len(lines):
        stripped = lines[index].strip()
        if not stripped:
            break
        if stripped.startswith("### ") or is_list_item(stripped) or is_table_start(lines, index):
            break
        paragraph_lines.append(lines[index])
        index += 1

    html_text = join_inline_lines(paragraph_lines, references)
    plain_text = collapse_spaces(strip_markdown(" ".join(line.strip() for line in paragraph_lines), references))
    return f"<p>{html_text}</p>", plain_text, index


def join_inline_lines(lines: list[str], references: dict[str, tuple[str, str]]) -> str:
    parts: list[str] = []

    for index, raw_line in enumerate(lines):
        line = raw_line.rstrip()
        parts.append(render_inline(line.strip(), references))
        if index == len(lines) - 1:
            continue
        parts.append("<br>" if raw_line.endswith("  ") else " ")

    return "".join(parts)


def render_inline(text: str, references: dict[str, tuple[str, str]]) -> str:
    placeholders: dict[str, str] = {}

    def stash(fragment: str) -> str:
        key = f"@@PLACEHOLDER_{len(placeholders)}@@"
        placeholders[key] = fragment
        return key

    def link_fragment(label: str, url: str, title: str = "") -> str:
        attrs = [f'href="{html.escape(url, quote=True)}"']
        if title:
            attrs.append(f'title="{html.escape(title, quote=True)}"')
        return f"<a {' '.join(attrs)}>{html.escape(label)}</a>"

    text = re.sub(
        r"`([^`]+)`",
        lambda match: stash(f"<code>{html.escape(match.group(1))}</code>"),
        text,
    )
    text = re.sub(
        r"\[([^\]]+)\]\(([^)\s]+)(?:\s+\"([^\"]+)\")?\)",
        lambda match: stash(link_fragment(match.group(1), match.group(2), match.group(3) or "")),
        text,
    )
    text = re.sub(
        r"\[([^\]]+)\]\[([^\]]+)\]",
        lambda match: stash(resolve_reference_link(match.group(1), match.group(2), references)),
        text,
    )
    text = re.sub(
        r"\[([^\]]+)\]",
        lambda match: stash(resolve_short_reference(match.group(1), references)) if match.group(1).strip().lower() in references else match.group(0),
        text,
    )

    text = html.escape(text)
    text = re.sub(
        r"\*\*([^*]+)\*\*",
        lambda match: stash(f"<strong>{match.group(1)}</strong>"),
        text,
    )
    text = re.sub(
        r"(?<!\*)\*([^*]+)\*(?!\*)",
        lambda match: stash(f"<em>{match.group(1)}</em>"),
        text,
    )

    for key, value in placeholders.items():
        text = text.replace(key, value)

    return text


def resolve_reference_link(label: str, ref_id: str, references: dict[str, tuple[str, str]]) -> str:
    key = ref_id.strip().lower()
    if key not in references:
        return html.escape(f"{label} [{ref_id}]")

    url, title = references[key]
    attrs = [f'href="{html.escape(url, quote=True)}"']
    if title:
        attrs.append(f'title="{html.escape(title, quote=True)}"')
    return f"<a {' '.join(attrs)}>{html.escape(label)}</a>"


def resolve_short_reference(ref_id: str, references: dict[str, tuple[str, str]]) -> str:
    url, title = references[ref_id.strip().lower()]
    attrs = [f'href="{html.escape(url, quote=True)}"']
    if title:
        attrs.append(f'title="{html.escape(title, quote=True)}"')
    return f"<a {' '.join(attrs)}>[{html.escape(ref_id)}]</a>"


def strip_markdown(text: str, references: dict[str, tuple[str, str]]) -> str:
    text = re.sub(r"`([^`]+)`", r"\1", text)
    text = re.sub(r"\[([^\]]+)\]\(([^)]+)\)", r"\1", text)
    text = re.sub(r"\[([^\]]+)\]\[([^\]]+)\]", r"\1", text)
    text = re.sub(
        r"\[([^\]]+)\]",
        lambda match: match.group(1) if match.group(1).strip().lower() in references else match.group(0),
        text,
    )
    text = text.replace("**", "").replace("*", "")
    text = text.replace("|", " ")
    return html.unescape(text)


def collapse_spaces(text: str) -> str:
    return re.sub(r"\s+", " ", text).strip()


def truncate(text: str, limit: int) -> str:
    if len(text) <= limit:
        return text
    return text[: limit - 1].rstrip() + "…"


def render_post_page(post: Post) -> str:
    description = html.escape(post.summary, quote=True)
    title = html.escape(post.display_title, quote=True)
    project = html.escape(post.project)
    tags = html.escape(post.tags)

    return f"""<!doctype html>
<html lang="zh-CN">
<head>
  <meta charset="utf-8">
  <meta name="viewport" content="width=device-width, initial-scale=1">
  <title>{title} | Field Notes</title>
  <meta name="description" content="{description}">
  <link rel="stylesheet" href="../style.css">
  <script defer src="../script.js"></script>
</head>
<body data-page="post">
  <div class="reading-progress" aria-hidden="true"><span></span></div>
  <div class="page-noise" aria-hidden="true"></div>

  <main class="post-wrap">
    <a class="back-link" href="../index.html">← 返回首页</a>

    <article class="post-shell reveal">
      <header class="post-header">
        <div>
          <span class="post-kicker">自动生成 / {post.date_label}</span>
          <h1 class="post-title">{html.escape(post.display_title)}</h1>
          <p class="lead">{html.escape(post.summary)}</p>
        </div>
        <aside class="meta-card">
          <p><strong>日期</strong><br>{post.date_label}</p>
          <p><strong>项目</strong><br>{project}</p>
          <p><strong>标签</strong><br>{tags}</p>
        </aside>
      </header>

      <div class="post-body">
{post.body_html}
      </div>
    </article>
  </main>
</body>
</html>
"""


def update_index(posts: list[Post]) -> None:
    index_html = INDEX_PATH.read_text(encoding="utf-8")
    if START_MARKER not in index_html or END_MARKER not in index_html:
        raise RuntimeError("index.html 缺少 GENERATED_JOURNAL 标记，无法自动更新日志列表。")

    cards = "\n".join(render_card(post) for post in posts)
    block = f"{START_MARKER}\n{cards}\n{END_MARKER}"
    pattern = re.compile(re.escape(START_MARKER) + r".*?" + re.escape(END_MARKER), re.S)
    updated = pattern.sub(block, index_html, count=1)
    INDEX_PATH.write_text(updated, encoding="utf-8")


def render_card(post: Post) -> str:
    href = f"./posts/{post.output_path.name}"
    return "\n".join(
        [
            f'        <a class="journal-card" href="{href}">',
            f"          <span class=\"journal-date\">{post.date_label}</span>",
            f"          <h3>{html.escape(post.display_title)}</h3>",
            f"          <p>{html.escape(post.summary)}</p>",
            "        </a>",
        ]
    )


def indent_lines(lines: list[str], prefix: str) -> list[str]:
    return [f"{prefix}{line}" if line else "" for line in lines]


if __name__ == "__main__":
    main()
