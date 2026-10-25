"""向量库读写。

- 用 Chroma 的本地持久化，数据落在 chroma_data/（已 gitignore）。
- id 直接用 chunk_id，所以同一篇文档重复入库是幂等的（upsert 覆盖）。
- 嵌入模型暂用 Chroma 自带的 all-MiniLM-L6-v2（英文向）。
  中文语料需要换成 bge-small-zh 等中文模型，见 docs/决策记录.md D7。

距离语义：Chroma 返回的 distance 越小越相关，且它不保证归一化，
所以对外同时给 raw distance 和一个单调的 score = 1/(1+distance)。
"""

from __future__ import annotations

import shutil
from dataclasses import dataclass
from pathlib import Path

import chromadb

from .chunker import Chunk
from .config import CHROMA_DIR, PDF_STORE_DIR, ROOT
from .embedding import MODEL_TAG, BGEEmbeddingFunction

# 集合名带模型标识：换嵌入模型 = 新集合，避免新旧向量混在一起（维度也不同）
COLLECTION = f"chunks_{MODEL_TAG}_v1"


@dataclass
class Hit:
    chunk_id: str
    doc_id: str
    doc_name: str
    page_no: int
    text: str
    distance: float
    pdf_file: str = ""  # 相对项目根目录的原件路径，用于「看原页」

    @property
    def score(self) -> float:
        """0~1，越大越相关。仅用于展示排序，不参与阈值判断。"""
        return 1.0 / (1.0 + self.distance)

    @property
    def pdf_path(self) -> Path:
        return ROOT / self.pdf_file if self.pdf_file else Path()


class Store:
    def __init__(self, path: Path | None = None) -> None:
        self.path = Path(path or CHROMA_DIR)
        self.client = chromadb.PersistentClient(path=str(self.path))
        self.col = self.client.get_or_create_collection(
            name=COLLECTION,
            metadata={"hnsw:space": "cosine"},
            embedding_function=BGEEmbeddingFunction(),
        )

    # --- 写入 ---
    def store_pdf(self, src: Path, doc_id: str) -> str:
        """把原件复制一份留底，返回相对项目根目录的路径。"""
        PDF_STORE_DIR.mkdir(parents=True, exist_ok=True)
        dst = PDF_STORE_DIR / f"{doc_id}.pdf"
        if not dst.exists() or dst.stat().st_size != Path(src).stat().st_size:
            shutil.copy2(src, dst)
        return str(dst.relative_to(ROOT)).replace("\\", "/")

    def upsert(self, chunks: list[Chunk], pdf_file: str = "") -> int:
        if not chunks:
            return 0
        self.col.upsert(
            ids=[c.chunk_id for c in chunks],
            documents=[c.text for c in chunks],
            metadatas=[
                {
                    "doc_id": c.doc_id,
                    "doc_name": c.doc_name,
                    "page_no": c.page_no,
                    "ordinal": c.ordinal,
                    "pdf_file": pdf_file,
                }
                for c in chunks
            ],
        )
        return len(chunks)

    def delete_doc(self, doc_id: str) -> None:
        """删除某篇文档的全部切片。切片参数变了要重入库时用。"""
        self.col.delete(where={"doc_id": doc_id})

    def purge_document(self, doc_id: str) -> None:
        """彻底删除一篇文档：向量切片 + 留底的原件。"""
        self.delete_doc(doc_id)
        leftover = PDF_STORE_DIR / f"{doc_id}.pdf"
        leftover.unlink(missing_ok=True)

    # --- 读 ---
    def search(self, query: str, top_k: int = 5) -> list[Hit]:
        if not query.strip() or self.count() == 0:
            return []
        res = self.col.query(query_texts=[query], n_results=min(top_k, self.count()))
        ids = res["ids"][0]
        docs = res["documents"][0]
        metas = res["metadatas"][0]
        dists = res["distances"][0]
        return [
            Hit(
                chunk_id=i,
                doc_id=m["doc_id"],
                doc_name=m.get("doc_name", m["doc_id"]),
                page_no=m["page_no"],
                text=d,
                distance=float(dist),
                pdf_file=m.get("pdf_file", ""),
            )
            for i, d, m, dist in zip(ids, docs, metas, dists)
        ]

    def count(self) -> int:
        return self.col.count()

    def docs(self) -> list[dict]:
        """返回库里已有哪些文档（去重）。"""
        if self.count() == 0:
            return []
        res = self.col.get(include=["metadatas"])
        seen: dict[str, dict] = {}
        for m in res["metadatas"]:
            did = m["doc_id"]
            item = seen.setdefault(did, {"doc_id": did, "doc_name": m.get("doc_name", did), "chunks": 0})
            item["chunks"] += 1
        return sorted(seen.values(), key=lambda x: x["doc_name"])
