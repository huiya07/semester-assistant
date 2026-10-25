"""中文嵌入模型。

为什么不用 Chroma 自带的 all-MiniLM-L6-v2：实测它对中文完全失效——
问「基础模型用了多少个注意力头」，正确页（p5）没进前 5，返回的是位置编码和参考文献。
英文正确命中 distance ≈ 0.39，中文查询 0.81~0.87，与「完全不相关」同一水平。

所以换成 BAAI/bge-small-zh-v1.5（中文检索专用，512 维，约 92MB）。
模型首次使用时从 HuggingFace 下载，缓存到本机  ~/.cache/huggingface。
"""

from __future__ import annotations

import os
from functools import lru_cache
from pathlib import Path

# 必须在导入 sentence_transformers 之前设置。
# 国内网络直连 HuggingFace 基本不通，默认走镜像；想用官方源可自行设置 HF_ENDPOINT。
os.environ.setdefault("HF_ENDPOINT", "https://hf-mirror.com")

MODEL_NAME = "BAAI/bge-small-zh-v1.5"
MODEL_TAG = "bge_zh"  # 用于区分不同嵌入模型产生的向量

# BGE 官方建议：查 query 时加指令前缀，文档侧不加。中文 v1.5 用这条。
QUERY_INSTRUCTION = "为这个句子生成表示以用于检索相关文章："


def _model_cached() -> bool:
    """模型是否已经在本地缓存。

    sentence-transformers 每次加载都会向镜像站查一次更新，
    网络不好时会让启动卡在重试上（实测遇到过 SSL EOF 重试 5 次）。
    本地已有缓存就直接离线加载，既快又不依赖网络。
    """
    hf_home = Path(os.getenv("HF_HOME", Path.home() / ".cache" / "huggingface"))
    repo_dir = hf_home / "hub" / "models--BAAI--bge-small-zh-v1.5"
    return repo_dir.exists()


if _model_cached():
    os.environ.setdefault("HF_HUB_OFFLINE", "1")
    os.environ.setdefault("TRANSFORMERS_OFFLINE", "1")

from sentence_transformers import SentenceTransformer  # noqa: E402


@lru_cache(maxsize=1)
def _model() -> SentenceTransformer:
    return SentenceTransformer(MODEL_NAME)


class BGEEmbeddingFunction:
    """Chroma 兼容的嵌入函数：返回归一化后的向量，余弦距离直接可用。"""

    def __init__(self) -> None:
        self._loaded: SentenceTransformer | None = None

    @property
    def model(self) -> SentenceTransformer:
        if self._loaded is None:
            self._loaded = _model()
        return self._loaded

    def __call__(self, input):  # noqa: A002 - Chroma 的签名就是 input
        vectors = self.model.encode(
            list(input),
            normalize_embeddings=True,
            convert_to_numpy=True,
            batch_size=32,
            show_progress_bar=False,
        )
        return vectors.tolist()

    # --- Chroma 1.x 要求拆开的两个入口 ---
    def embed_documents(self, input):  # noqa: A002
        """入库侧：不加指令前缀。"""
        return self.__call__(input)

    def embed_query(self, input):  # noqa: A002
        """检索侧：加 BGE 的查询指令前缀。"""
        return self.__call__([QUERY_INSTRUCTION + str(t) for t in input])

    # Chroma 1.x 持久化 collection 时会读这两个属性做校验
    def name(self) -> str:
        return MODEL_TAG

    @staticmethod
    def build_from_config(config: dict) -> "BGEEmbeddingFunction":
        return BGEEmbeddingFunction()

    def get_config(self) -> dict:
        return {"model": MODEL_NAME}

    @staticmethod
    def is_legacy() -> bool:
        return False
