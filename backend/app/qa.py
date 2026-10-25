"""知识问答：检索 → 组装带编号的上下文 → 调模型 → 校验引用。

这个模块是整个作品的「可信」防线，三条规则缺一不可：
1. 检索不到（或相关性太差）**不调模型**，直接返回 not_found —— 省钱，也杜绝凭空编造。
2. prompt 强制「只许用给定片段、每条结论标 [编号]、没有依据就输出 NO_ANSWER」。
3. 模型输出后**校验引用编号是否真实存在**，越界的引用清洗掉；一条有效引用都不剩就降级为 not_found。

第 3 条是后处理兜底：模型可能编造 [7]，而检索结果只有 5 条。
"""

from __future__ import annotations

import re
from dataclasses import dataclass, field

from openai import OpenAI

from .config import DEEPSEEK_API_KEY, DEEPSEEK_BASE_URL, DEEPSEEK_MODEL, require_api_key
from .store import Hit, Store

# 检索结果全部比这个还差，就不必问模型了。实测：正确命中 0.44~0.49，无关 0.54~0.88
MAX_DISTANCE = 0.65

NO_ANSWER_MARK = "NO_ANSWER"

SYSTEM_PROMPT = """你是一个严谨的课程资料助手。你必须严格依据用户提供的资料片段回答，不得使用任何外部知识。

规则：
1. 只能使用下面编号片段里的内容作答。
2. 每一条结论后面都要标注来源编号，格式为 [1]、[2]。
3. 如果片段中没有能回答问题的信息，只输出 NO_ANSWER 四个字母，不要输出别的。
4. 不得编造页码、作者、数字、公式。片段里没写的，就不写。
5. 用中文回答，简洁，不要复述问题。"""


@dataclass
class Citation:
    index: int
    chunk_id: str
    doc_id: str
    page_no: int
    text: str


@dataclass
class Answer:
    status: str  # "ok" | "not_found"
    text: str
    citations: list[Citation] = field(default_factory=list)
    searched: list[str] = field(default_factory=list)  # 已检索范围，用于告知用户
    best_distance: float | None = None


def _client() -> OpenAI:
    return OpenAI(api_key=require_api_key(), base_url=DEEPSEEK_BASE_URL)


def _format_context(hits: list[Hit]) -> str:
    lines = []
    for i, h in enumerate(hits, 1):
        snippet = h.text.strip().replace("\n", " ")
        lines.append(f"[{i}] （第 {h.page_no} 页）{snippet}")
    return "\n\n".join(lines)


def _searched_desc(hits: list[Hit]) -> list[str]:
    pages = sorted({h.page_no for h in hits})
    return [f"已检索 {len(hits)} 个片段，覆盖第 {pages[0]}–{pages[-1]} 页" if pages else "未检索到任何片段"]


def _not_found(hits: list[Hit], best: float | None) -> Answer:
    return Answer(
        status="not_found",
        text="资料里没有找到能回答这个问题的内容。",
        citations=[],
        searched=_searched_desc(hits),
        best_distance=best,
    )


def answer(question: str, top_k: int = 8, store: Store | None = None) -> Answer:
    question = question.strip()
    if not question:
        return Answer(status="not_found", text="问题为空。", searched=["没有发送检索请求"])

    store = store or Store()

    if store.count() == 0:
        return Answer(
            status="not_found",
            text="知识库还是空的，请先上传资料。",
            searched=["知识库为空"],
        )

    hits = store.search(question, top_k=top_k)
    if not hits:
        return _not_found([], None)

    best = min(h.distance for h in hits)
    if best > MAX_DISTANCE:
        # 相关性太差，不调模型
        return _not_found(hits, best)

    messages = [
        {"role": "system", "content": SYSTEM_PROMPT},
        {
            "role": "user",
            "content": f"资料片段：\n\n{_format_context(hits)}\n\n问题：{question}",
        },
    ]
    resp = _client().chat.completions.create(
        model=DEEPSEEK_MODEL,
        messages=messages,
        temperature=0,
        max_tokens=800,
    )
    raw = (resp.choices[0].message.content or "").strip()

    if NO_ANSWER_MARK in raw:
        return _not_found(hits, best)

    # --- 引用校验 ---
    used = {int(n) for n in re.findall(r"\[(\d+)\]", raw)}
    valid = {i for i in used if 1 <= i <= len(hits)}

    if used and not valid:
        # 模型引用的编号全部不存在 = 在编造，直接降级
        return _not_found(hits, best)

    citations = [
        Citation(
            index=i,
            chunk_id=hits[i - 1].chunk_id,
            doc_id=hits[i - 1].doc_id,
            page_no=hits[i - 1].page_no,
            text=hits[i - 1].text,
        )
        for i in sorted(valid)
    ]

    if not citations:
        # 没有任何引用标记，说明模型没按规则来，不可信
        return _not_found(hits, best)

    return Answer(
        status="ok",
        text=raw,
        citations=citations,
        searched=_searched_desc(hits),
        best_distance=best,
    )
