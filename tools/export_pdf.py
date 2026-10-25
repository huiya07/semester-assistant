"""把 Markdown 文档导出为 PDF。

流程：Markdown → HTML（带打印样式）→ Edge 无头打印 PDF。
不依赖 pandoc / LibreOffice，只要有 Edge 就能跑。

用法：
    uv run python tools/export_pdf.py docs/作品介绍.md [输出路径]
"""

from __future__ import annotations

import os
import subprocess
import sys
import tempfile
from pathlib import Path
from urllib.parse import quote

import markdown

EDGE_CANDIDATES = [
    r"C:\Program Files (x86)\Microsoft\Edge\Application\msedge.exe",
    r"C:\Program Files\Microsoft\Edge\Application\msedge.exe",
]

CSS = """
@page { size: A4; margin: 18mm 16mm; }
* { box-sizing: border-box; }
body {
  font-family: "Microsoft YaHei", "Segoe UI", sans-serif;
  font-size: 10.5pt; line-height: 1.65; color: #1a1a1a;
  max-width: 100%;
}
h1 { font-size: 20pt; border-bottom: 2px solid #333; padding-bottom: 6px; margin-top: 0; }
h2 { font-size: 15pt; margin-top: 22px; border-left: 4px solid #c0392b; padding-left: 10px; }
h3 { font-size: 12pt; margin-top: 16px; color: #333; }
h4 { font-size: 11pt; }
table { border-collapse: collapse; width: 100%; margin: 10px 0; font-size: 9.5pt; }
th, td { border: 1px solid #ccc; padding: 5px 8px; text-align: left; vertical-align: top; }
th { background: #f2f2f2; }
code { background: #f5f5f5; padding: 1px 4px; border-radius: 3px; font-size: 9.5pt;
       font-family: Consolas, monospace; }
pre { background: #f7f7f7; padding: 10px; border-left: 3px solid #999; overflow-x: auto;
      font-size: 9pt; line-height: 1.5; }
pre code { background: none; padding: 0; }
blockquote { margin: 8px 0; padding: 6px 12px; background: #fafafa; border-left: 3px solid #bbb;
             color: #555; }
ul, ol { padding-left: 22px; }
hr { border: none; border-top: 1px solid #ddd; margin: 18px 0; }
img { max-width: 100%; border: 1px solid #e0e0e0; border-radius: 4px;
      margin: 8px 0 4px; page-break-inside: avoid; }
p > img { display: block; }
a { color: #1a5276; }
"""


def find_edge() -> str:
    for p in EDGE_CANDIDATES:
        if Path(p).exists():
            return p
    raise SystemExit("找不到 Edge，无法导出 PDF。")


def build_html(md_text: str, base_dir: Path) -> str:
    body = markdown.markdown(
        md_text,
        extensions=["tables", "fenced_code", "sane_lists", "attr_list"],
    )
    return (
        "<!doctype html><html lang='zh-CN'><head><meta charset='utf-8'>"
        f"<style>{CSS}</style></head><body>{body}</body></html>"
    )


def main() -> None:
    if len(sys.argv) < 2:
        raise SystemExit(__doc__)
    src = Path(sys.argv[1]).resolve()
    if not src.exists():
        raise SystemExit(f"源文件不存在：{src}")
    out = Path(sys.argv[2]).resolve() if len(sys.argv) > 2 else src.with_suffix(".pdf")

    html = build_html(src.read_text(encoding="utf-8"), src.parent)

    # HTML 与图片放在源文件同目录，保证相对路径的图片能被加载
    html_path = src.with_name(f"_{src.stem}.html")
    html_path.write_text(html, encoding="utf-8")

    edge = find_edge()
    proc = subprocess.run(
        [
            edge,
            "--headless=new",
            "--disable-gpu",
            "--no-pdf-header-footer",
            f"--print-to-pdf={out}",
            "file:///" + quote(str(html_path).replace("\\", "/")),
        ],
        capture_output=True,
        text=True,
        timeout=120,
    )
    if not out.exists():
        raise SystemExit(f"导出失败：{proc.stderr[:300]}")

    size_kb = out.stat().st_size / 1024
    print(f"已生成 {out}（{size_kb:.0f} KB）")


if __name__ == "__main__":
    main()
