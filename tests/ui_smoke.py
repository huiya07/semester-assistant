"""前端端到端冒烟：用 Playwright 驱动真实浏览器走一遍主要流程。

后端 pytest 覆盖不到渲染和交互，这个脚本补那一段。

前置：
    后端已启动（uv run uvicorn backend.app.main:app --port 8000）
    Playwright 装在**全局** Python，不在项目 venv（系统 Edge 即可，不需要下 chromium）

运行：
    python -X utf8 tests/ui_smoke.py

截图落在 %TEMP%/sa-e2e/，失败时可直接看。
"""

from __future__ import annotations

import os
import sys
import tempfile
import time
from pathlib import Path

BASE = os.getenv("SA_BASE", "http://127.0.0.1:8000")
OUT = Path(tempfile.gettempdir()) / "sa-e2e"


class Check:
    def __init__(self) -> None:
        self.failed: list[str] = []

    def __call__(self, name: str, ok: bool, detail: str = "") -> None:
        mark = "PASS" if ok else "FAIL"
        print(f"  [{mark}] {name}" + (f"  — {detail}" if detail and not ok else ""))
        if not ok:
            self.failed.append(name)


def main() -> int:
    from playwright.sync_api import sync_playwright

    OUT.mkdir(parents=True, exist_ok=True)
    check = Check()

    with sync_playwright() as p:
        browser = p.chromium.launch(channel="msedge", headless=True)
        page = browser.new_page(viewport={"width": 1600, "height": 1000})

        print("== 加载 ==")
        page.goto(BASE, wait_until="networkidle")
        page.wait_for_timeout(1500)
        check("页面标题正确", "学期助手" in page.title(), page.title())
        check("侧边栏渲染", page.locator("text=学期助手").count() > 0)
        check("输入框可用", page.locator("textarea").count() == 1)

        # 资料库应该有内容（后端 pytest 保证至少有示例讲义）
        lib_text = page.locator("text=资料库").first.inner_text()
        check("资料库可读", "篇" in lib_text, lib_text)

        print("== 问答链路 ==")
        page.fill("textarea", "均值和中位数的区别是什么？")
        page.keyboard.press("Enter")

        # 等流式结束：发送按钮从「停止」变回「发送」
        deadline = time.time() + 60
        answered = False
        while time.time() < deadline:
            page.wait_for_timeout(500)
            body = page.inner_text("main")
            if "用时" in body:
                answered = True
                break
        check("提问得到回答", answered)
        body = page.inner_text("main")
        check("显示检索范围", "已检索" in body)
        check("显示耗时", "用时" in body or "不到 0.1" in body)

        # 出处卡片
        cite = page.locator("button:has-text('出处')").first
        check("出现出处卡片", cite.count() > 0)
        if cite.count():
            cite.click()
            page.wait_for_timeout(700)
            expanded = page.inner_text("main")
            check("出处可展开出原文", "命中片段" in expanded)
            page.screenshot(path=str(OUT / "01-answer.png"))

        # 找不到时不能编
        page.fill("textarea", "太阳系一共有几颗行星？")
        page.keyboard.press("Enter")
        deadline = time.time() + 40
        refused = False
        while time.time() < deadline:
            page.wait_for_timeout(500)
            if "没有检索到" in page.inner_text("main") or "没有直接回答" in page.inner_text("main"):
                refused = True
                break
        check("资料外的内容会被拒答", refused)
        page.screenshot(path=str(OUT / "02-notfound.png"))

        print("== 周视图 ==")
        page.click("button:has-text('这周该做什么')")
        page.wait_for_timeout(1200)
        week = page.inner_text("main")
        check("显示周次", "第" in week and "周" in week)
        days = sum(1 for d in ("周一", "周二", "周三", "周四", "周五", "周六", "周日") if d in week)
        check("7 列齐全", days == 7, f"只有 {days} 列")

        page.click("text=导入 / 管理课表与作业")
        page.wait_for_timeout(600)
        check("导入面板可展开", "导入课表 JSON" in page.inner_text("main"))
        page.screenshot(path=str(OUT / "03-week.png"))

        print("== 窄屏 ==")
        page.set_viewport_size({"width": 1280, "height": 800})
        page.wait_for_timeout(600)
        overflow = page.evaluate(
            "() => document.documentElement.scrollWidth > document.documentElement.clientWidth"
        )
        check("1280 宽无横向溢出", not overflow)
        page.screenshot(path=str(OUT / "04-narrow.png"))

        browser.close()

    print()
    if check.failed:
        print(f"失败 {len(check.failed)} 项：{', '.join(check.failed)}")
        print(f"截图目录 {OUT}")
        return 1
    print(f"全部通过。截图 {OUT}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
