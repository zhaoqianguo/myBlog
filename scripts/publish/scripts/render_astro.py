#!/usr/bin/env python3
"""canonical 草稿 -> AstroPaper 文章（src/content/blog/YYYY-MM-DD-slug.md）。
可独立 dry-run: python3 scripts/render_astro.py <draft.md> 2026-11-12 AM"""
from __future__ import annotations

import sys
from datetime import date
from pathlib import Path
from zoneinfo import ZoneInfo

sys.path.insert(0, str(Path(__file__).resolve().parent))
from common import clean_slug, load_config, parse_draft, pub_datetime, yaml_str


def render(draft: dict, d: date, window: str, cfg: dict) -> tuple[str, str]:
    slug = clean_slug(draft["title"])
    dt = pub_datetime(d, window, slug, cfg)
    # YAML 无时区时间戳按 UTC 解析；AstroPaper 的 postFilter 会把未来时间当定时文章隐藏。
    # 必须带上 config.timezone 的 offset，否则北京时间 09:00 会被当成 UTC 09:00（晚 8 小时才可见）。
    dt_iso = dt.replace(tzinfo=ZoneInfo(cfg.get("timezone", "Asia/Shanghai"))).isoformat(
        timespec="seconds"
    )
    lines = [
        "---",
        f"title: {yaml_str(draft['title'])}",
        f"pubDatetime: {dt_iso}",
        "tags:",
    ]
    for tag in draft["tags"]:
        lines.append(f"  - {yaml_str(tag)}")
    lines += [
        f"description: {yaml_str(draft['description'] or draft['title'])}",
        "draft: false",
        "---",
        "",
        draft["body"],
        "",
    ]
    rel = f"src/content/blog/{d.isoformat()}-{slug}.md"
    return rel, "\n".join(lines)


if __name__ == "__main__":
    if len(sys.argv) < 4:
        print("用法: render_astro.py <draft.md> <YYYY-MM-DD> <AM|PM>")
        sys.exit(2)
    draft = parse_draft(Path(sys.argv[1]))
    rel, text = render(draft, date.fromisoformat(sys.argv[2]), sys.argv[3], load_config())
    print(f"--- {rel} ---")
    print(text)
