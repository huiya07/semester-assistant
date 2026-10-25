"""把本项目的 AI 对话导出成可交付的快照（比赛要求「AI 对话历史导出」）。

处理原则：
1. 只取 user / assistant 的**文本**，工具调用与结果一律丢掉（体积大且无意义）
2. 脱敏：API key、报名 UID、手机号、绝对路径、学校名、班级号
3. 截断过长的回复，保证文件可读（评委要能翻）
4. 不做筛选式「美化」：保留对话原样，包括失败与返工

用法：
    uv run python tools/export_prompt_history.py <session.jsonl> [输出路径]
"""

from __future__ import annotations

import json
import re
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
DEFAULT_SRC = (
    Path.home()
    / ".claude"
    / "projects"
    / "C--Users-maybe"
    / "6d3fe149-eabe-44d7-8fca-e4b10c078e13.jsonl"
)
OUT = ROOT / "docs" / "prompts" / "raw" / "session-2026-10-25.md"

MAX_ASSISTANT_CHARS = 400  # 回复过长只留开头，避免文件膨胀

# 这些是系统注入的内容，不是人和 AI 的对话，一律跳过
SKIP_PREFIXES = (
    "Base directory for this skill:",
    "Caveat:",
    "You have superpowers",
    "<system-reminder>",
    "This session is being continued",
    "[Request interrupted",
)

REDACTIONS = [
    (re.compile(r"sk-[A-Za-z0-9]{16,}"), "[REDACTED_KEY]"),
    (re.compile(r"2119569"), "[UID]"),
    (re.compile(r"1[3-9]\d{9}"), "[手机号]"),
    (re.compile(r"[A-Za-z]:\\Users\\maybe\\[^\s\"'，。）]*"), "<本地路径>"),
    (re.compile(r"[A-Za-z]:\\maybe\\[^\s\"'，。）]*"), "<本地路径>"),
    (re.compile(r"西安职业技术学院"), "<学校>"),
    (re.compile(r"AI26102"), "<班级>"),
    (re.compile(r"huiya07"), "<GitHub用户名>"),
]

IMAGE_PLACEHOLDER = re.compile(r"\[Image: source:.*?\]", re.DOTALL)


def redact(text: str) -> str:
    text = IMAGE_PLACEHOLDER.sub("[用户发送了一张截图（本文档不含图片）]", text)
    for pattern, repl in REDACTIONS:
        text = pattern.sub(repl, text)
    return text


def content_text(message: dict) -> str:
    """只取文本块，丢弃 tool_use / tool_result / image。"""
    c = message.get("content")
    if isinstance(c, str):
        return c.strip()
    if not isinstance(c, list):
        return ""
    parts = [
        b.get("text", "")
        for b in c
        if isinstance(b, dict) and b.get("type") == "text"
    ]
    return "\n".join(p for p in parts if p).strip()


def main() -> None:
    src = Path(sys.argv[1]) if len(sys.argv) > 1 else DEFAULT_SRC
    out = Path(sys.argv[2]) if len(sys.argv) > 2 else OUT
    if not src.exists():
        raise SystemExit(f"找不到会话文件：{src}")

    turns: list[tuple[str, str, str]] = []  # (timestamp, role, text)
    with src.open(encoding="utf-8") as f:
        for line in f:
            try:
                d = json.loads(line)
            except json.JSONDecodeError:
                continue
            if d.get("type") not in ("user", "assistant"):
                continue
            text = content_text(d.get("message", {}))
            if not text:
                continue
            # 跳过系统注入与命令包装
            if text.startswith(SKIP_PREFIXES):
                continue
            if text.startswith("<") and text.endswith(">"):
                continue
            role = d["type"]
            if role == "assistant" and len(text) > MAX_ASSISTANT_CHARS:
                text = text[:MAX_ASSISTANT_CHARS].rstrip() + "…（后略）"
            turns.append((d.get("timestamp", "")[:19], role, redact(text)))

    lines = [
        "# AI 对话历史（节选）",
        "",
        "> 本项目全程以「人定义意图、AI 生成实现、人验收纠偏」的方式开发。",
        "> 以下为该会话的对话快照，已脱敏（密钥、UID、手机号、本地路径、学校与班级、GitHub 用户名），",
        "> 并省略了工具调用与命令输出，只保留对话文本。原对话中的截图未包含在本文档内。",
        "",
        f"**统计：** {len(turns)} 轮（user {sum(1 for t in turns if t[1]=='user')} / "
        f"assistant {sum(1 for t in turns if t[1]=='assistant')}）",
        "",
        "---",
        "",
    ]
    for ts, role, text in turns:
        who = "🧑 用户" if role == "user" else "🤖 AI"
        lines.append(f"### {who} · {ts}")
        lines.append("")
        lines.append(text)
        lines.append("")

    out.parent.mkdir(parents=True, exist_ok=True)
    out.write_text("\n".join(lines), encoding="utf-8")
    kb = out.stat().st_size / 1024
    print(f"已生成 {out}（{kb:.0f} KB，{len(turns)} 轮）")


if __name__ == "__main__":
    main()
