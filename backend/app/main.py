"""FastAPI 入口。

启动：uv run uvicorn backend.app.main:app --reload
"""

from __future__ import annotations

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from .config import DEEPSEEK_API_KEY

app = FastAPI(title="学期助手 API", version="0.1.0")

# 前端本地开发端口，按需增删
app.add_middleware(
    CORSMiddleware,
    allow_origins=[
        "http://localhost:5173",
        "http://127.0.0.1:5173",
        "http://localhost:8501",
        "http://127.0.0.1:8501",
    ],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


@app.get("/health")
def health() -> dict:
    """存活检查。不因为缺 API key 而失败，只如实报告状态。"""
    return {
        "status": "ok",
        "llm_configured": bool(DEEPSEEK_API_KEY),
    }
