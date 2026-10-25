"""生成一份无版权的示例讲义 PDF，用于演示与自测。

为什么需要它：仓库不附带第三方 PDF（版权），但干净克隆后必须能立刻跑通
「上传 → 解析 → 提问」全流程，所以用脚本现场造一份。

内容为虚构的数据分析入门讲义，不含任何第三方素材。

用法：
    uv run python tools/make_sample_pdf.py
输出：
    backend/samples/sample-lecture-notes.pdf
"""

from __future__ import annotations

from pathlib import Path

import pymupdf

OUT = Path(__file__).resolve().parents[1] / "backend" / "samples" / "sample-lecture-notes.pdf"

FONT = "china-s"  # PyMuPDF 内置简体中文字体
PAGE = pymupdf.paper_rect("a4")
MARGIN = 64
WIDTH = PAGE.width - 2 * MARGIN

PAGES: list[tuple[str, str, list[str]]] = [
    (
        "第一章 数据的类型",
        "在开始分析之前，先要弄清楚手里拿到的数据属于哪一类。不同类型的数据，"
        "能用的统计方法和可视化方式完全不同。",
        [
            "数值型数据（quantitative）：可以直接做加减乘除的量，例如身高、成绩、"
            "销售额。它又分为连续型和离散型：连续型可以取任意小数（如温度），"
            "离散型只能取整数（如人数）。",
            "分类型数据（nominal）：只是标签，没有大小顺序，例如专业名称、"
            "血型、城市。对分类型数据计算平均值没有意义。",
            "顺序型数据（ordinal）：有顺序但间隔不确定，例如满意度五级量表、"
            "学历层次。可以比较大小，但不能直接相减。",
            "常见错误：把学号当成数值型去做平均。学号只是标识，属于分类型。",
        ],
    ),
    (
        "第二章 描述统计",
        "描述统计用几个数字概括一批数据。选错指标，结论会完全相反。",
        [
            "均值（mean）：所有数值之和除以个数。对极端值非常敏感，"
            "一条异常记录就能把它拉偏。",
            "中位数（median）：排序后位于中间的数。不受极端值影响，"
            "收入、房价这类偏态分布数据通常用中位数更能代表典型水平。",
            "众数（mode）：出现次数最多的值。分类型数据唯一能用的集中趋势指标。",
            "标准差（standard deviation）：衡量数据分散程度。标准差大，"
            "说明个体差异明显；标准差小，说明数据集中在均值附近。",
            "经验判断：当均值和中位数差距明显时，说明数据存在偏态或异常值，"
            "此时优先报告中位数，并说明原因。",
        ],
    ),
    (
        "第三章 可视化选择",
        "图表不是越漂亮越好，而是要和数据类型、分析目的匹配。",
        [
            "直方图（histogram）：看连续数值型数据的分布形状，例如成绩分布是否"
            "呈双峰。注意它和柱状图不同：直方图的横轴是连续的区间。",
            "箱线图（box plot）：一次展示中位数、四分位数和异常值，"
            "适合比较多组的分布差异。",
            "散点图（scatter plot）：看两个数值型变量之间的关系，"
            "例如学习时长与成绩是否同向变化。",
            "柱状图（bar chart）：比较不同类别的数量，横轴是分类型标签。",
            "选择原则：先判断数据类型，再判断要看分布、比较还是关系，"
            "最后才考虑配色与美化。",
        ],
    ),
]


def wrap(text: str, fontsize: float, max_width: float) -> list[str]:
    """按字符宽度粗略折行（中文等宽，够用）。"""
    per_line = int(max_width // fontsize)
    lines: list[str] = []
    for para in text.split("\n"):
        for i in range(0, len(para), per_line):
            lines.append(para[i : i + per_line])
    return lines


def main() -> None:
    doc = pymupdf.open()

    for title, intro, bullets in PAGES:
        page = doc.new_page(width=PAGE.width, height=PAGE.height)
        y = MARGIN + 10

        page.insert_text((MARGIN, y), title, fontsize=18, fontname=FONT)
        y += 34

        for line in wrap(intro, 11, WIDTH):
            page.insert_text((MARGIN, y), line, fontsize=11, fontname=FONT)
            y += 18
        y += 10

        for i, bullet in enumerate(bullets, 1):
            head = f"{i}. "
            page.insert_text((MARGIN, y), head, fontsize=11, fontname=FONT)
            lines = wrap(bullet, 11, WIDTH - 20)
            for j, line in enumerate(lines):
                page.insert_text((MARGIN + 20, y), line, fontsize=11, fontname=FONT)
                y += 18
            y += 6

    OUT.parent.mkdir(parents=True, exist_ok=True)
    doc.save(OUT)
    doc.close()
    print(f"已生成 {OUT}（{len(PAGES)} 页）")


if __name__ == "__main__":
    main()
