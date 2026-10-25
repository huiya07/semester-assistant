"""命令行验收工具：不依赖前端就能验证后端功能。

用法：
    uv run python -m backend.cli week [YYYY-MM-DD]
    uv run python -m backend.cli parse <pdf路径>
    uv run python -m backend.cli index <pdf路径>
    uv run python -m backend.cli search <问题>
    uv run python -m backend.cli ask <问题>
    uv run python -m backend.cli stats
"""

from __future__ import annotations

import sys
from datetime import date, datetime
from pathlib import Path

from .app.chunker import chunk_doc
from .app.parser import NoTextLayerError, parse_pdf
from .app.semester import week_view
from .app.store import Store


def cmd_week(arg: str | None = None) -> None:
    d = datetime.strptime(arg, "%Y-%m-%d").date() if arg else date.today()
    view = week_view(d)

    if view.get("before_semester"):
        print(f"学期还没开始（开学日 {view['monday']}）。")
        return

    print(f"第 {view['week_no']} 周 · {view['monday']} 起 · 共 {view['course_count']} 节课")
    print("-" * 46)
    for day in view["days"]:
        mark = " ← 今天" if day["is_today"] else ""
        head = f"{day['weekday']} {day['date']}{mark}"
        if not day["courses"] and not day["due"]:
            print(f"{head}    无课")
            continue
        print(head)
        for c in day["courses"]:
            print(f"    {c['slot']:<16} {c['name']}")
        for a in day["due"]:
            print(f"    {'⚠ 作业截止':<14} {a['course']} · {a['title']}")

    if view["upcoming"]:
        print("-" * 46)
        print("接下来两周要交：")
        for a in view["upcoming"]:
            print(f"  {a['due_date']}  {a['course']} · {a['title']}")
    else:
        print("-" * 46)
        print("接下来两周没有到期作业。")


def cmd_parse(path_str: str) -> None:
    path = Path(path_str)
    try:
        doc = parse_pdf(path)
    except FileNotFoundError as e:
        print(f"[文件不存在] {e}")
        return
    except NoTextLayerError as e:
        print(f"[无法解析] {e}")
        return

    chunks = chunk_doc(doc)
    print(f"文件：{doc.filename}")
    print(f"doc_id：{doc.doc_id}")
    print(f"页数：{doc.page_count}   字符数：{doc.text_length}   切片数：{len(chunks)}")
    if doc.blank_pages:
        print(f"空白页（可能是图片页）：{doc.blank_pages}")
    print("-" * 46)
    if chunks:
        first = chunks[0]
        print(f"首片 [p{first.page_no} #{first.ordinal}] {len(first.text)} 字：")
        print("  " + first.text[:180].replace("\n", " ") + "…")
        last = chunks[-1]
        print(f"末片 [p{last.page_no} #{last.ordinal}] {len(last.text)} 字：")
        print("  " + last.text[:180].replace("\n", " ") + "…")


def cmd_index(path_str: str) -> None:
    path = Path(path_str)
    try:
        doc = parse_pdf(path)
    except FileNotFoundError as e:
        print(f"[文件不存在] {e}")
        return
    except NoTextLayerError as e:
        print(f"[无法解析] {e}")
        return

    chunks = chunk_doc(doc)
    store = Store()
    store.delete_doc(doc.doc_id)  # 重入库先清旧的，避免切片参数变化后残留
    pdf_file = store.store_pdf(path, doc.doc_id)
    n = store.upsert(chunks, pdf_file=pdf_file)
    print(f"已入库：{doc.filename}")
    print(f"doc_id：{doc.doc_id}   页数：{doc.page_count}   写入切片：{n}")
    print(f"原件留底：{pdf_file}")
    print(f"库内总切片：{store.count()}")


def cmd_search(query: str, top_k: int = 5) -> None:
    store = Store()
    print(f"库内总切片：{store.count()}")
    hits = store.search(query, top_k=top_k)
    if not hits:
        print("没有命中（库是空的，或问题为空）。")
        return
    print("-" * 46)
    for i, h in enumerate(hits, 1):
        print(f"[{i}] p{h.page_no}  distance={h.distance:.4f}  score={h.score:.3f}")
        print("    " + h.text[:150].replace("\n", " ") + "…")


def cmd_stats() -> None:
    store = Store()
    print(f"库内总切片：{store.count()}")
    for d in store.docs():
        print(f"  {d['doc_name']}  [{d['doc_id']}]  {d['chunks']} 片")


def cmd_ask(question: str) -> None:
    from .app.qa import answer as ask

    res = ask(question)
    print(f"状态：{res.status}" + (f"  最佳距离：{res.best_distance:.4f}" if res.best_distance is not None else ""))
    print("-" * 46)
    print(res.text)
    if res.citations:
        print("-" * 46)
        print("引用出处：")
        for c in res.citations:
            print(f"  [{c.index}] 《{c.doc_name}》第 {c.page_no} 页  {c.text[:80].replace(chr(10), ' ')}…")
    if res.related:
        print("-" * 46)
        print("最接近的内容：")
        for c in res.related:
            print(f"  [{c.index}] 《{c.doc_name}》第 {c.page_no} 页  {c.text[:80].replace(chr(10), ' ')}…")
    if res.searched:
        print("-" * 46)
        for s in res.searched:
            print(f"  {s}")


def main() -> None:
    args = sys.argv[1:]
    if not args or args[0] == "week":
        cmd_week(args[1] if len(args) > 1 else None)
    elif args[0] == "parse" and len(args) > 1:
        cmd_parse(args[1])
    elif args[0] == "index" and len(args) > 1:
        cmd_index(args[1])
    elif args[0] == "search" and len(args) > 1:
        cmd_search(" ".join(args[1:]))
    elif args[0] == "ask" and len(args) > 1:
        cmd_ask(" ".join(args[1:]))
    elif args[0] == "stats":
        cmd_stats()
    else:
        print(__doc__)


if __name__ == "__main__":
    main()
