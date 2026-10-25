"""学期视图：周次计算与按周排课。

数据来源：backend/data/courses.json（由 tools/build_courses.py 从个人课表脱敏生成）
周次口径：第 1 周从 SEMESTER_START（周一）开始。
"""

from __future__ import annotations

import json
from datetime import date, datetime, timedelta
from functools import lru_cache

from .config import DATA_DIR, SEMESTER_START

WEEKDAY_NAMES = ["周一", "周二", "周三", "周四", "周五", "周六", "周日"]


def _semester_start() -> date:
    return datetime.strptime(SEMESTER_START, "%Y-%m-%d").date()


@lru_cache(maxsize=1)
def load_courses() -> list[dict]:
    path = DATA_DIR / "courses.json"
    data = json.loads(path.read_text(encoding="utf-8"))
    return data["courses"]


def week_no(d: date) -> int:
    """返回 d 所在的教学周。早于开学日期时返回 0 或负数。"""
    return (d - _semester_start()).days // 7 + 1


def week_monday(d: date) -> date:
    """返回 d 所在教学周的周一。"""
    return _semester_start() + timedelta(weeks=week_no(d) - 1)


def _slot_text(c: dict) -> str:
    if c["start_section"] is not None:
        return f"第 {c['start_section']}-{c['end_section']} 节"
    if c["start_time"]:
        return f"{c['start_time']}-{c['end_time']}"
    return "时间待定"


def week_view(d: date) -> dict:
    """给定日期，返回该周的课表。"""
    wn = week_no(d)
    monday = week_monday(d)
    courses = load_courses()

    days = []
    for i in range(7):
        cur = monday + timedelta(days=i)
        todays = [
            {
                "name": c["name"],
                "slot": _slot_text(c),
                "start_section": c["start_section"],
                "end_section": c["end_section"],
                "start_time": c["start_time"],
                "end_time": c["end_time"],
            }
            for c in courses
            if c["day"] == i + 1 and wn in c["weeks"]
        ]
        days.append(
            {
                "date": cur.isoformat(),
                "weekday": WEEKDAY_NAMES[i],
                "is_today": cur == d,
                "courses": todays,
            }
        )

    return {
        "week_no": wn,
        "monday": monday.isoformat(),
        "days": days,
        "course_count": sum(len(x["courses"]) for x in days),
    }
