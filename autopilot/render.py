#!/usr/bin/env python3
"""把一份 canonical 草稿渲染成两边的文章文件。

canonical 草稿（autopilot/drafts/YYYY-MM-DD.md）只写一次，格式和 Hexo 那边一致：

    ---
    title: "标题"
    tags:
      - "React"
    categories: "随笔"
    description: "一句话"
    series: ""            # 可选，系列名
    ---
    正文……

输出：
  myBlog/source/_posts/YYYY-MM-DD-<slug>.md     （Hexo 源码，也是真身）
  astro-blog/src/content/blog/YYYY-MM-DD-<slug>.md

用法: python3 render.py <draft.md> [--date 2026-11-16]
"""
from __future__ import annotations

import argparse
import re
import sys
from datetime import date as Date
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))

from common import clean_slug, load_config, parse_draft, pub_datetime, yaml_str

# 体裁到 Hexo 分类的映射，和原来那套保持一致
GENRE_CATEGORY = {
    "事故复盘": "踩坑",
    "流水账": "随笔",
    "问答": "随笔",
    "笔记片段": "随笔",
    "对比吐槽": "随笔",
    "源码走读": "随笔",
}


def build_meta(draft: dict, d: Date, cfg: dict) -> dict:
    title = draft["title"]
    slug = clean_slug(title)
    when = pub_datetime(d, slug, cfg)
    tags = draft.get("tags") or ["随笔"]
    genre = draft.get("genre") or ""
    category = draft.get("categories") or GENRE_CATEGORY.get(genre, "随笔")
    return {
        "title": title,
        "slug": slug,
        "when": when,
        "tags": tags,
        "category": category,
        "description": draft.get("description", ""),
        "series": draft.get("series", ""),
        "body": draft["body"],
    }


def render_hexo(meta: dict) -> str:
    """Hexo 的 date 不能加引号，否则 YAML 会当字符串，归档和排序都会错。"""
    lines = ["---"]
    lines.append(f"title: {yaml_str(meta['title'])}")
    lines.append(f"date: {meta['when']:%Y-%m-%d %H:%M:%S}")
    lines.append("tags:")
    for t in meta["tags"]:
        lines.append(f"  - {yaml_str(t)}")
    lines.append(f"categories: {yaml_str(meta['category'])}")
    if meta["description"]:
        lines.append(f"description: {yaml_str(meta['description'])}")
    lines.append("---")
    lines.append("")
    lines.append(meta["body"])
    lines.append("")
    return "\n".join(lines)


def render_astro(meta: dict) -> str:
    """AstroPaper 的 pubDatetime 必须带时区，否则会被 scheduledPostMargin 当未来稿。"""
    lines = ["---"]
    lines.append(f"title: {yaml_str(meta['title'])}")
    lines.append(f"pubDatetime: {meta['when'].isoformat(timespec='seconds')}")
    lines.append("tags:")
    for t in meta["tags"]:
        lines.append(f"  - {yaml_str(t)}")
    if meta["description"]:
        lines.append(f"description: {yaml_str(meta['description'])}")
    lines.append("draft: false")
    lines.append("---")
    lines.append("")
    lines.append(meta["body"])
    lines.append("")
    return "\n".join(lines)


def write_outputs(draft_path: Path, d: Date, cfg: dict) -> dict:
    draft = parse_draft(draft_path)
    meta = build_meta(draft, d, cfg)
    stem = f"{d.isoformat()}-{meta['slug']}"

    hexo_path = Path(cfg["paths"]["myBlog"]) / "source" / "_posts" / f"{stem}.md"
    astro_path = Path(cfg["paths"]["astro"]) / "src" / "content" / "blog" / f"{stem}.md"

    hexo_path.parent.mkdir(parents=True, exist_ok=True)
    astro_path.parent.mkdir(parents=True, exist_ok=True)
    hexo_path.write_text(render_hexo(meta), encoding="utf-8")
    astro_path.write_text(render_astro(meta), encoding="utf-8")

    return {
        "title": meta["title"],
        "slug": meta["slug"],
        "stem": stem,
        "pub_datetime": meta["when"].isoformat(timespec="seconds"),
        "hexo_path": str(hexo_path),
        "astro_path": str(astro_path),
    }


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("draft")
    ap.add_argument("--date", help="发布日期 YYYY-MM-DD，默认今天")
    args = ap.parse_args()

    cfg = load_config()
    d = Date.fromisoformat(args.date) if args.date else Date.today()
    info = write_outputs(Path(args.draft), d, cfg)
    for k, v in info.items():
        print(f"{k}: {v}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
