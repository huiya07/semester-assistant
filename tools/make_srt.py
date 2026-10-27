"""根据旁白文本与时间轴生成 SRT 字幕。

时间轴来自 synthetic 配音的 adelay 设置，与视频对齐。
每段按标点切句，按字数比例分配时长，保证字幕与语音大致同步。
"""

from __future__ import annotations

import os
import re
from pathlib import Path

# 输出目录可用环境变量指定，默认放在项目内的 local/（不进仓库）
OUT = Path(
    os.getenv("SRT_OUT_DIR", Path(__file__).resolve().parents[1] / "local")
) / "学期助手-字幕.srt"

# (开始秒, 结束秒, 文本)
SEGMENTS = [
    (0.0, 23.7,
     "这是一个学期助手。它解决一个很具体的问题：课程资料散在几十份 PDF 里，复习的时候常常记得老师讲过，却翻不到在第几页。"
     "它做两件事。第一，把课程资料变成能问答的助手，而且每一个答案都能点回原文的那一页。"
     "第二，把课表和作业放在同一条时间轴上，直接告诉你这周该做什么。"),
    (24.0, 46.9,
     "先加一份资料。上传之后，系统自动解析、按页切片、向量化入库。"
     "这里有两个刻意的设计。切片不跨页，因为引用必须能精确到某一页；"
     "切点优先落在句子结尾，实测按固定长度硬切的时候，九成的片段断在句子中间，改成优先断句之后，八成能完整结束。"),
    (50.0, 77.5,
     "现在问它一个问题：均值和中位数有什么区别。"
     "答案里每一个结论后面都带编号，点开就是命中的原文片段，还可以选择查看这一页的原貌，不是截取的片段，是完整的排版。"
     "这里用的是本地中文嵌入模型做检索，再交给大模型组织语言。"
     "检索的时候会优先取同一份资料的片段，因为多份资料混在一起，无关内容会把正确的那一条挤掉。"),
    (88.0, 107.7,
     "再问一个资料里没有的问题。它不会编，而是直接说没找到，并列出检索过哪些页。"
     "这背后有三层防线：检索距离太远就不调用大模型；提示词限制它只能用给定片段；"
     "输出之后还要校验引用编号，编造出来的编号会被判为无效。"),
    (110.0, 131.6,
     "除了资料，还有一条时间轴。这周有哪些课，哪些作业快到期，一目了然。"
     "课表和作业可以导入 JSON，换成你自己的。"
     "这一块是这个作品和普通知识库产品的分界：通用的文档问答工具没有今天是第几周这个概念，"
     "所以问不出下周的作业要用哪一章这种需要交叉的问题。"),
    (132.0, 151.5,
     "这个项目是用 AI 协作开发的。现在提一个真实需求：在回答下方显示耗时。"
     "它改了后端模块和界面代码，我刷新页面验证——每个答案下面多了耗时显示。"
     "这是一次完整的迭代：提需求、改代码、验收，这就是 AI 协同开发的实际过程。"),
    (156.0, 165.6,
     "从零开始，检索、问答、界面和学期视图都是这样一步步做出来的。"
     "开发过程的对话记录也一并保留在仓库里。"),
]


def split_sentences(text: str) -> list[str]:
    parts = re.split(r"(?<=[。！？；])", text)
    return [p.strip() for p in parts if p.strip()]


def wrap(text: str, limit: int = 22) -> list[str]:
    """按字数折行，两行以内。"""
    if len(text) <= limit:
        return [text]
    mid = len(text) // 2
    for i in range(mid, min(mid + 8, len(text) - 1)):
        if text[i] in "，、。":
            return [text[: i + 1], text[i + 1 :]]
    return [text[:mid], text[mid:]]


def ts(sec: float) -> str:
    h = int(sec // 3600)
    m = int(sec % 3600 // 60)
    s = sec % 60
    return f"{h:02d}:{m:02d}:{s:06.3f}".replace(".", ",")


def main() -> None:
    entries: list[tuple[float, float, str]] = []
    CHARS_PER_SEC = 4.5  # 中文 TTS 大致语速
    for start, end, text in SEGMENTS:
        sents = split_sentences(text)
        span = end - start
        # 先按语速算每句需要的时长，再等比缩放到该段的实际长度
        raw = [max(len(s) / CHARS_PER_SEC, 1.2) for s in sents]
        scale = span / sum(raw) if sum(raw) > span else 1.0
        cursor = start
        for s, d in zip(sents, raw):
            dur = d * scale if scale < 1 else d
            entries.append((cursor, min(cursor + dur, end), s))
            cursor += dur
        # 若按语速算完还没占满该段，剩下的时间留给最后一句
        if entries and cursor < end:
            a, _, t = entries[-1]
            entries[-1] = (a, end, t)

    lines: list[str] = []
    for i, (a, b, text) in enumerate(entries, 1):
        lines.append(str(i))
        lines.append(f"{ts(a)} --> {ts(b)}")
        lines.extend(wrap(text))
        lines.append("")

    OUT.parent.mkdir(parents=True, exist_ok=True)
    OUT.write_text("\n".join(lines), encoding="utf-8")
    print(f"已生成 {OUT}（{len(entries)} 条字幕）")


if __name__ == "__main__":
    main()
