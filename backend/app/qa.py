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
    doc_name: str
    page_no: int
    text: str
    pdf_file: str = ""


@dataclass
class Answer:
    status: str  # "ok" | "not_found"
    text: str
    citations: list[Citation] = field(default_factory=list)
    related: list[Citation] = field(default_factory=list)  # not_found 时最接近的内容
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
    """按文档分组描述检索范围。不能把不同文档的页码混在一起说「第 1–10 页」。"""
    if not hits:
        return ["未检索到任何片段"]
    grouped: dict[str, list[int]] = {}
    for h in hits:
        grouped.setdefault(h.doc_name or h.doc_id, []).append(h.page_no)
    parts = []
    for name, pages in grouped.items():
        uniq = sorted(set(pages))
        shown = "、".join(str(p) for p in uniq[:6])
        more = f" 等 {len(uniq)} 页" if len(uniq) > 6 else " 页"
        parts.append(f"《{name}》第 {shown}{more}")
    return ["已检索：" + "；".join(parts)]


def _to_citation(index: int, hit: Hit) -> Citation:
    return Citation(
        index=index,
        chunk_id=hit.chunk_id,
        doc_id=hit.doc_id,
        doc_name=hit.doc_name,
        page_no=hit.page_no,
        text=hit.text,
        pdf_file=hit.pdf_file,
    )


def _not_found(hits: list[Hit], best: float | None) -> Answer:
    """区分「没检索到」和「找到了但不包含答案」，后者要告诉用户看到了什么。"""
    if not hits or best is None:
        return Answer(
            status="not_found",
            text="资料里没有检索到与这个问题相关的内容。",
            searched=_searched_desc(hits),
            best_distance=best,
        )

    if best > MAX_DISTANCE:
        return Answer(
            status="not_found",
            text="资料里没有检索到与这个问题相关的内容。",
            searched=_searched_desc(hits),
            best_distance=best,
        )

    # 找到了相关片段，但模型认为里面没有答案 —— 把最接近的原文摆出来让用户自己判断
    top = hits[0]
    same_doc = [h for h in hits if h.doc_id == top.doc_id][:2]
    related = [_to_citation(i, h) for i, h in enumerate(same_doc, 1)]
    return Answer(
        status="not_found",
        text=(
            f"检索到了《{top.doc_name}》第 {top.page_no} 页的相关内容，"
            "但里面没有直接回答这个问题的信息。\n\n最接近的原文在下面，你可以自己判断。"
        ),
        related=related,
        searched=_searched_desc(hits),
        best_distance=best,
    )


def _select_context(hits: list[Hit], max_other: int = 2) -> list[Hit]:
    """同文档优先：最相关片段所在的资料，优先把它的其它片段喂给模型。

    实测问题：问《习题1.1》时，8 个召回里有 7 个是英文论文的无关片段，
    噪声会稀释上下文，模型更容易答偏或拒答。
    """
    if len(hits) <= 2:
        return hits
    top_doc = hits[0].doc_id
    same = [h for h in hits if h.doc_id == top_doc]
    others = [h for h in hits if h.doc_id != top_doc][:max_other]
    return same + others


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

    # 同文档优先，减少跨资料噪声；后面的编号都以筛选后的顺序为准
    hits = _select_context(hits)

    messages = [
        {"role": "system", "content": SYSTEM_PROMPT},
        {
            "role": "user",
            "content": f"资料片段：\n\n{_format_context(hits)}\n\n问题：{question}",
        },
    ]
    try:
        resp = _client().chat.completions.create(
            model=DEEPSEEK_MODEL,
            messages=messages,
            temperature=0,
            max_tokens=800,
        )
        raw = (resp.choices[0].message.content or "").strip()
    except Exception as e:  # 断网、超时、额度不足都走这里
        return Answer(
            status="error",
            text="调用大模型失败，请检查网络或 API 配置后重试。",
            searched=[f"错误类型：{type(e).__name__}"],
            best_distance=best,
        )

    if NO_ANSWER_MARK in raw:
        return _not_found(hits, best)

    # --- 引用校验 ---
    used = {int(n) for n in re.findall(r"\[(\d+)\]", raw)}
    valid = {i for i in used if 1 <= i <= len(hits)}

    if used and not valid:
        # 模型引用的编号全部不存在 = 在编造，直接降级
        return _not_found(hits, best)

    citations = [
        _to_citation(i, hits[i - 1]) for i in sorted(valid)
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
