"""blog-autopilot 公共工具：配置、台账、周计划、调度窗口。仅依赖标准库。"""
from __future__ import annotations

import hashlib
import json
import os
import re
import subprocess
from datetime import date, datetime, timedelta
from pathlib import Path
from zoneinfo import ZoneInfo

ROOT = Path(__file__).resolve().parent.parent
HOME = Path.home()


_PATH_ENV = {
    "myBlog": "BLOG_PATH_MYBLOG",
    "gh_pages": "BLOG_PATH_GH_PAGES",
    "astro": "BLOG_PATH_ASTRO",
}


def load_config() -> dict:
    cfg = json.loads((ROOT / "config.json").read_text(encoding="utf-8"))
    # CI 把三个仓库 checkout 到临时目录，用环境变量覆盖本机绝对路径
    for key, env in _PATH_ENV.items():
        value = os.environ.get(env)
        if value:
            cfg["paths"][key] = value
    return cfg


def load_ledger() -> dict:
    return json.loads((ROOT / "ledger.json").read_text(encoding="utf-8"))


def save_ledger(data: dict) -> None:
    (ROOT / "ledger.json").write_text(
        json.dumps(data, ensure_ascii=False, indent=2) + "\n", encoding="utf-8"
    )


def today() -> date:
    return datetime.now().astimezone().date()


def iso_week(d: date) -> str:
    y, w, _ = d.isocalendar()
    return f"{y}-W{w:02d}"


def log(msg: str, level: str = "INFO") -> None:
    line = f"{datetime.now().astimezone():%Y-%m-%d %H:%M:%S} [{level}] {msg}"
    print(line, flush=True)
    log_dir = ROOT / "logs"
    log_dir.mkdir(parents=True, exist_ok=True)
    with (log_dir / "daily.log").open("a", encoding="utf-8") as f:
        f.write(line + "\n")


def seed_int(*parts) -> int:
    h = hashlib.sha256("|".join(str(p) for p in parts).encode("utf-8")).hexdigest()
    return int(h[:16], 16)


def pick_window(d: date, cfg: dict) -> str:
    """按日期哈希决定当天是上午还是晚上，同一天结果恒定，幂等。"""
    s = cfg["schedule"]
    if d.isoformat() == s["first_run_date"]:
        return s["first_window"]
    threshold = int(round(float(s["am_ratio"]) * 100))
    return "AM" if seed_int("window", d.isoformat()) % 100 < threshold else "PM"


def jitter_minutes(d: date, slug: str, cfg: dict) -> int:
    lo, hi = cfg["schedule"]["display_jitter_minutes"]
    if d.isoformat() == cfg["schedule"]["first_run_date"]:
        return 0
    return seed_int("jitter", d.isoformat(), slug) % (hi - lo + 1) + lo


def infer_window() -> str:
    """未显式指定窗口时按当前时间判断：中午前算 AM，之后算 PM。"""
    return "AM" if datetime.now().astimezone().hour < 12 else "PM"


def pub_datetime(d: date, window: str, slug: str, cfg: dict) -> datetime:
    """文章显示时间：按实际发布时刻往前随机 0~45 分钟（publish_moment），
    或按固定窗口时间往前偏移（window，旧行为）。
    AstroPaper 的 scheduledPostMargin 会把未来时间当定时文章隐藏，不能往后 jitter。
    取整到分钟，保证 prepare / render_astro / render_hexo 三次调用拿到同一时间。"""
    offset = jitter_minutes(d, slug, cfg)
    s = cfg["schedule"]
    if s.get("display_time_mode") == "publish_moment":
        now = datetime.now(ZoneInfo(cfg.get("timezone", "Asia/Shanghai")))
        return now.replace(tzinfo=None, second=0, microsecond=0) - timedelta(minutes=offset)
    hh, mm = (int(x) for x in s["windows"][window].split(":"))
    return datetime(d.year, d.month, d.day, hh, mm) - timedelta(minutes=offset)


def clean_slug(title: str) -> str:
    s = re.sub(r"[\s/\\:*?\"<>|#\[\]{}()（）《》，。！？、：；…—\-'`,.!?]+", "", title)
    return (s[:40] or "post")


def yaml_str(s) -> str:
    """字符串一律加双引号，避免中文标点/冒号破坏 YAML。时间与布尔值不要调用它。"""
    return '"' + str(s).replace("\\", "\\\\").replace('"', '\\"') + '"'


def parse_plan(d: date) -> dict | None:
    p = ROOT / "plan" / f"{iso_week(d)}.md"
    if not p.exists():
        return None
    for line in p.read_text(encoding="utf-8").splitlines():
        if not line.startswith("|"):
            continue
        cells = [c.strip() for c in line.strip().strip("|").split("|")]
        if len(cells) >= 7 and cells[0] == d.isoformat():
            return {
                "date": cells[0],
                "window": cells[1],
                "genre": cells[2],
                "title": cells[3],
                "series": cells[4],
                "facts": cells[5].split(),
                "status": cells[6],
            }
    return None


def update_plan_status(d: date, status: str) -> bool:
    p = ROOT / "plan" / f"{iso_week(d)}.md"
    if not p.exists():
        return False
    text = p.read_text(encoding="utf-8")
    out = []
    changed = False
    for line in text.splitlines():
        if line.startswith("|") and line.strip().strip("|").split("|")[0].strip() == d.isoformat():
            cells = [c.strip() for c in line.strip().strip("|").split("|")]
            if len(cells) >= 7 and cells[6] != status:
                cells[6] = status
                line = "| " + " | ".join(cells) + " |"
                changed = True
        out.append(line)
    if changed:
        p.write_text("\n".join(out) + "\n", encoding="utf-8")
    return changed


def draft_path(d: date, slug: str) -> Path:
    return ROOT / "drafts" / f"{d.isoformat()}-{slug}.md"


def parse_draft(path: Path) -> dict:
    txt = Path(path).read_text(encoding="utf-8")
    m = re.match(r"\A---\s*\n(.*?)\n---\s*\n(.*)\Z", txt, re.S)
    if not m:
        raise ValueError("草稿缺少 frontmatter（需要 --- 包裹的元数据块）")
    meta: dict[str, str] = {}
    for line in m.group(1).splitlines():
        if ":" in line and not line.strip().startswith("#"):
            k, v = line.split(":", 1)
            meta[k.strip()] = v.strip().strip('"')
    groups = re.findall(r"\[([^\]]*)\]", meta.get("tags", ""))
    tags = [x.strip() for g in groups for x in g.split(",") if x.strip()]
    if not m.group(2).strip():
        raise ValueError("草稿正文为空")
    return {
        "title": meta.get("title", ""),
        "genre": meta.get("genre", ""),
        "series": meta.get("series", ""),
        "description": meta.get("description", ""),
        "tags": tags or ["随笔"],
        "body": m.group(2).strip(),
    }


def run(cmd, cwd=None, timeout: int = 600, check: bool = True):
    result = subprocess.run(
        cmd,
        cwd=str(cwd) if cwd else None,
        shell=isinstance(cmd, str),
        capture_output=True,
        text=True,
        timeout=timeout,
    )
    if check and result.returncode != 0:
        raise RuntimeError(
            f"命令失败: {cmd}\nstdout: {result.stdout[-800:]}\nstderr: {result.stderr[-800:]}"
        )
    return result


def git_available(cfg: dict) -> bool:
    """本地代理偶发 502 会误判成通道不可用，重试一次再决定要不要降级 API。"""
    r = cfg["repos"]["astro"]
    url = f"https://github.com/{r['owner']}/{r['name']}.git"
    for _ in range(2):
        try:
            # 代理故障时 CONNECT 约 10s 才返回 502，别让它拖住整轮发布
            res = run(["git", "ls-remote", url, "HEAD"], check=False, timeout=12)
            if res.returncode == 0:
                return True
        except Exception:
            pass
    return False
