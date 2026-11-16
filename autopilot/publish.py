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


def commit_local(cfg: dict, paths: list[str], message: str) -> str | None:
    """在 myBlog 本地仓库把源码提交上去（push 由 push_source_to_myblog 负责）。"""
    root = Path(cfg["paths"]["myBlog"])
    # 草稿也一起提交：以后想回头改文风、看实验记录，得从仓库里找得到
    extra = ["autopilot/drafts", "autopilot/plan", "autopilot/ledger.json"]
    try:
        _git(root, "add", "--", *paths, *[p for p in extra if (root / p).exists()], timeout=90)
        res = _git(root, "commit", "-m", message, timeout=60)
        if res.returncode != 0:
            log(f"myBlog 本地提交跳过：{res.stdout.strip() or res.stderr.strip()}")
            return None
        sha = _git(root, "rev-parse", "HEAD", timeout=30).stdout.strip()
        log(f"myBlog 本地提交 -> {sha[:8]}")
        return sha
    except Exception as exc:  # noqa: BLE001
        log(f"myBlog 本地提交失败（不影响发布）：{exc}", "WARN")
        return None


def _git(root: Path, *args: str, timeout: int = 60) -> subprocess.CompletedProcess:
    return subprocess.run(
        ["git", *args], cwd=root, capture_output=True, text=True, timeout=timeout
    )


def push_source_to_myblog(cfg: dict, message: str) -> tuple[str | None, str]:
    """把 myBlog 的本地提交推到远端，返回 (sha, 通道)。

    先试 git push：网络好的时候几十秒就过，且本地/远端历史一致，最干净。
    push 全失败才降级走 Git Data API，只把这次渲染出的源码文件送上去 —— 这样
    「发布成功但源码没上去」不会再发生。降级意味着远端多一个 API 提交、本地多
    一个还没推的提交，历史会分叉，所以打 WARN 提醒下次网络好时手动收拢。
    两条都不通就返回 (None, "failed")，不影响站点已经发布这件事。
    """
    root = Path(cfg["paths"]["myBlog"])
    branch = cfg["repos"]["myBlog"]["branch"]

    for attempt in (1, 2, 3):
        try:
            res = _git(root, "push", "origin", branch, timeout=120)
            if res.returncode == 0:
                sha = _git(root, "rev-parse", "HEAD", timeout=30).stdout.strip()
                log(f"myBlog 源码已 push -> {sha[:8]}")
                return sha, "git"
            log(f"myBlog push 第 {attempt} 次失败：{(res.stderr or res.stdout).strip()[:200]}", "WARN")
        except subprocess.TimeoutExpired:
            log(f"myBlog push 第 {attempt} 次超时（120s）", "WARN")
        except Exception as exc:  # noqa: BLE001
            log(f"myBlog push 第 {attempt} 次异常：{exc}", "WARN")

    # 降级：远端工作区是干净的，用 Git Data API 把源码文件直接写上去
    try:
        dirty = _git(root, "status", "--porcelain", "--untracked-files=no", timeout=30).stdout.strip()
        if dirty:
            log("myBlog 工作区不干净，跳过 API 降级（怕把半个提交推上去）", "WARN")
            return None, "failed"
        diff = _git(root, "diff", "--name-only", "origin/" + branch, "HEAD", timeout=60).stdout.split()
        if not diff:
            sha = _git(root, "rev-parse", "HEAD", timeout=30).stdout.strip()
            log("myBlog 远端已经是这个提交了", "WARN")
            return sha, "already"
        files = {p: (root / p).read_bytes() for p in diff if (root / p).exists()}
        repo = cfg["repos"]["myBlog"]
        res = gh.commit_files(repo["owner"], repo["name"], branch, files, message)
        log(
            f"myBlog 源码走 API 上去 -> {res['commit'][:8]}（{len(res['changed'])} 个文件）"
        )
        # API 提交和本地提交内容一致、只是历史不同。能 fetch 就把本地对齐过去，
        # 否则下次 push 会 non-fast-forward 直接失败。
        try:
            if _git(root, "fetch", "origin", branch, timeout=120).returncode == 0:
                _git(root, "reset", "--hard", f"origin/{branch}", timeout=60)
                log(f"myBlog 本地已对齐到远端 {res['commit'][:8]}")
                return res["commit"], "api"
        except Exception as exc:  # noqa: BLE001
            log(f"对齐本地失败（下次手跑 git fetch && git reset --hard origin/{branch}）：{exc}", "WARN")
        return res["commit"], "api"
    except Exception as exc:  # noqa: BLE001
        log(f"myBlog 源码两条通道都没上去：{exc}", "ERROR")
        return None, "failed"


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

    # 6. 源码提交到 myBlog 并推到远端（push 不通才降级 API）
    hexo_rel = f"source/_posts/{info['stem']}.md"
    src_sha = commit_local(cfg, [hexo_rel], msg)
    src_sha, src_channel = push_source_to_myblog(cfg, msg)

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
        "myBlog_source_channel": src_channel,
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
