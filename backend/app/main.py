"""FastAPI 入口。

开发：
    uv run uvicorn backend.app.main:app --reload --port 8000
    （前端另起：cd frontend && npm run dev）

生产（单进程同时供 API 与前端静态文件）：
    cd frontend && npm run build
    uv run uvicorn backend.app.main:app --port 8000
    浏览器打开 http://127.0.0.1:8000
"""

from __future__ import annotations

from pathlib import Path

from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import FileResponse
from fastapi.staticfiles import StaticFiles

from .api import router as api_router
from .config import DEEPSEEK_API_KEY, ROOT

app = FastAPI(title="学期助手 API", version="0.2.0")

# 前端本地开发端口
app.add_middleware(
    CORSMiddleware,
    allow_origins=[
        "http://localhost:5173",
        "http://127.0.0.1:5173",
        "http://localhost:8501",
        "http://127.0.0.1:8501",
        f"http://localhost:8000",
        f"http://127.0.0.1:8000",
    ],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(api_router)


@app.get("/health")
def health() -> dict:
    """存活检查。不因为缺 API key 而失败，只如实报告状态。"""
    return {
        "status": "ok",
        "llm_configured": bool(DEEPSEEK_API_KEY),
    }


# ---------------------------------------------------------------- 前端静态文件
# 只在 frontend/dist 存在时挂载，保证没构建过也能跑 API。

_DIST = ROOT / "frontend" / "dist"

if (_DIST / "assets").is_dir():
    app.mount("/assets", StaticFiles(directory=_DIST / "assets"), name="assets")


@app.get("/{full_path:path}", include_in_schema=False)
def spa_fallback(full_path: str):
    """前端单页应用：非 /api 的路径一律交给 index.html（404 也交给它做路由）。"""
    # /api 下不存在的路径不能落到 index.html —— 前端拿到一段 HTML 去 JSON.parse，
    # 报的错会让人完全摸不着头脑；这里如实返回 404。
    if full_path.startswith("api/") or full_path == "health":
        raise HTTPException(status_code=404, detail="接口不存在。")
    if not _DIST.is_dir():
        return {"detail": "前端尚未构建。开发时请用 Vite dev server（npm run dev）。"}
    target = _DIST / full_path
    if full_path and target.is_file():
        return FileResponse(target)
    index = _DIST / "index.html"
    if index.is_file():
        return FileResponse(index)
    return {"detail": "前端尚未构建。"}
