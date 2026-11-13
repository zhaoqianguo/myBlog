"""GitHub REST / Git Data API 发布通道。
git 协议被代理挡住时，用一次 tree + commit + ref 更新把多个文本文件推上去。
token 优先取 GH_TOKEN / BLOG_PAT 环境变量（CI），回落本机 ~/.git-credentials。
不落盘、不打印。仅依赖标准库。"""
from __future__ import annotations

import json
import os
import re
import urllib.error
import urllib.request
from pathlib import Path

API = "https://api.github.com"


def load_tokens() -> list[str]:
    out: list[str] = []
    env_token = os.environ.get("GH_TOKEN") or os.environ.get("BLOG_PAT")
    if env_token:
        out.append(env_token)
    p = Path.home() / ".git-credentials"
    if p.exists():
        for line in p.read_text(encoding="utf-8", errors="ignore").splitlines():
            m = re.match(r"https://[^:]+:([^@]+)@github\.com\s*$", line.strip())
            if m and m.group(1) not in out:
                out.append(m.group(1))
    if not out:
        raise RuntimeError("没有可用 token（GH_TOKEN / BLOG_PAT / ~/.git-credentials）")
    return out


def api(method: str, path: str, payload: dict | None = None, timeout: int = 60) -> dict:
    data = json.dumps(payload, ensure_ascii=False).encode("utf-8") if payload is not None else None
    last: Exception | None = None
    for token in load_tokens():
        req = urllib.request.Request(
            API + path,
            data=data,
            method=method,
            headers={
                "Authorization": f"Bearer {token}",
                "Accept": "application/vnd.github+json",
                "Content-Type": "application/json",
                "User-Agent": "blog-autopilot",
                "X-GitHub-Api-Version": "2022-11-28",
            },
        )
        try:
            with urllib.request.urlopen(req, timeout=timeout) as resp:
                raw = resp.read().decode("utf-8")
                return json.loads(raw) if raw.strip() else {}
        except urllib.error.HTTPError as exc:
            detail = exc.read().decode("utf-8", errors="ignore")[:300]
            last = RuntimeError(f"{method} {path} -> HTTP {exc.code}: {detail}")
            if exc.code in (401, 403, 404):
                continue
            raise last
        except Exception as exc:
            last = exc
    raise last if last else RuntimeError("API 请求失败")


def head_sha(owner: str, repo: str, branch: str) -> str:
    return api("GET", f"/repos/{owner}/{repo}/git/ref/heads/{branch}")["object"]["sha"]


def commit_files(owner: str, repo: str, branch: str, files: dict[str, str], message: str) -> str:
    """把 {仓库内相对路径: 文本内容} 作为一次 commit 推到指定分支。"""
    if not files:
        raise ValueError("没有要提交的文件")
    base_sha = head_sha(owner, repo, branch)
    base_tree = api("GET", f"/repos/{owner}/{repo}/git/commits/{base_sha}")["tree"]["sha"]
    items = [
        {"path": p, "mode": "100644", "type": "blob", "content": c}
        for p, c in sorted(files.items())
    ]
    tree_sha = base_tree
    for i in range(0, len(items), 40):
        res = api(
            "POST",
            f"/repos/{owner}/{repo}/git/trees",
            {"base_tree": tree_sha, "tree": items[i : i + 40]},
        )
        tree_sha = res["sha"]
    new_commit = api(
        "POST",
        f"/repos/{owner}/{repo}/git/commits",
        {"message": message, "tree": tree_sha, "parents": [base_sha]},
    )
    api("PATCH", f"/repos/{owner}/{repo}/git/refs/heads/{branch}", {"sha": new_commit["sha"]})
    return new_commit["sha"]


def create_tag(owner: str, repo: str, branch: str, tag: str) -> str:
    sha = head_sha(owner, repo, branch)
    ref = f"refs/tags/{tag}"
    try:
        api("POST", f"/repos/{owner}/{repo}/git/refs", {"ref": ref, "sha": sha})
        return f"created {ref} -> {sha[:8]}"
    except RuntimeError as exc:
        if "422" in str(exc):
            return f"{ref} 已存在，跳过"
        raise


if __name__ == "__main__":
    import sys

    who = api("GET", "/user")
    print(f"认证成功: {who.get('login')}")
    if len(sys.argv) > 1 and sys.argv[1] == "--check":
        print("gh-pages HEAD:", head_sha("zhaoqianguo", "zhaoqianguo.github.io", "gh-pages")[:8])
        print("main HEAD:", head_sha("zhaoqianguo", "astro-blog", "main")[:8])
