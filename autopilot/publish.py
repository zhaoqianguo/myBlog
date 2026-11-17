#!/usr/bin/env python3
"""发布一篇：草稿 → 文风闸门 → 渲染两端 → 推 myBlog(master) 与 astro(main)，部署交给线上。

    python3 publish.py --date 2026-11-17            # 正常发布
    python3 publish.py --date 2026-11-17 --dry-run  # 只跑闸门 + 本地构建自检，不推
    python3 publish.py --check                      # 只看今天该不该发、发了没
    python3 publish.py --verify --date 2026-11-17    # 查线上 Actions / gh-pages / Vercel 成没成

两条部署路径都不在本地做：
- myBlog master push 后由 .github/workflows/deploy.yml 构建并推 zhaoqianguo.github.io 的 gh-pages；
- astro-blog main push 后由 Vercel 自动构建部署。

本地只做两件事：把源码提交推上去、用 hexo 本地构建一次做自检（0 字节页面直接拦下）。
这样做的好处是发布不再依赖本机网络稳定 —— 本机只要能把提交送出去就行。
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
    parse_plan,
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
    # 也接受带标题后缀的草稿：2026-11-17-微任务队列在哪一步清空.md
    hits = sorted((ROOT / "drafts").glob(f"{d.isoformat()}-*.md"))
    return hits[0] if hits else None


def _git(root: Path, *args: str, timeout: int = 60) -> subprocess.CompletedProcess:
    return subprocess.run(
        ["git", *args], cwd=root, capture_output=True, text=True, timeout=timeout
    )


def run_hexo(cfg: dict) -> Path:
    """本地构建一次，纯粹为了自检。产物不推，推的是 GitHub Actions 构建的那份。"""
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

    # 新文章该生成的页面必须存在，否则说明 frontmatter 又出问题了
    return public


def push_with_fallback(root: Path, repo: dict, files_hint: list[str], message: str) -> tuple[str | None, str]:
    """先 git push，不通降级 Git Data API。返回 (sha, 通道)。"""
    branch = repo["branch"]
    for attempt in (1, 2, 3):
        try:
            res = _git(root, "push", "origin", branch, timeout=120)
            if res.returncode == 0:
                sha = _git(root, "rev-parse", "HEAD", timeout=30).stdout.strip()
                log(f"{repo['name']} 已 push -> {sha[:8]}")
                return sha, "git"
            log(f"{repo['name']} push 第 {attempt} 次失败：{(res.stderr or res.stdout).strip()[:200]}", "WARN")
        except subprocess.TimeoutExpired:
            log(f"{repo['name']} push 第 {attempt} 次超时（120s）", "WARN")
        except Exception as exc:  # noqa: BLE001
            log(f"{repo['name']} push 第 {attempt} 次异常：{exc}", "WARN")

    # 降级：远端工作区是干净的，用 Git Data API 把这次的文件直接写上去
    try:
        dirty = _git(root, "status", "--porcelain", "--untracked-files=no", timeout=30).stdout.strip()
        if dirty:
            log(f"{repo['name']} 工作区不干净，跳过 API 降级（怕把半个提交推上去）", "WARN")
            return None, "failed"
        diff = _git(root, "diff", "--name-only", "origin/" + branch, "HEAD", timeout=60).stdout.split()
        diff = diff or files_hint
        if not diff:
            sha = _git(root, "rev-parse", "HEAD", timeout=30).stdout.strip()
            log(f"{repo['name']} 远端已经是这个提交了", "WARN")
            return sha, "already"
        files = {p: (root / p).read_bytes() for p in diff if (root / p).exists()}
        res = gh.commit_files(repo["owner"], repo["name"], branch, files, message)
        log(f"{repo['name']} 走 API 上去 -> {res['commit'][:8]}（{len(res['changed'])} 个文件）")
        # API 提交与本地提交内容一致、历史不同。能 fetch 就对齐，否则下次 push 会 non-fast-forward
        try:
            if _git(root, "fetch", "origin", branch, timeout=120).returncode == 0:
                _git(root, "reset", "--hard", f"origin/{branch}", timeout=60)
                log(f"{repo['name']} 本地已对齐到远端 {res['commit'][:8]}")
        except Exception as exc:  # noqa: BLE001
            log(f"{repo['name']} 对齐本地失败（下次手跑 git fetch && git reset --hard）：{exc}", "WARN")
        return res["commit"], "api"
    except Exception as exc:  # noqa: BLE001
        log(f"{repo['name']} 两条通道都没上去：{exc}", "ERROR")
        return None, "failed"


def commit_local(cfg: dict, paths: list[str], message: str) -> str | None:
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
        (
            e
            for e in load_ledger().get("entries", [])
            if e.get("date") == d.isoformat() and e.get("status") in ("pushed", "published")
        ),
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

    # 2. 渲染两端（写进两个仓库的工作区）
    info = render.write_outputs(src, d, cfg)
    log(f"渲染完成：{info['stem']}")
    log(f"  显示时间 {info['pub_datetime']}")

    hexo_rel = f"source/_posts/{info['stem']}.md"
    astro_rel = f"src/content/blog/{info['stem']}.md"

    # 3. 本地构建自检：0 字节页面、目标文章页没生成，都当场拦下
    public = run_hexo(cfg)
    expected = [p for p in public.rglob("index.html") if info["slug"] in str(p)]
    if not expected:
        raise SystemExit(f"构建完了却没找到这篇文章的页面（slug={info['slug']}），检查 frontmatter")

    if dry_run:
        log(f"dry-run：渲染了 {hexo_rel} 与 {astro_rel}，本地构建 OK（{len(expected)} 个页面）")
        # dry-run 只做自检，不许在仓库里留改动：把刚写进去的两份文件还原
        for root, rel in (
            (Path(cfg["paths"]["myBlog"]), hexo_rel),
            (Path(cfg["paths"]["astro"]), astro_rel),
        ):
            if (root / ".git").exists():
                _git(root, "checkout", "--", rel, timeout=60)
        return {"dry_run": True, "would_push": [hexo_rel, astro_rel], **info}

    msg = cfg["publish"]["commit_message"].format(title=info["title"], date=d.isoformat())

    # 4. 源文进 myBlog 并推到 master —— 推上去之后 GitHub Actions 构建并部署
    commit_local(cfg, [hexo_rel], msg)
    src_sha, src_channel = push_with_fallback(
        Path(cfg["paths"]["myBlog"]), cfg["repos"]["myBlog"], [hexo_rel], msg
    )

    # 5. astro 正文提交到 main —— 推上去之后 Vercel 自己构建部署
    astro_root = Path(cfg["paths"]["astro"])
    astro_repo = cfg["repos"]["astro"]
    astro_bytes = Path(info["astro_path"]).read_bytes()  # 先存下来，reset 会冲掉工作区
    committed = False
    if (astro_root / ".git").exists():
        # 先对齐本地，免得带着上次残留的脏文件去提交
        try:
            if _git(astro_root, "fetch", "origin", astro_repo["branch"], timeout=120).returncode == 0:
                _git(astro_root, "reset", "--hard", f"origin/{astro_repo['branch']}", timeout=60)
        except Exception as exc:  # noqa: BLE001
            log(f"astro 本地对齐失败（走 API 也行）：{exc}", "WARN")
        # 把同一份字节写回去。不能重渲 —— 重渲会拿到新的 pub_datetime，两边就对不上了
        target = astro_root / astro_rel
        target.parent.mkdir(parents=True, exist_ok=True)
        target.write_bytes(astro_bytes)
        _git(astro_root, "add", "--", astro_rel, timeout=60)
        res = _git(astro_root, "commit", "-m", msg, timeout=60)
        committed = res.returncode == 0
        if not committed:
            log(f"astro 本地没提交（{res.stdout.strip() or res.stderr.strip()}），改走 API", "WARN")

    if committed:
        astro_sha, astro_channel = push_with_fallback(astro_root, astro_repo, [astro_rel], msg)
    else:
        # 本地这条走不通就直接 API 写远端，别让 push 白跑一趟报个假的 sha
        try:
            res = gh.commit_files(
                astro_repo["owner"], astro_repo["name"], astro_repo["branch"],
                {astro_rel: astro_bytes}, msg,
            )
            astro_sha, astro_channel = res["commit"], "api"
            log(f"astro 走 API 上去 -> {astro_sha[:8]}")
        except Exception as exc:  # noqa: BLE001
            log(f"astro 两条通道都没上去：{exc}", "ERROR")
            astro_sha, astro_channel = None, "failed"
    log(f"astro -> {astro_sha[:8] if astro_sha else 'failed'}")

    # 6. 记账
    ledger = load_ledger()
    entry = {
        "date": d.isoformat(),
        "slug": info["slug"],
        "title": info["title"],
        "pub_datetime": info["pub_datetime"],
        "status": "pushed",
        "myBlog_source_sha": src_sha,
        "myBlog_source_channel": src_channel,
        "astro_sha": astro_sha,
        "astro_channel": astro_channel,
        "deploy": {"myBlog": "actions", "astro": "vercel"},
        "lint": {"chars": lint["stats"]["chars"], "warnings": lint["warnings"]},
    }
    ledger.setdefault("entries", [])
    ledger["entries"] = [e for e in ledger["entries"] if e.get("date") != d.isoformat()]
    ledger["entries"].append(entry)
    ledger["entries"].sort(key=lambda e: e["date"])
    save_ledger(ledger)

    update_plan_status(d, "已推送·等部署")
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


def verify(cfg: dict, d: Date) -> dict:
    """查这一天推上去之后，线上到底构建成没成。只读，不改任何东西。"""
    entry = next((e for e in load_ledger().get("entries", []) if e.get("date") == d.isoformat()), None)
    out: dict = {"date": d.isoformat(), "ledger": entry}

    # myBlog：Actions 那次 run 成没成
    try:
        runs = gh.api("GET", f"{gh.repo_path('zhaoqianguo', 'myBlog')}/actions/runs?per_page=5")["workflow_runs"]
        mine = [r for r in runs if entry and r["head_sha"].startswith((entry.get("myBlog_source_sha") or "\0")[:8])]
        run = mine[0] if mine else runs[0]
        out["actions"] = {
            "id": run["id"], "status": run["status"], "conclusion": run["conclusion"],
            "head_sha": run["head_sha"][:8], "url": run["html_url"],
        }
    except Exception as exc:  # noqa: BLE001
        out["actions"] = {"error": str(exc)}

    # gh-pages：产物仓库的 head
    try:
        repo = cfg["repos"]["gh_pages"]
        ref = gh.api("GET", f"{gh.repo_path(repo['owner'], repo['name'])}/git/ref/heads/{repo['branch']}")
        c = gh.api("GET", f"{gh.repo_path(repo['owner'], repo['name'])}/commits/{ref['object']['sha']}")
        out["gh_pages"] = {"sha": c["sha"][:8], "date": c["commit"]["author"]["date"],
                           "message": c["commit"]["message"].splitlines()[0][:60]}
    except Exception as exc:  # noqa: BLE001
        out["gh_pages"] = {"error": str(exc)}

    # astro：commit status 里的 Vercel context
    try:
        st = gh.api("GET", f"{gh.repo_path('zhaoqianguo', 'astro-blog')}/commits/main/status")
        out["vercel"] = {s["context"]: s["state"] for s in st.get("statuses", [])}
    except Exception as exc:  # noqa: BLE001
        out["vercel"] = {"error": str(exc)}

    out["ok"] = (
        out.get("actions", {}).get("conclusion") == "success"
        and out.get("vercel", {}).get("Vercel") in ("success", "pending")
        and "error" not in out.get("gh_pages", {})
    )
    return out


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--date")
    ap.add_argument("--dry-run", action="store_true")
    ap.add_argument("--check", action="store_true")
    ap.add_argument("--verify", action="store_true", help="查这一天的线上部署成没成")
    ap.add_argument("--force", action="store_true", help="当天已发过也重发一遍")
    args = ap.parse_args()

    cfg = load_config()

    if args.check:
        print(json.dumps(check(cfg), ensure_ascii=False, indent=2))
        return 0

    d = Date.fromisoformat(args.date) if args.date else today(cfg)

    if args.verify:
        out = verify(cfg, d)
        print(json.dumps(out, ensure_ascii=False, indent=2))
        return 0 if out["ok"] else 1

    entry = publish(d, cfg, args.dry_run, args.force)
    print(json.dumps(entry, ensure_ascii=False, indent=2))
    return 0


if __name__ == "__main__":
    sys.exit(main())
