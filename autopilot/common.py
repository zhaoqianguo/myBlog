"""公共工具：配置、台账、周计划、发布时间。仅依赖标准库。"""
from __future__ import annotations

import hashlib
import json
import os
import re
from datetime import date, datetime, timedelta
from pathlib import Path
from zoneinfo import ZoneInfo

ROOT = Path(__file__).resolve().parent

_PATH_ENV = {
    "myBlog": "BLOG_PATH_MYBLOG",
    "gh_pages": "BLOG_PATH_GH_PAGES",
    "astro": "BLOG_PATH_ASTRO",
}


def load_config() -> dict:
    cfg = json.loads((ROOT / "config.json").read_text(encoding="utf-8"))
    for key, env in _PATH_ENV.items():
        value = os.environ.get(env)
        if value:
            cfg["paths"][key] = value
    return cfg


def load_ledger() -> dict:
    p = ROOT / "ledger.json"
    if not p.exists():
        return {"entries": [], "series": []}
    return json.loads(p.read_text(encoding="utf-8"))


def save_ledger(data: dict) -> None:
    (ROOT / "ledger.json").write_text(
        json.dumps(data, ensure_ascii=False, indent=2) + "\n", encoding="utf-8"
    )


def tz(cfg: dict) -> ZoneInfo:
    return ZoneInfo(cfg.get("timezone", "Asia/Shanghai"))


def now(cfg: dict) -> datetime:
    return datetime.now(tz(cfg))


def today(cfg: dict) -> date:
    return now(cfg).date()


def iso_week(d: date) -> str:
    y, w, _ = d.isocalendar()
    return f"{y}-W{w:02d}"


def log(msg: str, level: str = "INFO") -> None:
    line = f"{datetime.now().astimezone():%Y-%m-%d %H:%M:%S} [{level}] {msg}"
    print(line, flush=True)
    logs = ROOT / "logs"
    logs.mkdir(parents=True, exist_ok=True)
    with (logs / "daily.log").open("a", encoding="utf-8") as f:
        f.write(line + "\n")


def seed_int(*parts) -> int:
    h = hashlib.sha256("|".join(str(p) for p in parts).encode("utf-8")).hexdigest()
    return int(h[:16], 16)


def jitter_minutes(d: date, slug: str, cfg: dict) -> int:
    """当天显示时间的随机提前量，同一日期恒定，多次调用结果一致。"""
    lo, hi = cfg["schedule"]["display_jitter_minutes"]
    return seed_int("jitter", d.isoformat(), slug) % (hi - lo + 1) + lo


def pub_datetime(d: date, slug: str, cfg: dict) -> datetime:
    """文章上显示的发布时间 = 真正推送的那一刻。

    不套「窗口时刻 + 随机偏移」那套。定时任务每晚同一时刻启动，但每篇写多久不一样，
    推送时刻天然就散在窗口里，用它当显示时间反而真实 —— 每篇都是 20:1x 二十几分
    那种整整齐齐的分钟数，才像机器干的。
    """
    return now(cfg).replace(second=0, microsecond=0)


def clean_slug(title: str) -> str:
    s = re.sub(r"[\s/\\:*?\"<>|#\[\]{}()（）《》，。！？、：；…—\-'`,.!?]+", "", title)
    return s[:40] or "post"


def yaml_str(s) -> str:
    """字符串一律加双引号；时间和布尔值不要走这里。"""
    return '"' + str(s).replace("\\", "\\\\").replace('"', '\\"') + '"'


PLAN_HEADER = "| 日期 | 体裁 | 标题 | 系列 | 素材 | 状态 |"
PLAN_SEP = "| --- | --- | --- | --- | --- | --- |"


def plan_path(d: date) -> Path:
    return ROOT / "plan" / f"{iso_week(d)}.md"


def parse_plan(d: date) -> dict | None:
    p = plan_path(d)
    if not p.exists():
        return None
    for line in p.read_text(encoding="utf-8").splitlines():
        if not line.startswith("|"):
            continue
        cells = [c.strip() for c in line.strip().strip("|").split("|")]
        if len(cells) >= 6 and cells[0] == d.isoformat():
            return {
                "date": cells[0],
                "genre": cells[1],
                "title": cells[2],
                "series": "" if cells[3] in ("-", "—", "") else cells[3],
                "material": cells[4],
                "status": cells[5],
            }
    return None


def update_plan_status(d: date, status: str) -> None:
    p = plan_path(d)
    if not p.exists():
        return
    out = []
    for line in p.read_text(encoding="utf-8").splitlines():
        if line.startswith("|"):
            cells = [c.strip() for c in line.strip().strip("|").split("|")]
            if len(cells) >= 6 and cells[0] == d.isoformat():
                cells[-1] = status
                line = "| " + " | ".join(cells) + " |"
        out.append(line)
    p.write_text("\n".join(out) + "\n", encoding="utf-8")


def parse_draft(path: Path) -> dict:
    """解析 canonical 草稿：frontmatter(title/tags/description) + 正文。"""
    raw = path.read_text(encoding="utf-8")
    m = re.match(r"^---\n(.*?)\n---\n?(.*)$", raw, re.S)
    if not m:
        raise SystemExit(f"{path} 缺少 frontmatter")
    fm, body = m.group(1), m.group(2).strip()
    meta: dict = {"tags": []}
    key = None
    for line in fm.splitlines():
        if re.match(r"^\s*-\s+", line) and key == "tags":
            meta["tags"].append(line.strip()[1:].strip().strip('"'))
            continue
        mm = re.match(r"^([a-zA-Z_]+):\s*(.*)$", line)
        if mm:
            key, value = mm.group(1), mm.group(2).strip().strip('"')
            # tags 是块状列表：`tags:` 后面跟若干 `- xxx`，不要把空值写进去
            if key == "tags" and not value:
                meta["tags"] = []
                continue
            meta[key] = value
    meta["body"] = body
    return meta
