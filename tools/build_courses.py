"""把个人课表 JSON 转换成项目使用的 courses.json。

开发期一次性工具，不参与运行时。源文件在个人目录，转换时**去掉教师姓名与教室**，
只保留学期视图真正需要的字段。

用法：
    uv run python tools/build_courses.py <源课表 JSON 路径>

源文件格式（拾光课表导出）：{"courses": [{name, teacher, position, day,
startSection, endSection, weeks, customStartTime, customEndTime}, ...]}
"""

from __future__ import annotations

import json
import os
import sys
from pathlib import Path

OUTPUT = Path(__file__).resolve().parents[1] / "backend" / "data" / "courses.json"
SEMESTER_START = "2026-09-07"


def convert(source: Path) -> dict:
    raw = json.loads(source.read_text(encoding="utf-8"))
    items = raw["courses"] if isinstance(raw, dict) else raw

    courses: list[dict] = []
    for item in items:
        weeks = sorted(int(w) for w in item.get("weeks", []))
        if not weeks:
            continue
        courses.append(
            {
                "name": str(item["name"]).strip(),
                "day": int(item["day"]),  # 1=周一 … 7=周日
                "start_section": item.get("startSection"),
                "end_section": item.get("endSection"),
                "weeks": weeks,
                # 无节次的课程（如晚自习）用自定义时间
                "start_time": item.get("customStartTime"),
                "end_time": item.get("customEndTime"),
            }
        )

    courses.sort(key=lambda c: (c["day"], c["start_section"] or 99, c["name"]))

    return {
        "_meta": {
            "semester_start": SEMESTER_START,
            "note": "由个人课表转换，已去除教师姓名与教室，不含任何个人信息",
            "count": len(courses),
        },
        "courses": courses,
    }


def main() -> None:
    arg = sys.argv[1] if len(sys.argv) > 1 else os.getenv("TIMETABLE_JSON")
    if not arg:
        raise SystemExit(
            "缺少源文件。用法：uv run python tools/build_courses.py <课表 JSON 路径>\n"
            "或设置环境变量 TIMETABLE_JSON。\n"
            "（源文件是个人课表导出，不随仓库分发）"
        )
    source = Path(arg)
    if not source.exists():
        raise SystemExit(f"源文件不存在：{source}")

    data = convert(source)
    OUTPUT.parent.mkdir(parents=True, exist_ok=True)
    OUTPUT.write_text(
        json.dumps(data, ensure_ascii=False, indent=2) + "\n", encoding="utf-8"
    )
    print(f"已生成 {OUTPUT}（{data['_meta']['count']} 条）")


if __name__ == "__main__":
    main()
