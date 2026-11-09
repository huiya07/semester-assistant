"""PDF 页级工具：取整页文本、定位检索片段、渲染页面图像。

设计：入库时原件被复制到 backend/data/pdfs/{doc_id}.pdf，
所以即使原始文件被移动或删除，引用依然能回溯。
"""

from __future__ import annotations

from pathlib import Path

try:
    import pymupdf as fitz
except ImportError:  # pragma: no cover
    import fitz  # type: ignore[no-redef]


def _open_page(pdf_path: Path, page_no: int):
    """打开文档并确认页码有效，返回 (doc, page)；调用方负责关闭 doc。"""
    path = Path(pdf_path)
    if not path.exists():
        return None, None
    doc = fitz.open(path)
    if page_no < 1 or page_no > doc.page_count:
        doc.close()
        return None, None
    return doc, doc[page_no - 1]


def page_count(pdf_path: Path) -> int:
    """文档总页数；文件缺失时返回 0。"""
    try:
        if not Path(pdf_path).exists():
            return 0
        with fitz.open(pdf_path) as doc:
            return doc.page_count
    except Exception:
        return 0


def render_page(pdf_path: Path, page_no: int, dpi: int = 110) -> bytes | None:
    """返回该页的 PNG 字节；页码越界或文件缺失时返回 None。"""
    try:
        doc, page = _open_page(pdf_path, page_no)
        if doc is None:
            return None
        with doc:
            return page.get_pixmap(dpi=dpi).tobytes("png")
    except Exception:
        return None

