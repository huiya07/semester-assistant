"""学期视图：周次计算与按周排课。

数据来源：backend/data/courses.json（由 tools/build_courses.py 从个人课表脱敏生成）
周次口径：第 1 周从 SEMESTER_START（周一）开始。
"""

from __future__ import annotations

import json
from datetime import date, datetime, timedelta
from functools import lru_cache
from pathlib import Path

from .config import DATA_DIR, SEMESTER_START

WEEKDAY_NAMES = ["周一", "周二", "周三", "周四", "周五", "周六", "周日"]

# 用户导入的数据放在 local/（不进仓库），存在时覆盖仓库自带的示例
USER_DATA_DIR = DATA_DIR.parents[1] / "local" / "data"


def data_path(filename: str) -> Path:
    """优先用用户导入的文件，其次用仓库自带示例。"""
    user = USER_DATA_DIR / filename
    return user if user.exists() else DATA_DIR / filename


COURSE_FIELDS = ("name", "day", "weeks")
ASSIGNMENT_FIELDS = ("course", "title", "due_date")


def validate_courses(data) -> tuple[bool, str]:
    """导入前校验：宁可拒绝，也不要让坏数据把周视图搞崩。"""
    items = data.get("courses") if isinstance(data, dict) else data
    if not isinstance(items, list) or not items:
        return False, "courses 必须是非空数组"
    for i, c in enumerate(items, 1):
        if not isinstance(c, dict):
            return False, f"第 {i} 条不是对象"
        missing = [f for f in COURSE_FIELDS if f not in c]
        if missing:
            return False, f"第 {i} 条缺少字段 {'、'.join(missing)}"
        if not isinstance(c["weeks"], list):
            return False, f"第 {i} 条的 weeks 必须是数组"
    return True, ""


def validate_assignments(data) -> tuple[bool, str]:
    items = data.get("assignments") if isinstance(data, dict) else data
    if not isinstance(items, list) or not items:
        return False, "assignments 必须是非空数组"
    for i, a in enumerate(items, 1):
        if not isinstance(a, dict):
            return False, f"第 {i} 条不是对象"
        missing = [f for f in ASSIGNMENT_FIELDS if f not in a]
        if missing:
            return False, f"第 {i} 条缺少字段 {'、'.join(missing)}"
    return True, ""


def _safe_courses() -> list[dict]:
    """读取时再过滤一遍：历史遗留的坏条目直接跳过，不让页面崩。"""
    try:
        items = json.loads(data_path("courses.json").read_text(encoding="utf-8"))["courses"]
    except Exception:
        return []
    return [
        c
        for c in items
        if isinstance(c, dict) and all(f in c for f in COURSE_FIELDS)
    ]


def _safe_assignments() -> list[dict]:
    try:
        items = json.loads(data_path("assignments.json").read_text(encoding="utf-8"))["assignments"]
    except Exception:
        return []
    return [
        a
        for a in items
        if isinstance(a, dict) and all(f in a for f in ASSIGNMENT_FIELDS)
    ]


def reload_data() -> None:
    """导入或恢复默认后清缓存，否则页面还读旧的。"""
    load_courses.cache_clear()
    load_assignments.cache_clear()


def _semester_start() -> date:
    return datetime.strptime(SEMESTER_START, "%Y-%m-%d").date()


@lru_cache(maxsize=1)
def load_courses() -> list[dict]:
    return _safe_courses()


@lru_cache(maxsize=1)
def load_assignments() -> list[dict]:
    """作业是一次性事件（带截止日期），不是每周固定条目。"""
    return _safe_assignments()


def assignments_due_on(d: date) -> list[dict]:
    return [a for a in load_assignments() if a["due_date"] == d.isoformat()]


def upcoming_assignments(d: date, within_days: int = 14) -> list[dict]:
    """从 d 起（含）未来 within_days 天内到期的作业，按日期升序。"""
    end = (d + timedelta(days=within_days)).isoformat()
    start = d.isoformat()
    return sorted(
        (a for a in load_assignments() if start <= a["due_date"] <= end),
        key=lambda a: a["due_date"],
    )


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
    """给定日期，返回该周的课表。早于开学日期时返回空视图并标记。"""
    wn = week_no(d)
    if wn < 1:
        return {
            "week_no": wn,
            "monday": _semester_start().isoformat(),
            "days": [],
            "course_count": 0,
            "upcoming": upcoming_assignments(d),
            "before_semester": True,
        }

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
                "due": assignments_due_on(cur),
            }
        )

    return {
        "week_no": wn,
        "monday": monday.isoformat(),
        "days": days,
        "course_count": sum(len(x["courses"]) for x in days),
        "upcoming": upcoming_assignments(d),
        "before_semester": False,
    }
