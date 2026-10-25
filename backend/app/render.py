"""把 PDF 某一页渲染成图片，供界面「点出处看原页」使用。

设计：入库时原件被复制到 backend/data/pdfs/{doc_id}.pdf，
所以即使原始文件被移动或删除，引用依然能回溯。
"""

from __future__ import annotations

from pathlib import Path

try:
    import pymupdf as fitz
except ImportError:  # pragma: no cover
    import fitz  # type: ignore[no-redef]


def render_page(pdf_path: Path, page_no: int, dpi: int = 110) -> bytes | None:
    """返回该页的 PNG 字节；页码越界或文件缺失时返回 None。"""
    path = Path(pdf_path)
    if not path.exists():
        return None
    try:
        with fitz.open(path) as doc:
            if page_no < 1 or page_no > doc.page_count:
                return None
            page = doc[page_no - 1]
            pix = page.get_pixmap(dpi=dpi)
            return pix.tobytes("png")
    except Exception:
        return None
