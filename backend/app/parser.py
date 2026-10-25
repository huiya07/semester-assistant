"""PDF 解析：把 PDF 拆成带页码的纯文本页。

设计约束：
- 只做「文本层提取」，不做 OCR。扫描件识别不了就明确报错，不静默产出空内容。
- doc_id 由文件内容哈希决定，同一文件重复上传得到同一个 id（幂等的基础）。
"""

from __future__ import annotations

import hashlib
from dataclasses import dataclass, field
from pathlib import Path

try:  # PyMuPDF 2.x 同时提供两个入口名，优先新名
    import pymupdf as fitz
except ImportError:  # pragma: no cover
    import fitz  # type: ignore[no-redef]


class NoTextLayerError(Exception):
    """PDF 里提取不到任何文本，通常是扫描件。"""


@dataclass
class Page:
    page_no: int  # 从 1 开始
    text: str


@dataclass
class ParsedDoc:
    doc_id: str
    filename: str
    pages: list[Page]
    blank_pages: list[int] = field(default_factory=list)

    @property
    def page_count(self) -> int:
        return len(self.pages)

    @property
    def text_length(self) -> int:
        return sum(len(p.text) for p in self.pages)


def file_doc_id(path: Path) -> str:
    """按文件内容生成稳定 id，用于去重。"""
    h = hashlib.sha1()
    with Path(path).open("rb") as f:
        for block in iter(lambda: f.read(1 << 20), b""):
            h.update(block)
    return h.hexdigest()[:12]


def parse_pdf(path: Path) -> ParsedDoc:
    path = Path(path)
    if not path.exists():
        raise FileNotFoundError(f"文件不存在：{path}")

    pages: list[Page] = []
    with fitz.open(path) as doc:
        for i, page in enumerate(doc, start=1):
            pages.append(Page(page_no=i, text=page.get_text("text").strip()))

    blank = [p.page_no for p in pages if not p.text]
    if pages and len(blank) == len(pages):
        raise NoTextLayerError(
            f"《{path.name}》提取不到任何文本，可能扫描件。"
            "本系统暂不支持 OCR，请换带文本层的 PDF。"
        )

    return ParsedDoc(
        doc_id=file_doc_id(path),
        filename=path.name,
        pages=pages,
        blank_pages=blank,
    )
