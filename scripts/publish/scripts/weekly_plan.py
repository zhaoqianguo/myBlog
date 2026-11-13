#!/usr/bin/env python3
"""周计划校验与滚动。
  python3 scripts/weekly_plan.py --check [YYYY-MM-DD]   检查下一周计划是否齐备
  python3 scripts/weekly_plan.py --template 2026-W48     打印空白周计划模板
  python3 scripts/weekly_plan.py --series-status         输出系列进度
"""
from __future__ import annotations

import argparse
import json
import re
import sys
from datetime import date, timedelta
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
from common import ROOT, iso_week, load_ledger, today


def week_range(anchor: date) -> tuple[date, list[str]]:
    monday = anchor - timedelta(days=anchor.weekday())
    return monday, [(monday + timedelta(days=i)).isoformat() for i in range(7)]


def check_next_week(d: date) -> dict:
    anchor = d + timedelta(days=7)
    monday, expected = week_range(anchor)
    week = iso_week(monday)
    p = ROOT / "plan" / f"{week}.md"
    if not p.exists():
        return {"week": week, "ready": False, "reason": f"缺少 {week}.md，周日运行前必须生成", "path": str(p)}
    found = re.findall(r"^\|\s*(\d{4}-\d{2}-\d{2})\s*\|", p.read_text(encoding="utf-8"), re.M)
    missing = [x for x in expected if x not in found]
    return {
        "week": week,
        "ready": not missing,
        "expected_days": expected,
        "found_days": found,
        "missing": missing,
        "path": str(p),
    }


def template(week: str) -> str:
    y, w = week.split("-W")
    monday = date.fromisocalendar(int(y), int(w), 1)
    days = [(monday + timedelta(days=i)).isoformat() for i in range(7)]
    rows = "\n".join(f"| {x} | AM/PM | 待定 | 待定 | - | Fxx | planned |" for x in days)
    return (
        f"# {week} 计划（{days[0]} ~ {days[-1]}）\n"
        "状态: upcoming\n"
        "生成于: （填当天日期）\n"
        "说明: 提前一周规划，七篇选题、体裁、素材来源、系列进度都要写清楚。\n\n"
        "| 日期 | 窗口 | 体裁 | 标题 | 系列 | 素材 | 状态 |\n"
        "|---|---|---|---|---|---|---|\n"
        f"{rows}\n\n"
        "## 备用选题\n- （至少 2 条，同样基于 FACT_POOL）\n"
    )


def series_status() -> dict:
    ledger = load_ledger()
    out = {}
    for key, s in ledger.get("series", {}).items():
        done = sum(
            1
            for e in ledger["entries"]
            if e.get("series", "").startswith(key) and e.get("status") == "published"
        )
        out[key] = {**s, "published_actual": done, "remaining": max(0, s["total"] - done)}
    return out


if __name__ == "__main__":
    ap = argparse.ArgumentParser()
    ap.add_argument("--check", nargs="?", const="", default=None)
    ap.add_argument("--template")
    ap.add_argument("--series-status", action="store_true")
    args = ap.parse_args()
    if args.template:
        print(template(args.template))
    elif args.series_status:
        print(json.dumps(series_status(), ensure_ascii=False, indent=2))
    elif args.check is not None:
        d = date.fromisoformat(args.check) if args.check else today()
        print(json.dumps(check_next_week(d), ensure_ascii=False, indent=2))
    else:
        print(json.dumps({"check": check_next_week(today()), "series": series_status()}, ensure_ascii=False, indent=2))
