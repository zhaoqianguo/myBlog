#!/usr/bin/env python3
"""canonical 草稿 -> Hexo 源码文章（source/_posts/YYYY-MM-DD-slug.md）。
注意 date 不加引号：Hexo 用 YAML 时间戳解析。"""
from __future__ import annotations

import sys
from datetime import date
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
from common import clean_slug, load_config, parse_draft, pub_datetime, yaml_str


def render(draft: dict, d: date, window: str, cfg: dict) -> tuple[str, str]:
    slug = clean_slug(draft["title"])
    dt = pub_datetime(d, window, slug, cfg)
    lines = [
        "---",
        f"title: {yaml_str(draft['title'])}",
        f"date: {dt:%Y-%m-%d %H:%M:%S}",
        "tags:",
    ]
    for tag in draft["tags"]:
        lines.append(f"  - {yaml_str(tag)}")
    lines += [
        f"categories: {yaml_str('踩坑' if draft['genre'] == '事故复盘' else '随笔')}",
        f"description: {yaml_str(draft['description'] or draft['title'])}",
        "---",
        "",
        draft["body"],
        "",
    ]
    rel = f"source/_posts/{d.isoformat()}-{slug}.md"
    return rel, "\n".join(lines)


if __name__ == "__main__":
    if len(sys.argv) < 4:
        print("用法: render_hexo.py <draft.md> <YYYY-MM-DD> <AM|PM>")
        sys.exit(2)
    draft = parse_draft(Path(sys.argv[1]))
    rel, text = render(draft, date.fromisoformat(sys.argv[2]), sys.argv[3], load_config())
    print(f"--- {rel} ---")
    print(text)
