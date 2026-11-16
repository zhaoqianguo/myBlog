#!/usr/bin/env python3
"""发布一篇：草稿 → 文风闸门 → 渲染两端 → hexo 构建 → 推 gh-pages → 推 astro。

    python3 publish.py --date 2026-11-16            # 正常发布
    python3 publish.py --date 2026-11-16 --dry-run  # 只跑闸门和构建，不推
    python3 publish.py --check                      # 只看今天该不该发、发了没

设计上刻意不做两件事：
- 不做 git push（本机到 github.com 的 git 协议基本不通），全走 HTTPS API。
- 不删远端文件（skip_deletions），只增改。删错一个页面比多一个孤儿页糟糕得多。
"""
from __future__ import annotations

import argparse
import json
import subprocess
import sys
from datetime import date as Date
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))

import github_api as gh
import render
import voice_lint
from common import (
    ROOT,
    log,
    load_config,
    load_ledger,
    parse_draft,
    parse_plan,
    pub_datetime,
    save_ledger,
    today,
    update_plan_status,
)

PUBLIC = "public"


def draft_path(d: Date) -> Path:
    return ROOT / "drafts" / f"{d.isoformat()}.md"


def find_draft(d: Date) -> Path | None:
    p = draft_path(d)
    if p.exists():
        return p
    # 也接受带标题后缀的草稿：2026-11-16-微任务队列在哪一步清空.md
    hits = sorted((ROOT / "drafts").glob(f"{d.isoformat()}-*.md"))
    return hits[0] if hits else None


def run_hexo(cfg: dict) -> Path:
    root = Path(cfg["paths"]["myBlog"])
    hexo = root / "node_modules" / ".bin" / "hexo"
    if not hexo.exists():
        raise SystemExit(f"找不到 hexo：{hexo}，先在 myBlog 跑 npm ci")
    for args in (["clean"], ["generate"]):
        res = subprocess.run(
            [str(hexo), *args], cwd=root, capture_output=True, text=True, timeout=600
        )
        if res.returncode != 0:
            raise SystemExit(f"hexo {args[0]} 失败:\n{res.stdout}\n{res.stderr}")
    public = root / PUBLIC
    if not public.exists():
        raise SystemExit("hexo generate 没产出 public/")

    # 0 字节的文章页说明构建中途出过错，这种页面推上去就是死链
    empty = [
        str(p.relative_to(public))
        for p in public.rglob("index.html")
        if p.stat().st_size == 0
    ]
    if empty:
        raise SystemExit(f"构建出 0 字节页面：{empty[:5]}")
    return public


def collect_changes(public: Path, cfg: dict) -> tuple[dict[str, bytes], list[str]]:
    """对比本地 public/ 与远端 gh-pages，返回要推的文件和要删的文件。"""
    repo = cfg["repos"]["gh_pages"]
    tree = gh.api(
        "GET",
        f"{gh.repo_path(repo['owner'], repo['name'])}/git/trees/{repo['branch']}?recursive=1",
    )
    remote = {x["path"]: x["sha"] for x in tree["tree"] if x["type"] == "blob"}

    upload: dict[str, bytes] = {}
    for f in sorted(public.rglob("*")):
        if not f.is_file():
            continue
        rel = str(f.relative_to(public))
        data = f.read_bytes()
        if remote.get(rel) != _blob_sha(data):
            upload[rel] = data

    deletions: list[str] = []
    if not cfg["publish"].get("skip_deletions", True):
        deletions = sorted(p for p in remote if p not in {
            str(f.relative_to(public)) for f in public.rglob("*") if f.is_file()
        })
    return upload, deletions


def _blob_sha(data: bytes) -> str:
    import hashlib

    h = hashlib.sha1()
    h.update(b"blob %d\0" % len(data))
    h.update(data)
    return h.hexdigest()


def commit_local_myblog(cfg: dict, paths: list[str], message: str) -> str | None:
    """在 myBlog 本地仓库提交源码。

    只提交，不 push：本机到 github.com 的 git 协议基本不通，push 必超时。
    本地留个提交，等于源码有另一份历史；以后网络好了 `git push` 一把就能推上去。
    推送失败不影响发布，所以这里全部吞掉异常。
    """
    root = Path(cfg["paths"]["myBlog"])
    try:
        subprocess.run(["git", "add", "--", *paths], cwd=root, check=True,
                       capture_output=True, timeout=60)
        res = subprocess.run(
            ["git", "commit", "-m", message], cwd=root,
            capture_output=True, text=True, timeout=60,
        )
        if res.returncode != 0:
            log(f"myBlog 本地提交跳过：{res.stdout.strip() or res.stderr.strip()}")
            return None
        sha = subprocess.run(
            ["git", "rev-parse", "HEAD"], cwd=root,
            capture_output=True, text=True, timeout=30,
        ).stdout.strip()
        log(f"myBlog 本地提交 -> {sha[:8]}")
        return sha
    except Exception as exc:
        log(f"myBlog 本地提交失败（不影响发布）：{exc}", "WARN")
        return None


def hold_file() -> Path:
    return ROOT / "HOLD"


def publish(d: Date, cfg: dict, dry_run: bool, force: bool = False) -> dict:
    if hold_file().exists() and not dry_run:
        raise SystemExit(f"{hold_file()} 还在，停发。删掉它再跑。")

    src = find_draft(d)
    if not src:
        raise SystemExit(f"{d} 没有草稿：{draft_path(d)} 不存在")

    # 已经发过就别再发一遍：重跑会改显示时间、重推一遍文件，旧链接的时间戳也会变
    done = next(
        (e for e in load_ledger().get("entries", []) if e.get("date") == d.isoformat() and e.get("status") == "published"),
        None,
    )
    if done and not force:
        log(f"{d} 已经发过了（{done.get('slug')}），要重发加 --force")
        return done

    # 1. 闸门。不通过就不许往下走 —— 这一步是整套系统的价值所在
    lint = voice_lint.lint(src)
    if not lint["pass"]:
        print(json.dumps(lint, ensure_ascii=False, indent=2))
        raise SystemExit("文风闸门未通过，不出稿")

    # 2. 渲染两端
    info = render.write_outputs(src, d, cfg)
    log(f"渲染完成：{info['stem']}")
    log(f"  显示时间 {info['pub_datetime']}")

    # 3. hexo 构建
    public = run_hexo(cfg)
    upload, deletions = collect_changes(public, cfg)
    log(f"gh-pages 待推 {len(upload)} 个文件" + (f"，待删 {len(deletions)} 个" if deletions else ""))

    if dry_run:
        for p in sorted(upload)[:20]:
            print("  +", p)
        return {"dry_run": True, "would_upload": len(upload), **info}

    # 4. 推 gh-pages
    repo = cfg["repos"]["gh_pages"]
    msg = cfg["publish"]["commit_message"].format(title=info["title"], date=d.isoformat())
    res_gh = gh.commit_files(
        repo["owner"], repo["name"], repo["branch"], upload, msg, deletions
    )
    log(f"gh-pages -> {res_gh['commit'][:8]}（{len(res_gh['changed'])} 个文件）")

    # 5. 推 astro 正文
    astro_repo = cfg["repos"]["astro"]
    astro_rel = f"src/content/blog/{info['stem']}.md"
    res_astro = gh.commit_files(
        astro_repo["owner"],
        astro_repo["name"],
        astro_repo["branch"],
        {astro_rel: Path(info["astro_path"]).read_bytes()},
        msg,
    )
    log(f"astro -> {res_astro['commit'][:8]}")

    # 6. 源码在 myBlog 本地落地成一次提交（不 push，见函数注释）
    hexo_rel = f"source/_posts/{info['stem']}.md"
    src_sha = commit_local_myblog(cfg, [hexo_rel], msg)

    # 7. 记账
    ledger = load_ledger()
    entry = {
        "date": d.isoformat(),
        "slug": info["slug"],
        "title": info["title"],
        "pub_datetime": info["pub_datetime"],
        "status": "published",
        "gh_pages_sha": res_gh["commit"],
        "gh_pages_files": len(res_gh["changed"]),
        "astro_sha": res_astro["commit"],
        "myBlog_source_sha": src_sha,
        "lint": {"chars": lint["stats"]["chars"], "warnings": lint["warnings"]},
    }
    ledger.setdefault("entries", [])
    ledger["entries"] = [e for e in ledger["entries"] if e.get("date") != d.isoformat()]
    ledger["entries"].append(entry)
    ledger["entries"].sort(key=lambda e: e["date"])
    save_ledger(ledger)

    update_plan_status(d, "已发布")
    return entry


def check(cfg: dict) -> dict:
    d = today(cfg)
    ledger = load_ledger()
    done = next((e for e in ledger.get("entries", []) if e.get("date") == d.isoformat()), None)
    plan = parse_plan(d)
    draft = find_draft(d)
    return {
        "date": d.isoformat(),
        "already_published": done is not None,
        "ledger_status": (done or {}).get("status"),
        "plan": plan,
        "draft_ready": draft is not None,
        "draft_path": str(draft) if draft else None,
    }


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--date")
    ap.add_argument("--dry-run", action="store_true")
    ap.add_argument("--check", action="store_true")
    ap.add_argument("--force", action="store_true", help="当天已发过也重发一遍")
    args = ap.parse_args()

    cfg = load_config()

    if args.check:
        print(json.dumps(check(cfg), ensure_ascii=False, indent=2))
        return 0

    d = Date.fromisoformat(args.date) if args.date else today(cfg)
    entry = publish(d, cfg, args.dry_run, args.force)
    print(json.dumps(entry, ensure_ascii=False, indent=2))
    return 0


if __name__ == "__main__":
    sys.exit(main())
