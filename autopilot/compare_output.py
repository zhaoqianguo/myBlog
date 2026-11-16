#!/usr/bin/env python3
"""比对本地 public/ 与远端 gh-pages 的产物树，按 git blob sha 逐个文件比较。

用法: python3 compare_output.py [--local-only]

git 协议在本机不稳，这里只用 HTTPS API + 重试。
"""
from __future__ import annotations

import hashlib
import json
import os
import re
import sys
import time
import urllib.request
from pathlib import Path

OWNER = "zhaoqianguo"
REPO = "zhaoqianguo.github.io"
BRANCH = "gh-pages"
API = "https://api.github.com"


def token() -> str:
    for env in ("GH_TOKEN", "BLOG_PAT"):
        if os.environ.get(env):
            return os.environ[env]
    creds = Path.home() / ".git-credentials"
    if creds.exists():
        for line in creds.read_text().splitlines():
            m = re.match(r"https://[^:]+:([^@]+)@github\.com\s*$", line.strip())
            if m:
                return m.group(1)
    raise SystemExit("找不到 GitHub token")


def api(path: str, tries: int = 5) -> dict:
    last = None
    for i in range(tries):
        try:
            req = urllib.request.Request(
                API + path,
                headers={
                    "Authorization": f"Bearer {token()}",
                    "User-Agent": "blog-autopilot",
                    "Accept": "application/vnd.github+json",
                },
            )
            with urllib.request.urlopen(req, timeout=90) as resp:
                return json.loads(resp.read().decode())
        except Exception as exc:  # 网络抖动是常态，不是错误
            last = exc
            time.sleep(2 + i * 2)
    raise SystemExit(f"API 请求失败: {last}")


def blob_sha(data: bytes) -> str:
    h = hashlib.sha1()
    h.update(b"blob %d\0" % len(data))
    h.update(data)
    return h.hexdigest()


def remote_tree() -> dict[str, str]:
    tree = api(f"/repos/{OWNER}/{REPO}/git/trees/{BRANCH}?recursive=1")
    return {x["path"]: x["sha"] for x in tree["tree"] if x["type"] == "blob"}


def local_tree(root: Path) -> dict[str, str]:
    return {
        str(f.relative_to(root)): blob_sha(f.read_bytes())
        for f in root.rglob("*")
        if f.is_file()
    }


def main() -> None:
    root = Path(sys.argv[2]) if len(sys.argv) > 2 else Path("public")
    local = local_tree(root)
    remote = remote_tree()

    same = [p for p in local if remote.get(p) == local[p]]
    diff = sorted(p for p in local if p in remote and remote[p] != local[p])
    new = sorted(p for p in local if p not in remote)
    gone = sorted(p for p in remote if p not in local)

    print(f"local={len(local)} remote={len(remote)} same={len(same)} "
          f"diff={len(diff)} new={len(new)} remote_only={len(gone)}")
    for label, items in (("diff", diff), ("new", new), ("remote_only", gone)):
        if items:
            print(f"\n{label}:")
            for p in items:
                print("  " + p)


if __name__ == "__main__":
    main()
