#!/usr/bin/env python3
"""给 gh-pages 当前线上状态打备份 tag（本地 + 远端 API），首次全量重建前必跑。
用法: python3 scripts/backup.py [--apply]"""
from __future__ import annotations

import json
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
from common import load_config, run

sys.path.insert(0, str(Path(__file__).resolve().parent))
from github_api import create_tag


def main() -> None:
    apply = "--apply" in sys.argv
    cfg = load_config()
    tag = cfg["publish"]["backup_tag"]
    repo = cfg["repos"]["gh_pages"]
    local = Path(cfg["paths"][repo["local"]])
    sha = run(["git", "rev-parse", "HEAD"], cwd=local).stdout.strip()
    existing = run(["git", "tag", "-l", tag], cwd=local, check=False).stdout.strip()
    out = {"tag": tag, "local_head": sha, "local_tag_exists": bool(existing), "remote": "skipped"}
    if apply:
        if not existing:
            run(["git", "tag", tag, sha], cwd=local)
            out["local"] = "created"
        else:
            out["local"] = "already exists"
        try:
            out["remote"] = create_tag(repo["owner"], repo["name"], repo["branch"], tag)
        except Exception as exc:
            out["remote"] = f"failed: {exc}"
    print(json.dumps(out, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()
