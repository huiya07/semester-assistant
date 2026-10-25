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


def page_text(pdf_path: Path, page_no: int) -> str | None:
    """取该页的完整文本（用于「整页展示 + 标出你问到的部分」）。"""
    try:
        doc, page = _open_page(pdf_path, page_no)
        if doc is None:
            return None
        with doc:
            return page.get_text("text").strip()
    except Exception:
        return None


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


def split_by_excerpt(full_text: str, excerpt: str) -> tuple[str, str, str] | None:
    """把整页文本按检索片段切成 (前, 片段, 后)。

    切片来自同一份 PDF 的提取文本，理论上能精确匹配；
    匹配不上时返回 None，由调用方降级处理。
    """
    core = excerpt.strip()
    if not core:
        return None

    idx = full_text.find(core)
    if idx >= 0:
        return full_text[:idx], core, full_text[idx + len(core) :]

    # 退一步：用开头 60 个字符定位，应对首尾空白差异
    head = core[:60]
    idx = full_text.find(head)
    if idx < 0:
        return None
    end = min(len(full_text), idx + len(core))
    return full_text[:idx], full_text[idx:end], full_text[end:]
