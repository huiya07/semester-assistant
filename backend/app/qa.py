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

from .settings import load as load_settings
from .store import Hit, Store

# 检索结果全部比这个还差，就不必问模型了。实测：正确命中 0.44~0.49，无关 0.54~0.88
MAX_DISTANCE = 0.65

NO_ANSWER_MARK = "NO_ANSWER"

SYSTEM_PROMPT = """你是一个严谨的课程资料助手。你必须严格依据用户提供的资料片段回答，不得使用任何外部知识。

规则：
1. 只能使用下面编号片段里的内容作答。
2. 每一条结论后面都要标注来源编号，格式为 [1]、[2]。
3. 只要片段里包含问题**任何一部分**的答案，就把能答的部分如实回答；资料没有涉及的方面，
   在回答末尾单独用一行写「资料未覆盖：<具体缺哪个方面>」。
   只有当片段与问题**完全无关**、一点相关信息都没有时，才只输出 NO_ANSWER 四个字母。
4. 不得编造页码、作者、数字、公式。片段里没写的，就不写。
5. 用中文回答，简洁，不要复述问题。
6. 用户可能用「它」「这个指标」等指代前文的对象，结合对话历史理解指的是什么；
   但答案内容依然只能来自本轮的资料片段，历史只用于消除指代。"""


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


class MissingAPIKeyError(RuntimeError):
    """没有配置任何 API Key。单独区分出来，好给用户一条能照做的提示。"""


def _client() -> OpenAI:
    """取运行期配置：界面保存的优先，其次 .env。"""
    s = load_settings()
    if not s.ready:
        raise MissingAPIKeyError(
            "还没有配置 API Key。"
            "在页面顶部的「⚙ 模型配置」里填好并保存，或编辑项目根目录的 .env 文件。"
        )
    # 显式给超时：默认值偏长，模型侧卡住时前端要干等好几分钟
    return OpenAI(api_key=s.api_key, base_url=s.base_url, timeout=90.0, max_retries=1)


_PAGE_RE = re.compile(r"第\s*(\d+)\s*页")


def _page_hits(store: Store, question: str, course: str | None = None) -> list[Hit]:
    """问题里点名了「第 N 页」就直接按页取，不走向量检索。

    这类问题问的是文档位置而非内容，语义检索匹配不上：
    实测「《X》的第 1 页说了什么？」距离 0.661，恰好越过 0.65 阈值被拦。
    用户已经把页码说清楚了，没必要再猜。
    """
    m = _PAGE_RE.search(question)
    if not m:
        return []
    return store.chunks_of_page(int(m.group(1)), course=course)


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


def _history_messages(history: list[dict] | None, rounds: int = 5) -> list[dict]:
    """把最近几轮问答转成 messages。

    只用于消除指代（「它」「这个」），答案内容仍必须来自本轮检索片段。
    答案截断到 300 字，避免历史把上下文预算吃光。
    """
    out: list[dict] = []
    for h in (history or [])[-rounds:]:
        q = (h.get("q") or "").strip()
        a = (h.get("a") or "").strip()
        if not q:
            continue
        out.append({"role": "user", "content": q})
        if a:
            out.append({"role": "assistant", "content": a[:300]})
    return out


def answer(
    question: str,
    top_k: int = 8,
    store: Store | None = None,
    course: str | None = None,
    history: list[dict] | None = None,
) -> Answer:
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

    hits = _page_hits(store, question, course=course) or store.search(
        question, top_k=top_k, course=course
    )
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
        *_history_messages(history),
        {
            "role": "user",
            "content": f"资料片段：\n\n{_format_context(hits)}\n\n问题：{question}",
        },
    ]
    try:
        s = load_settings()
        resp = _client().chat.completions.create(
            model=s.model,
            messages=messages,
            temperature=0,
            max_tokens=800,
        )
        raw = (resp.choices[0].message.content or "").strip()
    except MissingAPIKeyError as e:
        return Answer(
            status="error",
            text=str(e),
            searched=[],
            best_distance=best,
        )
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


# ---------------------------------------------------------------------------
# 流式版本（React 前端用）
#
# 与 answer() 共用检索、上下文选择与引用校验逻辑，只是把模型调用换成 stream=True。
# 事件序列：
#   {"type":"meta", ...}        检索完成，附带检索范围（前端可先显示）
#   {"type":"token", "text":…}  增量文本
#   {"type":"done", "citations":[…]}   完成，带校验通过的引用
#   {"type":"not_found", …}     检索不到 / 模型拒答 / 引用全越界
#   {"type":"error", "text":…}  调用失败
#
# NO_ANSWER 处理：模型可能吐到一半才输出该标记，所以前面先扣住一段缓冲，
# 确认不是 NO_ANSWER 再放出去，避免前端闪一下再清空。
# ---------------------------------------------------------------------------

_HOLD_CHARS = 12  # 足够覆盖 "NO_ANSWER" 及前导空白


def answer_stream(
    question: str,
    top_k: int = 8,
    store: Store | None = None,
    course: str | None = None,
    history: list[dict] | None = None,
):
    """生成器，逐条产出事件字典。"""
    question = question.strip()
    if not question:
        yield {"type": "not_found", "text": "问题为空。", "searched": ["没有发送检索请求"]}
        return

    store = store or Store()

    if store.count() == 0:
        yield {
            "type": "not_found",
            "text": "知识库还是空的，请先上传资料。",
            "searched": ["知识库为空"],
        }
        return

    hits = _page_hits(store, question, course=course) or store.search(
        question, top_k=top_k, course=course
    )
    if not hits:
        nf = _not_found([], None)
        yield {
            "type": "not_found",
            "text": nf.text,
            "related": [],
            "searched": nf.searched,
        }
        return

    best = min(h.distance for h in hits)
    if best > MAX_DISTANCE:
        nf = _not_found(hits, best)
        yield {
            "type": "not_found",
            "text": nf.text,
            "related": [],
            "searched": nf.searched,
            "best_distance": best,
        }
        return

    hits = _select_context(hits)
    yield {"type": "meta", "searched": _searched_desc(hits), "best_distance": best}

    messages = [
        {"role": "system", "content": SYSTEM_PROMPT},
        *_history_messages(history),
        {
            "role": "user",
            "content": f"资料片段：\n\n{_format_context(hits)}\n\n问题：{question}",
        },
    ]

    buf = ""
    raw_parts: list[str] = []
    try:
        s = load_settings()
        stream = _client().chat.completions.create(
            model=s.model,
            messages=messages,
            temperature=0,
            max_tokens=800,
            stream=True,
        )
        for chunk in stream:
            delta = chunk.choices[0].delta.content or ""
            if not delta:
                continue
            raw_parts.append(delta)
            buf += delta
            # 还短且可能是 NO_ANSWER：继续扣住
            if len(buf) < _HOLD_CHARS and NO_ANSWER_MARK.startswith(buf.strip()[: len(NO_ANSWER_MARK)]):
                continue
            if buf:
                yield {"type": "token", "text": buf}
                buf = ""
    except MissingAPIKeyError as e:
        yield {"type": "error", "text": str(e)}
        return
    except Exception as e:
        yield {
            "type": "error",
            "text": "调用大模型失败，请检查网络或 API 配置后重试。",
            "detail": type(e).__name__,
        }
        return

    raw = "".join(raw_parts).strip()

    if NO_ANSWER_MARK in raw:
        nf = _not_found(hits, best)
        yield {
            "type": "not_found",
            "text": nf.text,
            "related": [
                {
                    "index": c.index, "doc_id": c.doc_id, "doc_name": c.doc_name,
                    "page_no": c.page_no, "text": c.text, "pdf_file": c.pdf_file,
                }
                for c in nf.related
            ],
            "searched": nf.searched,
        }
        return

    used = {int(n) for n in re.findall(r"\[(\d+)\]", raw)}
    valid = {i for i in used if 1 <= i <= len(hits)}

    if (used and not valid) or not valid:
        nf = _not_found(hits, best)
        yield {
            "type": "not_found",
            "text": nf.text,
            "related": [
                {
                    "index": c.index, "doc_id": c.doc_id, "doc_name": c.doc_name,
                    "page_no": c.page_no, "text": c.text, "pdf_file": c.pdf_file,
                }
                for c in nf.related
            ],
            "searched": nf.searched,
        }
        return

    yield {
        "type": "done",
        "citations": [
            {
                "index": c.index, "doc_id": c.doc_id, "doc_name": c.doc_name,
                "page_no": c.page_no, "text": c.text, "pdf_file": c.pdf_file,
            }
            for c in (_to_citation(i, hits[i - 1]) for i in sorted(valid))
        ],
        "searched": _searched_desc(hits),
        "best_distance": best,
    }
