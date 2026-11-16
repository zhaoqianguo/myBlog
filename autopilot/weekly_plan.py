#!/usr/bin/env python3
"""周计划工具。

    python3 weekly_plan.py --check              # 下一周的计划齐了没（每周日跑）
    python3 weekly_plan.py --template 2026-W48  # 打一份空模板
    python3 weekly_plan.py --status             # 本周七天的状态

计划文件是手写的 markdown 表格，人可以直接改。这个脚本只负责查漏和回写，
不做选题 —— 选题得看当时在写什么、读者在问什么，机器排不出来。
"""
from __future__ import annotations

import argparse
import re
import sys
from datetime import date as Date, timedelta
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))

from common import (
    ROOT,
    iso_week,
    load_config,
    load_ledger,
    plan_path,
    tz,
    today,
)

PLAN_DIR = ROOT / "plan"


def week_dates(iso_week_str: str) -> list[Date]:
    year, week = iso_week_str.split("-W")
    first = Date.fromisocalendar(int(year), int(week), 1)
    return [first + timedelta(days=i) for i in range(7)]


def parse_week_file(path: Path) -> dict[str, dict]:
    rows: dict[str, dict] = {}
    if not path.exists():
        return rows
    for line in path.read_text(encoding="utf-8").splitlines():
        if not line.startswith("|"):
            continue
        cells = [c.strip() for c in line.strip().strip("|").split("|")]
        if len(cells) < 6 or not cells[0].startswith("2"):
            continue
        rows[cells[0]] = {
            "genre": cells[1],
            "title": cells[2],
            "series": "" if cells[3] in ("-", "—", "") else cells[3],
            "material": cells[4],
            "status": cells[5],
        }
    return rows


def check_next_week(as_of: Date) -> dict:
    """周日调用：确认下一周七天的计划都在。缺了就报出来。"""
    next_week = as_of + timedelta(days=(7 - as_of.isoweekday()) + 1)
    key = iso_week(next_week)
    path = plan_path(next_week)
    rows = parse_week_file(path)

    missing = [d.isoformat() for d in week_dates(key) if d.isoformat() not in rows]
    # 模板里留的「待定」不算填过。检查是用来催人的，不是用来庆祝文件存在的
    empty_titles = [
        k for k, v in rows.items()
        if not v["title"] or v["title"] in ("-", "—", "待定")
    ]
    # 素材列写的是「这篇要跑什么实验」，模板留下的「周二」也算没填
    unfilled_material = [
        k for k, v in rows.items()
        if not v["material"] or v["material"] in ("-", "—")
        or re.fullmatch(r"周[一二三四五六日]", v["material"])
    ]

    return {
        "week": key,
        "file": str(path),
        "exists": path.exists(),
        "planned": len(rows),
        "missing_dates": missing,
        "empty_titles": empty_titles,
        "unfilled_material": unfilled_material,
        "ok": path.exists() and not missing and not empty_titles and not unfilled_material,
    }


def template(key: str) -> str:
    dates = week_dates(key)
    lines = [
        f"# {key}（{dates[0].month:02d}-{dates[0].day:02d} ~ {dates[-1].month:02d}-{dates[-1].day:02d}）",
        "",
        "系列：（如果不开系列写 -）",
        "",
        "| 日期 | 体裁 | 标题 | 系列 | 素材 | 状态 |",
        "| --- | --- | --- | --- | --- | --- |",
    ]
    weekdays = "一二三四五六日"
    for i, d in enumerate(dates):
        lines.append(
            f"| {d.isoformat()} | 待定 | 待定 | - | 周{weekdays[i]} | 待写 |"
        )
    lines += ["", "## 备注", "", "- 素材列写「这篇要跑什么实验 / 查什么源码」，不写「写什么道理」。"]
    return "\n".join(lines) + "\n"


def week_status(d: Date) -> dict:
    path = plan_path(d)
    rows = parse_week_file(path)
    ledger = load_ledger()
    published = {e["date"]: e.get("status") for e in ledger.get("entries", [])}
    days = []
    for day in week_dates(iso_week(d)):
        key = day.isoformat()
        row = rows.get(key, {})
        days.append(
            {
                "date": key,
                "title": row.get("title", ""),
                "plan_status": row.get("status", "无"),
                "ledger": published.get(key, ""),
            }
        )
    return {"week": iso_week(d), "file": str(path), "days": days}


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--check", action="store_true")
    ap.add_argument("--template")
    ap.add_argument("--status", action="store_true")
    args = ap.parse_args()

    cfg = load_config()
    d = today(cfg)

    if args.template:
        out = PLAN_DIR / f"{args.template}.md"
        if out.exists():
            raise SystemExit(f"{out} 已存在，不覆盖")
        out.parent.mkdir(parents=True, exist_ok=True)
        out.write_text(template(args.template), encoding="utf-8")
        print(f"已生成 {out}")
        return 0

    if args.check:
        import json

        res = check_next_week(d)
        print(json.dumps(res, ensure_ascii=False, indent=2))
        return 0 if res["ok"] else 1

    if args.status:
        import json

        print(json.dumps(week_status(d), ensure_ascii=False, indent=2))
        return 0

    ap.print_help()
    return 2


if __name__ == "__main__":
    sys.exit(main())
