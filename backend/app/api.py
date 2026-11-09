"""REST API —— React 前端的接口层。

设计原则：
1. 只做「路由 + 序列化」，业务逻辑仍在 parser / chunker / store / qa / semester 里，
   不把规则复制一份到这里（否则两套逻辑迟早漂移）。
2. Store 是重量级单例（构造时要加载嵌入模型），进程内只建一次。
   Chroma 的写入不是线程安全的，所以写操作统一走同一把锁。
3. 不回传 API Key —— 只回 `has_key: bool`。

挂在 `main.py` 的 `/api` 前缀下。
"""

from __future__ import annotations

import json
import re
import shutil
import tempfile
import threading
from datetime import date, datetime
from pathlib import Path

from fastapi import APIRouter, File, HTTPException, UploadFile
from fastapi.responses import Response, StreamingResponse
from pydantic import BaseModel, Field
from starlette.background import BackgroundTask

from .chunker import chunk_doc
from .parser import NoTextLayerError, parse_pdf
from .qa import answer, answer_stream
from .render import page_count, render_page
from .semester import (
    USER_DATA_DIR,
    load_assignments,
    load_courses,
    reload_data,
    validate_assignments,
    validate_courses,
    week_view,
)
from .settings import LLMSettings, clear as clear_settings, load as load_settings, save as save_settings
from .store import Store

router = APIRouter(prefix="/api", tags=["api"])

# ---------------------------------------------------------------- Store 单例

_store_lock = threading.Lock()
_write_lock = threading.Lock()
# 同一时刻只允许一个问答在进行：并发进来既费钱，也会让 Chroma 同时被读
_ask_lock = threading.Lock()
_store: Store | None = None


def get_store() -> Store:
    global _store
    if _store is None:
        with _store_lock:
            if _store is None:
                _store = Store()
    return _store


# ---------------------------------------------------------------- 请求体

class SettingsIn(BaseModel):
    base_url: str = ""
    api_key: str = ""
    model: str = ""


class AskIn(BaseModel):
    question: str = Field(min_length=1)


class CoursesIn(BaseModel):
    courses: list[dict]


class AssignmentsIn(BaseModel):
    assignments: list[dict]


# ---------------------------------------------------------------- 设置

@router.get("/settings")
def get_settings() -> dict:
    s = load_settings()
    return {
        "base_url": s.base_url,
        "model": s.model,
        "has_key": s.ready,
    }


@router.put("/settings")
def put_settings(body: SettingsIn) -> dict:
    now = load_settings()
    new_key = body.api_key.strip() or now.api_key
    if not new_key.strip():
        raise HTTPException(status_code=400, detail="API Key 不能为空。")
    save_settings(
        LLMSettings(
            base_url=(body.base_url or now.base_url).strip(),
            api_key=new_key,
            model=(body.model or now.model).strip(),
        )
    )
    return {"ok": True, "message": "已保存，下一条消息生效。"}


@router.post("/settings/clear")
def post_settings_clear() -> dict:
    clear_settings()
    return {"ok": True, "message": "已清除界面配置，回退到 .env。"}


# ---------------------------------------------------------------- 资料库

@router.get("/library")
def get_library() -> dict:
    store = get_store()
    return {"docs": store.docs(), "total_chunks": store.count()}


@router.post("/library/upload")
def post_upload(file: UploadFile = File(...)) -> dict:
    store = get_store()
    name = file.filename or "upload.pdf"
    tmpdir = Path(tempfile.mkdtemp())
    tmp = tmpdir / Path(name).name
    try:
        # 上限定在 50 MB：整份读进内存，没有上限时一个超大文件就能打爆进程
        raw = file.file.read(MAX_UPLOAD_BYTES + 1)
        if len(raw) > MAX_UPLOAD_BYTES:
            raise HTTPException(status_code=413, detail="文件超过 50 MB，请拆分后再上传。")
        tmp.write_bytes(raw)
        try:
            doc = parse_pdf(tmp)
        except NoTextLayerError as e:
            raise HTTPException(status_code=422, detail=str(e)) from e
        except Exception as e:
            raise HTTPException(
                status_code=422,
                detail=f"无法解析 {name}：{type(e).__name__}。请确认是完整的 PDF 文件。",
            ) from e

        with _write_lock:
            pdf_file = store.store_pdf(tmp, doc.doc_id)
            # 先写后清：写入失败时旧数据还在，不会整篇消失
            n = store.replace_chunks(doc.doc_id, chunk_doc(doc), pdf_file)
        return {
            "doc_id": doc.doc_id,
            "doc_name": doc.filename,
            "pages": doc.page_count,
            "chunks": n,
        }
    finally:
        shutil.rmtree(tmpdir, ignore_errors=True)


@router.delete("/library/{doc_id}")
def delete_doc(doc_id: str) -> dict:
    with _write_lock:
        get_store().purge_document(doc_id)
    return {"ok": True}


# ---------------------------------------------------------------- 问答

def _answer_payload(a) -> dict:
    return {
        "status": a.status,
        "text": a.text,
        "citations": [
            {
                "index": c.index, "doc_id": c.doc_id, "doc_name": c.doc_name,
                "page_no": c.page_no, "text": c.text, "pdf_file": c.pdf_file,
            }
            for c in a.citations
        ],
        "related": [
            {
                "index": c.index, "doc_id": c.doc_id, "doc_name": c.doc_name,
                "page_no": c.page_no, "text": c.text, "pdf_file": c.pdf_file,
            }
            for c in a.related
        ],
        "searched": a.searched,
        "best_distance": a.best_distance,
    }


BUSY_DETAIL = "上一个问题还在回答中，等它说完再问。"
MAX_UPLOAD_BYTES = 50 * 1024 * 1024


@router.post("/ask")
def post_ask(body: AskIn) -> dict:
    if not _ask_lock.acquire(blocking=False):
        raise HTTPException(status_code=429, detail=BUSY_DETAIL)
    try:
        store = get_store()
        started = datetime.now()
        res = answer(body.question, store=store)
        payload = _answer_payload(res)
        payload["elapsed"] = round((datetime.now() - started).total_seconds(), 1)
        return payload
    finally:
        _ask_lock.release()


@router.post("/ask/stream")
def post_ask_stream(body: AskIn) -> StreamingResponse:
    if not _ask_lock.acquire(blocking=False):
        raise HTTPException(status_code=429, detail=BUSY_DETAIL)
    store = get_store()

    # 双保险：客户端中途断开时 Starlette 不保证把生成器消费完，
    # 只靠 gen 的 finally 会漏锁（实测断开后 9 秒仍 429）。
    # 因此再用 BackgroundTask 兜底，并用标志位防止重复 release。
    released = False

    def release() -> None:
        nonlocal released
        if not released:
            released = True
            _ask_lock.release()

    def gen():
        try:
            for ev in answer_stream(body.question, store=store):
                yield f"data: {json.dumps(ev, ensure_ascii=False)}\n\n"
        except Exception as e:  # 兜底：不让生成器异常把连接吊死
            yield (
                "data: "
                + json.dumps(
                    {"type": "error", "text": "服务端异常。", "detail": type(e).__name__},
                    ensure_ascii=False,
                )
                + "\n\n"
            )
        finally:
            release()
        yield "data: [DONE]\n\n"

    return StreamingResponse(
        gen(),
        media_type="text/event-stream",
        headers={
            "Cache-Control": "no-cache",
            "X-Accel-Buffering": "no",  # 防 nginx 类代理攒包
        },
        background=BackgroundTask(release),
    )


# ---------------------------------------------------------------- 原页图

@router.get("/page-count/{doc_id}")
def get_page_count(doc_id: str) -> dict:
    path = _pdf_path(doc_id)
    if path is None:
        raise HTTPException(status_code=404, detail="原件不存在。")
    return {"total": page_count(path)}


# file_doc_id 的产出固定是 12 位小写十六进制。只放行这个形状，
# 挡住 "../" 一类拼进文件路径的输入（实测未校验时能落到 SPA 通配路由，行为不可控）。
_DOC_ID_RE = re.compile(r"^[0-9a-f]{12}$")


def _pdf_path(doc_id: str) -> Path | None:
    """按 doc_id 找留底原件。文件名就是 {doc_id}.pdf。"""
    from .config import PDF_STORE_DIR

    if not _DOC_ID_RE.fullmatch(doc_id):
        return None
    p = PDF_STORE_DIR / f"{doc_id}.pdf"
    return p if p.exists() else None


@router.get("/page/{doc_id}/{page_no}")
def get_page(doc_id: str, page_no: int, dpi: int = 110) -> Response:
    path = _pdf_path(doc_id)
    if path is None:
        raise HTTPException(status_code=404, detail="原件已被删除。")
    # 不限制的话 ?dpi=2000 能把内存和 CPU 打满
    dpi = max(50, min(int(dpi), 300))
    png = render_page(path, page_no, dpi=dpi)
    if png is None:
        raise HTTPException(status_code=404, detail=f"第 {page_no} 页无法读取。")
    return Response(
        content=png,
        media_type="image/png",
        headers={"Cache-Control": "public, max-age=3600"},
    )


# ---------------------------------------------------------------- 学期视图

@router.get("/semester")
def get_semester(day: str | None = None) -> dict:
    try:
        d = date.fromisoformat(day) if day else date.today()
    except ValueError as e:
        raise HTTPException(status_code=400, detail="日期格式应为 YYYY-MM-DD。") from e
    try:
        return week_view(d)
    except Exception as e:
        raise HTTPException(
            status_code=500,
            detail=f"课表数据有误：{type(e).__name__}: {e}",
        ) from e


@router.get("/semester/meta")
def get_semester_meta() -> dict:
    user_c = USER_DATA_DIR / "courses.json"
    user_a = USER_DATA_DIR / "assignments.json"
    return {
        "courses": len(load_courses()),
        "assignments": len(load_assignments()),
        "custom_courses": user_c.exists(),
        "custom_assignments": user_a.exists(),
    }


@router.put("/semester/courses")
def put_courses(body: CoursesIn) -> dict:
    data = {"courses": body.courses}
    ok, err = validate_courses(data)
    if not ok:
        raise HTTPException(status_code=422, detail=err)
    USER_DATA_DIR.mkdir(parents=True, exist_ok=True)
    (USER_DATA_DIR / "courses.json").write_text(
        json.dumps(data, ensure_ascii=False, indent=2), encoding="utf-8"
    )
    reload_data()
    return {"ok": True, "count": len(body.courses)}


@router.put("/semester/assignments")
def put_assignments(body: AssignmentsIn) -> dict:
    data = {"assignments": body.assignments}
    ok, err = validate_assignments(data)
    if not ok:
        raise HTTPException(status_code=422, detail=err)
    USER_DATA_DIR.mkdir(parents=True, exist_ok=True)
    (USER_DATA_DIR / "assignments.json").write_text(
        json.dumps(data, ensure_ascii=False, indent=2), encoding="utf-8"
    )
    reload_data()
    return {"ok": True, "count": len(body.assignments)}


@router.post("/semester/reset")
def post_semester_reset() -> dict:
    for p in (USER_DATA_DIR / "courses.json", USER_DATA_DIR / "assignments.json"):
        p.unlink(missing_ok=True)
    reload_data()
    return {"ok": True, "message": "已恢复默认数据。"}
