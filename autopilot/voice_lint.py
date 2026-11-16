#!/usr/bin/env python3
"""去 AI 味自检。用法: python3 voice_lint.py <draft.md>

退出码 0=通过，1=不通过。输出 JSON 便于自动化消费。
判据是「有没有一手事实 + 结构像不像人」，不是「词表干净」。
"""
from __future__ import annotations

import json
import re
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
from common import load_config, parse_draft

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
# 元叙述：写了「我怎么查的」而不是「查到了什么」。读者不关心过程。
META_NARRATION = [
    "母本", "参考自", "我查了", "我翻了", "资料显示", "我抄", "先记着",
    "本文参考", "翻译自", "原文链接见下",
]
TUTORIAL_TITLE_WORDS = ["教程", "速查", "指南", "全网最全", "保姆级"]


def _strip_code(body: str) -> str:
    """去掉代码块和行内代码，剩下的才是叙述文字。"""
    out = re.sub(r"```.*?```", "", body, flags=re.S)
    out = re.sub(r"`[^`\n]*`", "", out)
    return out


def _split_references(body: str) -> tuple[str, str]:
    """把文末的「参考」小节切出去。

    那一节本来就该出现英文原文标题和「编译自」，不能拿正文的尺子量它。
    """
    m = re.search(r"^##\s*参\s*考\s*$", body, re.M)
    if not m:
        return body, ""
    return body[: m.start()], body[m.start():]


def lint(path: Path) -> dict:
    draft = parse_draft(Path(path))
    body_full = draft["body"]
    # 文末「参考」是出处清单，不是正文。整节切出去，不参与正文判据。
    body, _refs = _split_references(body_full)
    title = draft.get("title", "")
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

    for w in META_NARRATION:
        if w in body:
            violations.append(f"元叙述（写了查找过程而不是结论）: {w}")

    if len(title) > 24:
        violations.append(f"标题 {len(title)} 字，超过 24 字上限")
    for w in TITLE_BANNED:
        if w in title:
            violations.append(f"标题党句式: {w}")
    for w in TUTORIAL_TITLE_WORDS:
        if w in title:
            violations.append(f"教程腔标题词: {w}")

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
    long_p = sum(1 for p in plain if len(p) > 120)
    if short < 2:
        violations.append(f"只有 {short} 个短段落（单句成段），要求至少 2 个")
    if long_p < 1:
        violations.append("没有超过 120 字的长段落，段落太齐整像模板")

    h2 = len(re.findall(r"^##\s+", body, re.M))
    if h2 >= 4 and len(set(round(len(p) / 20) for p in plain)) <= 2:
        violations.append("四段以上 H2 且段落长度高度一致，疑似 AI 三段式")

    # 一手事实：必须有真实代码或命令行痕迹，光有版本号不算
    has_code_block = "```" in body
    has_inline_code = bool(re.search(r"`[^`\n]{2,}`", body))
    if not (has_code_block or has_inline_code):
        violations.append("没有任何代码片段或命令，撑不起「我真跑过」这条")

    if not re.search(r"\d+\.\d+", body):
        warnings.append("正文里没出现版本号（v22.22.1 之类），建议补一处")

    if re.search(r"[\U0001F300-\U0001FAFF\u2600-\u27BF]", body):
        violations.append("正文含 emoji")
    if body.count("——") > 1:
        violations.append(f"中文破折号出现 {body.count('——')} 次，最多 1 次")
    if re.search(r"不仅.{0,12}而且", body):
        violations.append("出现「不仅…而且…」对仗句")

    if body.rstrip().endswith("（完）"):
        violations.append("教程式收尾「（完）」，写完就停")

    numbered_h2 = len(
        re.findall(r"^##\s*(?:[一二三四五六七八九十]+、|\d+[.、])\s*", body, re.M)
    )
    if numbered_h2 >= 3:
        violations.append(f"编号 H2 有 {numbered_h2} 个，教程骨架太重")

    # 翻译腔：叙述文字里连续 12 个以上英文单词（不是术语）
    prose = _strip_code(body)
    for m in re.finditer(r"(?:[A-Za-z][A-Za-z'-]*[ ,]+){12,}", prose):
        snippet = m.group(0).strip()
        violations.append(f"疑似整句英文未译: {snippet[:50]}…")
        break

    chars = len(re.sub(r"\s", "", _strip_code(body)))
    if chars < cfg["min_chars"]:
        warnings.append(f"叙述文字约 {chars} 字，低于建议下限 {cfg['min_chars']}")
    if chars > cfg["max_chars"]:
        warnings.append(f"叙述文字约 {chars} 字，超过建议上限 {cfg['max_chars']}")

    return {
        "pass": not violations,
        "title": title,
        "violations": violations,
        "warnings": warnings,
        "stats": {
            "chars": chars,
            "paragraphs": len(paras),
            "short_paragraphs": short,
            "long_paragraphs": long_p,
            "first_person": n_me,
            "h2": h2,
            "has_code_block": has_code_block,
        },
    }


if __name__ == "__main__":
    if len(sys.argv) < 2:
        print(json.dumps(
            {"pass": False, "violations": ["用法: voice_lint.py <draft.md>"]},
            ensure_ascii=False,
        ))
        sys.exit(2)
    try:
        result = lint(Path(sys.argv[1]))
    except Exception as exc:
        result = {"pass": False, "violations": [f"解析失败: {exc}"]}
    print(json.dumps(result, ensure_ascii=False, indent=2))
    sys.exit(0 if result["pass"] else 1)
