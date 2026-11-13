#!/usr/bin/env python3
"""一次性工具：把线上 gh-pages 里有、myBlog 源码里缺的老文章保真回填。
正文保留渲染后的 HTML（butterfly 的 article-container 内容），不做有损的 HTML->MD 转换。
用法: python3 scripts/backfill_hexo.py [--apply]  不带 --apply 只报告。"""
from __future__ import annotations

import html
import json
import re
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
from common import load_config, yaml_str

ARTICLE_OPEN = re.compile(r'<article[^>]*id="article-container"[^>]*>', re.I)
ARTICLE_TAG = re.compile(r"<(/?)article\b[^>]*>", re.I)


def extract_article(htm: str) -> str:
    m = ARTICLE_OPEN.search(htm)
    if not m:
        raise ValueError("找不到 article-container")
    depth, pos = 1, m.end()
    last = None
    while depth > 0:
        n = ARTICLE_TAG.search(htm, pos)
        if not n:
            break
        last = n
        depth += -1 if n.group(1) else 1
        pos = n.end()
    if depth != 0 or last is None:
        raise ValueError("article 标签未闭合")
    return htm[m.end() : last.start()].strip()


def first(pattern, htm: str, default: str = "") -> str:
    m = re.search(pattern, htm, re.S)
    return html.unescape(m.group(1).strip()) if m else default


def convert(page: Path) -> dict:
    htm = page.read_text(encoding="utf-8", errors="ignore")
    title = first(r'<h1 class="post-title">(.*?)</h1>', htm)
    pubdate = first(r'title="发表于\s*(\d{4}-\d{2}-\d{2}\s+\d{2}:\d{2}:\d{2})"', htm)
    if not pubdate:
        iso = first(r'<time datetime="([^"]+)"', htm)
        pubdate = iso.replace("T", " ").rstrip("Z")[:19] if iso else ""
    cat = first(r'<a class="post-meta-categories"[^>]*>(.*?)</a>', htm)
    tag_block_m = re.search(r'<div class="post-meta__tag-list">(.*?)</div>', htm, re.S)
    tag_block = tag_block_m.group(1) if tag_block_m else ""
    tags = [
        html.unescape(re.sub(r"<[^>]+>", "", t)).strip()
        for t in re.findall(r"<a[^>]*>(.*?)</a>", tag_block, re.S)
    ]
    tags = [t for t in tags if t][:6]
    body = extract_article(htm)
    return {"title": title, "date": pubdate, "category": cat, "tags": tags, "body": body}


def source_rel_from_page(page: Path, gh_pages: Path) -> str:
    rel = page.parent.relative_to(gh_pages).as_posix()  # 2022/06/09/ES6/ES6_14_async 函数
    bits = rel.split("/")
    if len(bits) < 4 or not re.fullmatch(r"\d{4}", bits[0]):
        raise ValueError(f"无法从路径推导源码位置: {rel}")
    return "/".join(bits[3:]) + ".md"


def build_markdown(meta: dict) -> str:
    lines = [
        "---",
        f"title: {yaml_str(meta['title'])}",
        f"date: {meta['date']}",
        "tags:",
    ]
    for t in meta["tags"]:
        lines.append(f"  - {yaml_str(t)}")
    if meta["category"]:
        lines.append(f"categories: {yaml_str(meta['category'])}")
    lines += ["---", "", meta["body"], ""]
    return "\n".join(lines)


def main() -> None:
    apply = "--apply" in sys.argv
    cfg = load_config()
    gh_pages = Path(cfg["paths"]["gh_pages"])
    myblog = Path(cfg["paths"]["myBlog"])
    posts = myblog / "source" / "_posts"
    pages = sorted(
        p
        for p in gh_pages.rglob("index.html")
        if ".git" not in p.relative_to(gh_pages).parts
        and len(p.relative_to(gh_pages).parts) >= 6
        and re.fullmatch(r"20\d{2}", p.relative_to(gh_pages).parts[0])
    )
    report = []
    for page in pages:
        rel = source_rel_from_page(page, gh_pages)
        target = posts / rel
        if target.exists():
            continue
        try:
            meta = convert(page)
        except Exception as exc:
            report.append({"page": page.as_posix(), "error": str(exc)})
            continue
        if not meta["title"] or not meta["date"]:
            report.append({"page": page.as_posix(), "error": "缺少标题或日期"})
            continue
        item = {
            "page": str(page.relative_to(gh_pages)),
            "source": f"source/_posts/{rel}",
            "title": meta["title"],
            "date": meta["date"],
            "body_chars": len(meta["body"]),
        }
        if apply:
            target.parent.mkdir(parents=True, exist_ok=True)
            target.write_text(build_markdown(meta), encoding="utf-8")
            item["written"] = True
        report.append(item)
    print(json.dumps({"apply": apply, "found": len(pages), "missing": len(report), "items": report}, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()
