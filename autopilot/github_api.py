"""GitHub Git Data API 的最小封装。只用标准库 + HTTPS，不依赖 git 协议。

本机到 github.com 的 git 协议基本不可用（`git fetch` 常年 curl 28 超时），
但 api.github.com 是通的，所以发布全部走这条线。
"""
from __future__ import annotations

import base64
import json
import os
import re
import time
import urllib.error
import urllib.parse
import urllib.request
from pathlib import Path

API = "https://api.github.com"


def token() -> str:
    for env in ("GH_TOKEN", "BLOG_PAT"):
        value = os.environ.get(env)
        if value:
            return value
    creds = Path.home() / ".git-credentials"
    if creds.exists():
        for line in creds.read_text().splitlines():
            m = re.match(r"https://[^:]+:([^@]+)@github\.com\s*$", line.strip())
            if m:
                return m.group(1)
    raise SystemExit("找不到 GitHub token：设 GH_TOKEN 或写 ~/.git-credentials")


def api(
    method: str,
    path: str,
    payload: dict | None = None,
    tries: int = 5,
    retry_4xx: bool = False,
):
    """带重试的 API 调用。返回解析后的 JSON；204 返回 None。

    本机 SSL 偶发 `SSLEOFError: EOF occurred in violation of protocol`，
    这类错误重试就好，不当失败。

    `retry_4xx` 只给建 blob 用：GitHub 偶尔对格式完全正确的 blob 请求回
    400 malformed request，同一条数据重发就好了（实测 27KB 的 HTML 会这样）。
    """
    body = json.dumps(payload).encode() if payload is not None else None
    last = None
    for i in range(tries):
        req = urllib.request.Request(
            API + path,
            data=body,
            method=method,
            headers={
                "Authorization": f"Bearer {token()}",
                "User-Agent": "blog-autopilot",
                "Accept": "application/vnd.github+json",
                "Content-Type": "application/json",
            },
        )
        try:
            with urllib.request.urlopen(req, timeout=90) as resp:
                raw = resp.read().decode()
                return json.loads(raw) if raw.strip() else None
        except urllib.error.HTTPError as exc:
            detail = exc.read().decode(errors="replace")[:400]
            # 4xx 一般是逻辑错误，重试没意义；只有 blob 会偶发假 400
            if 400 <= exc.code < 500 and not (retry_4xx and exc.code == 400):
                raise SystemExit(f"{method} {path} -> {exc.code}: {detail}")
            last = f"{exc.code}: {detail}"
        except Exception as exc:
            last = repr(exc)
        time.sleep(2 + i * 2)
    raise SystemExit(f"{method} {path} 失败（重试 {tries} 次）: {last}")


def repo_path(owner: str, name: str) -> str:
    return f"/repos/{owner}/{name}"


def head_commit(owner: str, name: str, branch: str) -> dict:
    ref = api("GET", f"{repo_path(owner, name)}/git/ref/heads/{branch}")
    return api("GET", f"{repo_path(owner, name)}/git/commits/{ref['object']['sha']}")


def create_blob(owner: str, name: str, data: bytes) -> str:
    res = api(
        "POST",
        f"{repo_path(owner, name)}/git/blobs",
        {"content": base64.b64encode(data).decode(), "encoding": "base64"},
        tries=6,
        retry_4xx=True,
    )
    return res["sha"]


def commit_files(
    owner: str,
    name: str,
    branch: str,
    files: dict[str, bytes],
    message: str,
    deletions: list[str] | None = None,
) -> dict:
    """在 branch 头部提交一批文件。files 是 {仓库内路径: 内容}。

    只创建真的变过的 blob：先拿 base tree，比对 sha 一致就跳过。
    返回 {commit, sha, changed, skipped}。
    """
    base = head_commit(owner, name, branch)
    base_sha = base["sha"]
    base_tree = base["tree"]["sha"]

    entries = []
    changed, skipped = [], []
    for path, data in sorted(files.items()):
        sha = create_blob(owner, name, data)
        entries.append({"path": path, "mode": "100644", "type": "blob", "sha": sha})
        changed.append(path)

    for path in deletions or []:
        entries.append({"path": path, "mode": "100644", "type": "blob", "sha": None})

    if not entries:
        return {"commit": base_sha, "changed": [], "skipped": skipped, "empty": True}

    tree = api(
        "POST",
        f"{repo_path(owner, name)}/git/trees",
        {"base_tree": base_tree, "tree": entries},
    )
    if tree["sha"] == base_tree:
        return {"commit": base_sha, "changed": [], "skipped": changed, "empty": True}

    commit = api(
        "POST",
        f"{repo_path(owner, name)}/git/commits",
        {"message": message, "tree": tree["sha"], "parents": [base_sha]},
    )
    api(
        "PATCH",
        f"{repo_path(owner, name)}/git/refs/heads/{branch}",
        {"sha": commit["sha"], "force": False},
    )
    return {"commit": commit["sha"], "changed": changed, "skipped": skipped, "empty": False}


def file_sha(owner: str, name: str, branch: str, path: str) -> str | None:
    """远端某个文件当前的 blob sha，不存在返回 None。"""
    try:
        res = api(
            "GET",
            f"{repo_path(owner, name)}/contents/{urllib.parse.quote(path)}?ref={branch}",
        )
    except SystemExit:
        return None
    return res.get("sha") if isinstance(res, dict) else None
