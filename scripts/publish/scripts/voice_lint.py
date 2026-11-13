#!/usr/bin/env python3
"""去 AI 味自检。用法: python3 scripts/voice_lint.py <draft.md>
退出码 0=通过, 1=不通过。输出 JSON 便于自动化消费。"""
from __future__ import annotations

import json
import re
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
from common import parse_draft, load_config

BANNED = [
    "首先", "其次", "再者", "总而言之", "综上所述", "总的来说", "在当今",
    "随着", "值得一提的是", "值得注意的是", "众所周知", "不难发现", "显而易见",
    "深入浅出", "一文搞懂", "详解", "最佳实践", "赋能", "闭环", "抓手",
    "全方位", "多维度", "助力", "极大提升", "让我们一起", "希望通过本文",
    "本文将带您", "欢迎留言", "欢迎交流", "希望能帮到你", "希望这篇文章",
    "有所帮助", "点赞关注", "在现代", "不可或缺的一部分",
]
TITLE_BANNED = [
    "一文搞懂", "深入浅出", "彻底搞懂", "万字长文", "从入门到精通",
    "最佳实践", "全网最全", "保姆级",
]
SUMMARY_HEADINGS = ["总结", "结语", "小结", "写在最后", "总的来说", "后记", "感想"]
CLOSING_CLICHES = [
    "希望能帮到你", "欢迎留言", "欢迎交流", "希望这篇文章", "有所帮助",
    "点赞", "关注我", "下期再见", "如果觉得有用",
]


def lint(path: Path) -> dict:
    draft = parse_draft(Path(path))
    body = draft["body"]
    title = draft["title"]
    cfg = load_config()["writing"]
    violations: list[str] = []
    warnings: list[str] = []

    if not title:
        violations.append("缺少 title")

    n_me = len(re.findall(r"我", body))
    if n_me < 3:
        violations.append(f"第一人称「我」只有 {n_me} 处，硬规则要求至少 3 处")

    for w in BANNED:
        if w in body or w in title:
            violations.append(f"禁用词: {w}")

    if len(title) > 24:
        violations.append(f"标题 {len(title)} 字，超过 24 字上限")
    for w in TITLE_BANNED:
        if w in title:
            violations.append(f"标题党句式: {w}")

    tail = body[-180:]
    for w in CLOSING_CLICHES:
        if w in tail:
            violations.append(f"结尾套话: {w}")

    for h in re.findall(r"^#{1,3}\s+(.+)$", body, re.M):
        if any(k in h for k in SUMMARY_HEADINGS):
            violations.append(f"出现总结型小标题: {h.strip()}")

    paras = [p.strip() for p in re.split(r"\n\s*\n", body) if p.strip()]
    plain = [p for p in paras if not p.startswith(("```", "|", "#", "-", ">"))]
    short = sum(1 for p in plain if len(p) < 40)
    long = sum(1 for p in plain if len(p) > 120)
    if short < 2:
        violations.append(f"只有 {short} 个短段落（单句成段），要求至少 2 个")
    if long < 1:
        violations.append("没有超过 120 字的长段落，段落太齐整像模板")

    h2 = len(re.findall(r"^##\s+", body, re.M))
    if h2 >= 4 and len(set(round(len(p) / 20) for p in plain)) <= 2:
        violations.append("四段以上 H2 且段落长度高度一致，疑似 AI 三段式")

    concrete = bool(re.search(r"`[^`]{2,}`", body)) or bool(
        re.search(r"\b(v?\d+\.\d+(?:\.\d+)?|node|npm|pnpm|hexo|astro|git)\b", body, re.I)
    )
    if not concrete:
        violations.append("没有任何具体细节（版本号 / 命令 / 反引号代码片段）")

    if re.search(r"[\U0001F300-\U0001FAFF\u2600-\u27BF]", body):
        violations.append("正文含 emoji")
    if body.count("——") > 1:
        violations.append(f"中文破折号出现 {body.count('——')} 次，最多 1 次")
    if re.search(r"不仅.{0,12}而且", body):
        violations.append("出现「不仅…而且…」对仗句")

    # 外部博主只借笔触，不借教程骨架（见 STYLE_CORPUS.md 末节）
    if body.rstrip().endswith("（完）"):
        violations.append("教程式收尾「（完）」，本站写完就停")
    numbered_h2 = len(
        re.findall(r"^##\s*(?:[一二三四五六七八九十]+、|\d+[.、])\s*", body, re.M)
    )
    if numbered_h2 >= 3:
        violations.append(f"编号 H2 有 {numbered_h2} 个，教程骨架太重，本站不是教程")
    for w in ("教程", "速查", "指南", "全网最全", "保姆级"):
        if w in title:
            violations.append(f"教程腔标题词: {w}")

    chars = len(re.sub(r"\s", "", body))
    if chars < cfg["min_chars"]:
        warnings.append(f"正文约 {chars} 字，低于建议下限 {cfg['min_chars']}")
    if chars > cfg["max_chars"]:
        warnings.append(f"正文约 {chars} 字，超过建议上限 {cfg['max_chars']}")

    return {
        "pass": not violations,
        "title": title,
        "violations": violations,
        "warnings": warnings,
        "stats": {
            "chars": chars,
            "paragraphs": len(paras),
            "short_paragraphs": short,
            "long_paragraphs": long,
            "first_person": n_me,
            "h2": h2,
        },
    }


if __name__ == "__main__":
    if len(sys.argv) < 2:
        print(json.dumps({"pass": False, "violations": ["用法: voice_lint.py <draft.md>"]}, ensure_ascii=False))
        sys.exit(2)
    try:
        result = lint(Path(sys.argv[1]))
    except Exception as exc:
        result = {"pass": False, "violations": [f"解析失败: {exc}"]}
    print(json.dumps(result, ensure_ascii=False, indent=2))
    sys.exit(0 if result["pass"] else 1)
