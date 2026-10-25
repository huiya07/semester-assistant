"""命令行验收工具：不依赖前端就能验证后端功能。

用法：
    uv run python -m backend.cli week [YYYY-MM-DD]
    uv run python -m backend.cli parse <pdf路径>
"""

from __future__ import annotations

import sys
from datetime import date, datetime
from pathlib import Path

from .app.chunker import chunk_doc
from .app.parser import NoTextLayerError, parse_pdf
from .app.semester import week_view


def cmd_week(arg: str | None = None) -> None:
    d = datetime.strptime(arg, "%Y-%m-%d").date() if arg else date.today()
    view = week_view(d)

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


def main() -> None:
    args = sys.argv[1:]
    if not args or args[0] == "week":
        cmd_week(args[1] if len(args) > 1 else None)
    elif args[0] == "parse" and len(args) > 1:
        cmd_parse(args[1])
    else:
        print(__doc__)


if __name__ == "__main__":
    main()
