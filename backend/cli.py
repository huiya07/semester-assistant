"""命令行验收工具：不依赖前端就能验证后端功能。

用法：
    uv run python -m backend.cli week [YYYY-MM-DD]
"""

from __future__ import annotations

import sys
from datetime import date, datetime

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


def main() -> None:
    args = sys.argv[1:]
    if not args or args[0] == "week":
        cmd_week(args[1] if len(args) > 1 else None)
    else:
        print(__doc__)


if __name__ == "__main__":
    main()
