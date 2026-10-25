"""文本切片。

约束：
- **不跨页**：每个 chunk 只属于一页，这样引用能精确到页码，也避免跨页拼接产生的语义断裂。
- 按字符窗口切，带 overlap，保证句子被截断时上下文仍留在相邻块里。
- chunk_id 由 doc_id + 页码 + 序号构成，重复入库时可幂等覆盖。
"""

from __future__ import annotations

from dataclasses import dataclass

from .parser import ParsedDoc


@dataclass
class Chunk:
    chunk_id: str
    doc_id: str
    page_no: int
    ordinal: int  # 在本页内的序号，从 0 开始
    text: str


def _split_page(text: str, size: int, overlap: int) -> list[str]:
    if len(text) <= size:
        return [text] if text else []

    step = max(1, size - overlap)
    parts: list[str] = []
    start = 0
    while start < len(text):
        piece = text[start : start + size].strip()
        if piece:
            parts.append(piece)
        if start + size >= len(text):
            break
        start += step
    return parts


def chunk_doc(doc: ParsedDoc, size: int = 600, overlap: int = 80) -> list[Chunk]:
    if overlap >= size:
        raise ValueError("overlap 必须小于 size")

    chunks: list[Chunk] = []
    for page in doc.pages:
        if not page.text:
            continue
        for ordinal, piece in enumerate(_split_page(page.text, size, overlap)):
            chunks.append(
                Chunk(
                    chunk_id=f"{doc.doc_id}-p{page.page_no}-{ordinal:03d}",
                    doc_id=doc.doc_id,
                    page_no=page.page_no,
                    ordinal=ordinal,
                    text=piece,
                )
            )
    return chunks
