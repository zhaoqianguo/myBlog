#!/usr/bin/env python3
"""两条线共用的发布辅助入口。

  python3 cloud.py check                        环境自检（不写任何东西）
  python3 cloud.py sync [--dry-run]             把控制面状态推到 myBlog/master
  python3 cloud.py publish [--dry-run] [--date] 晚间兜底发布

本机线写完草稿或人工即发后跑 sync；云端 workflow 每晚 20:17 跑 publish。
判重不依赖台账：直接查两个产物仓库当天有没有 `post: ... (日期)` 提交。
"""
from __future__ import annotations

import argparse
import hashlib
import json
import os
import sys
from datetime import date, timedelta
from pathlib import Path

ROOT = Path(__file__).resolve().parent
sys.path.insert(0, str(ROOT / "scripts"))

from common import load_config, parse_plan, today  # noqa: E402
from github_api import api, commit_files  # noqa: E402

OWNER = "zhaoqianguo"
PREFIX = "scripts/publish/"
SOURCE_REPO = "myBlog"
SOURCE_BRANCH = "master"
EXCLUDE_NAMES = {"VOICE.md", "STYLE_CORPUS.md", "FACT_POOL.md"}
PRODUCT_SIDES = {
    "astro": ("astro-blog", "main"),
    "gh_pages": ("zhaoqianguo.github.io", "gh-pages"),
}


def _blob_sha(text: str) -> str:
    data = text.encode("utf-8")
    return hashlib.sha1(b"blob " + str(len(data)).encode() + b"\0" + data).hexdigest()


def collect_state() -> dict[str, str]:
    """白名单收集：只推运行云端发布所必需的文件。"""
    out: dict[str, str] = {}
    for name in (".gitignore", "cloud.py", "config.json", "ledger.json"):
        p = ROOT / name
        if p.is_file():
            out[PREFIX + name] = p.read_text(encoding="utf-8")
    for sub in ("scripts", "plan", "drafts"):
        base = ROOT / sub
        if not base.is_dir():
            continue
        for p in sorted(base.iterdir()):
            if not p.is_file() or p.name in EXCLUDE_NAMES:
                continue
            if sub == "scripts" and p.suffix != ".py":
                continue
            if p.suffix not in (".py", ".md", ".json"):
                continue
            out[f"{PREFIX}{sub}/{p.name}"] = p.read_text(encoding="utf-8")
    return out


def _remote_blob_shas() -> dict[str, str]:
    tree = api("GET", f"/repos/{OWNER}/{SOURCE_REPO}/git/trees/{SOURCE_BRANCH}?recursive=1")
    if tree.get("truncated"):
        return {}
    return {i["path"]: i["sha"] for i in tree.get("tree", []) if i.get("type") == "blob"}


def sync_state(dry_run: bool = False, message: str | None = None) -> dict:
    files = collect_state()
    if dry_run:
        return {"action": "dry-run", "files": len(files), "paths": sorted(files)}
    remote = _remote_blob_shas()
    changed = {k: v for k, v in files.items() if remote.get(k) != _blob_sha(v)}
    if not changed:
        return {"action": "already", "files": 0}
    msg = message or f"chore: sync autopilot state ({today().isoformat()}) [skip ci]"
    sha = commit_files(OWNER, SOURCE_REPO, SOURCE_BRANCH, changed, msg)
    return {"action": "synced", "sha": sha[:8], "files": len(changed), "paths": sorted(changed)}


def check(cfg: dict) -> tuple[dict, int]:
    out: dict = {"auth": None, "heads": {}, "checks": {}}
    try:
        out["auth"] = api("GET", "/user").get("login")
    except Exception as exc:
        return {"error": f"GitHub 认证失败: {exc}"}, 1
    heads = {"source": (SOURCE_REPO, SOURCE_BRANCH), **PRODUCT_SIDES}
    for label, (repo, branch) in heads.items():
        try:
            out["heads"][label] = api(
                "GET", f"/repos/{OWNER}/{repo}/git/ref/heads/{branch}"
            )["object"]["sha"][:8]
        except Exception as exc:
            out["heads"][label] = f"ERROR: {str(exc)[:160]}"
    myblog = Path(cfg["paths"]["myBlog"])
    ghp = Path(cfg["paths"]["gh_pages"])
    out["checks"] = {
        "myBlog_root": str(myblog),
        "hexo_bin": (myblog / "node_modules" / ".bin" / "hexo").exists(),
        "package_lock": (myblog / "package-lock.json").exists(),
        "gh_pages_index": (ghp / "index.html").exists(),
        "drafts": len(list((ROOT / "drafts").glob("*.md"))),
        "plans": len(list((ROOT / "plan").glob("*.md"))),
        "local_date": today().isoformat(),
        "cloud_mode": os.environ.get("AUTOPILOT_CLOUD") == "1",
        "token_from_env": bool(os.environ.get("GH_TOKEN") or os.environ.get("BLOG_PAT")),
    }
    ok = (
        all(out["checks"][k] for k in ("hexo_bin", "package_lock", "gh_pages_index"))
        and out["checks"]["plans"] > 0
        and not any(str(v).startswith("ERROR") for v in out["heads"].values())
    )
    out["ok"] = ok
    return out, (0 if ok else 1)


def published_commits(d: date) -> dict:
    """两条线唯一的耦合点：产物仓库当天的 post 提交。"""
    since = f"{d - timedelta(days=1)}T00:00:00Z"
    found: dict = {}
    for label, (repo, branch) in PRODUCT_SIDES.items():
        try:
            commits = api(
                "GET", f"/repos/{OWNER}/{repo}/commits?sha={branch}&since={since}&per_page=50"
            )
            msgs = [c["commit"]["message"].splitlines()[0] for c in commits] if isinstance(commits, list) else []
        except Exception as exc:
            found[f"{label}_error"] = [str(exc)[:200]]
            msgs = []
        found[label] = [m for m in msgs if m.startswith("post: ") and f"({d.isoformat()})" in m]
    return found


def publish(cfg: dict, d: date, dry_run: bool) -> tuple[dict, int]:
    hold = ROOT / "HOLD"
    if hold.exists():
        reason = hold.read_text(encoding="utf-8").strip() or "人工暂停"
        return {"action": "skip", "reason": f"HOLD: {reason}"}, 0

    found = published_commits(d)
    if found.get("astro") and found.get("gh_pages"):
        return {"action": "skip", "reason": "今天两站都已有发布提交（本机线已发）", "evidence": found}, 0

    plan = parse_plan(d)
    if not plan:
        return {"action": "need_plan", "date": d.isoformat()}, 1
    if plan["status"] in ("skipped", "published"):
        return {"action": "skip", "reason": f"周计划里今天标记为 {plan['status']}"}, 0

    drafts = sorted((ROOT / "drafts").glob(f"{d.isoformat()}-*.md"))
    if not drafts:
        return {
            "action": "need_draft",
            "date": d.isoformat(),
            "hint": "本机下午没把当天草稿推上来，云端不发布、不补发",
        }, (0 if dry_run else 1)

    os.environ["AUTOPILOT_CLOUD"] = "1"
    import daily  # noqa: E402

    result = daily.publish(d, None, dry_run, False)
    if not dry_run and result.get("action") in ("published", "partial"):
        result["state_sync"] = sync_state(
            message=f"chore: sync autopilot state ({d.isoformat()}) [skip ci]"
        )
    bad = ("error", "lint_failed", "need_draft", "awaiting_approval")
    return result, (1 if result.get("action") in bad else 0)


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("command", choices=["check", "sync", "publish"])
    ap.add_argument("--dry-run", action="store_true")
    ap.add_argument("--date")
    args = ap.parse_args()
    d = date.fromisoformat(args.date) if args.date else today()
    try:
        if args.command == "check":
            result, code = check(load_config())
        elif args.command == "sync":
            result, code = sync_state(args.dry_run), 0
        else:
            result, code = publish(load_config(), d, args.dry_run)
    except Exception as exc:
        result, code = {"action": "error", "error": f"{type(exc).__name__}: {exc}"}, 1
    print(json.dumps(result, ensure_ascii=False, indent=2))
    sys.exit(code)


if __name__ == "__main__":
    main()
