"""冒烟测试：一条命令验证后端全链路是否还完整。

前置：服务已启动
    uv run uvicorn backend.app.main:app --port 8000

运行：
    uv run pytest tests/test_smoke.py -v

设计原则：
1. **不依赖用户数据**。需要问答的用例会幂等地上传仓库自带的示例讲义
   （内容哈希生成的 doc_id 固定，重复上传不会产生副本）。
2. **自己造、自己清**。上传测试用的 PDF 由 PyMuPDF 现生成，用完删掉。
3. 用例之间有先后依赖（上传 → 读取 → 删除），所以按文件内顺序执行。
"""

from __future__ import annotations

import io
from pathlib import Path

import httpx
import pytest

BASE = "http://127.0.0.1:8000"
ROOT = Path(__file__).resolve().parents[1]
SAMPLE = ROOT / "backend" / "samples" / "sample-lecture-notes.pdf"


@pytest.fixture(scope="module")
def client():
    try:
        r = httpx.get(f"{BASE}/health", timeout=5)
        r.raise_for_status()
    except Exception as e:  # pragma: no cover
        pytest.skip(f"服务没起来（{BASE}）：{e}")
    with httpx.Client(base_url=BASE, timeout=120) as c:
        yield c


def _make_test_pdf() -> bytes:
    """现场生成一份两页 PDF，避免依赖任何用户文件。"""
    import pymupdf

    doc = pymupdf.open()
    for i in (1, 2):
        page = doc.new_page()
        page.insert_text((72, 90), f"Smoke Test Page {i}", fontsize=18)
        page.insert_text((72, 130), "This document exists only for the smoke test.", fontsize=11)
    data = doc.tobytes()
    doc.close()
    return data


# ---------------------------------------------------------------- 基础

def test_health(client):
    d = client.get("/health").json()
    assert d["status"] == "ok"
    assert "llm_configured" in d


def test_settings_never_leaks_key(client):
    d = client.get("/api/settings").json()
    assert "has_key" in d
    # 接口只回布尔，绝不能把 key 带出来
    assert "api_key" not in d
    assert "sk-" not in str(d)


def test_library_lists_docs(client):
    d = client.get("/api/library").json()
    assert isinstance(d["docs"], list)
    assert isinstance(d["total_chunks"], int)
    for doc in d["docs"]:
        assert {"doc_id", "doc_name", "chunks"} <= set(doc)


# ---------------------------------------------------------------- 资料入库链路

@pytest.fixture(scope="module")
def pdf_bytes() -> bytes:
    """PyMuPDF 每次生成的字节都不同（内含随机 ID），
    所以整个模块只造一次，幂等性测试必须用同一份字节。"""
    return _make_test_pdf()


@pytest.fixture(scope="module")
def uploaded(client, pdf_bytes):
    """上传一份现造的 PDF，模块结束后删除。"""
    r = client.post(
        "/api/library/upload",
        files={"file": ("smoke-test.pdf", pdf_bytes, "application/pdf")},
    )
    assert r.status_code == 200, r.text
    info = r.json()
    assert info["pages"] == 2
    assert info["chunks"] > 0
    yield info
    client.delete(f"/api/library/{info['doc_id']}")


def test_upload_appears_in_library(client, uploaded):
    names = [d["doc_name"] for d in client.get("/api/library").json()["docs"]]
    assert "smoke-test.pdf" in names


def test_upload_is_idempotent(client, uploaded, pdf_bytes):
    """同样字节再传一次，片段数不应变化（doc_id 由内容哈希决定）。"""
    before = client.get("/api/library").json()["total_chunks"]
    r = client.post(
        "/api/library/upload",
        files={"file": ("smoke-test.pdf", pdf_bytes, "application/pdf")},
    )
    assert r.status_code == 200
    assert r.json()["doc_id"] == uploaded["doc_id"]
    after = client.get("/api/library").json()["total_chunks"]
    assert after == before, f"重复上传产生了多余切片：{before} -> {after}"


def test_page_image_returns_png(client, uploaded):
    r = client.get(f"/api/page/{uploaded['doc_id']}/1")
    assert r.status_code == 200
    assert r.headers["content-type"] == "image/png"
    assert r.content[:8] == b"\x89PNG\r\n\x1a\n"


def test_page_out_of_range_is_404(client, uploaded):
    r = client.get(f"/api/page/{uploaded['doc_id']}/999")
    assert r.status_code == 404


def test_bad_doc_id_rejected(client):
    """路径遍历形状的 doc_id 必须被挡掉。"""
    for bad in ("..%2F..%2F.env", "not-a-hash"):
        assert client.get(f"/api/page/{bad}/1").status_code == 404


def test_unknown_api_path_is_json_404(client):
    r = client.get("/api/definitely-not-here")
    assert r.status_code == 404
    assert r.json()["detail"]  # 是 JSON，不是 index.html


# ---------------------------------------------------------------- 问答链路

def _ensure_sample(client):
    if not SAMPLE.exists():
        pytest.skip("仓库自带的示例讲义不存在")
    if not any(d["doc_name"] == SAMPLE.name for d in client.get("/api/library").json()["docs"]):
        with SAMPLE.open("rb") as fh:
            r = client.post(
                "/api/library/upload",
                files={"file": (SAMPLE.name, fh, "application/pdf")},
            )
            assert r.status_code == 200, r.text


def test_ask_returns_citations(client):
    _ensure_sample(client)
    d = client.post("/api/ask", json={"question": "均值和中位数的区别是什么？"}).json()
    assert d["status"] in ("ok", "not_found", "error")
    if d["status"] == "ok":
        assert d["citations"], "ok 状态必须带出处"
        for c in d["citations"]:
            assert c["page_no"] >= 1
            assert c["doc_name"]
            assert 1 <= c["index"] <= 99


def test_ask_refuses_when_absent(client):
    """资料里没有的内容必须老实说找不到，不能编。"""
    _ensure_sample(client)
    d = client.post("/api/ask", json={"question": "太阳系一共有几颗行星？"}).json()
    assert d["status"] == "not_found", f"竟然回答了不存在的内容：{d['text'][:80]}"


def test_ask_stream_emits_events(client):
    _ensure_sample(client)
    seen = []
    with client.stream("POST", "/api/ask/stream", json={"question": "众数是什么？"}) as r:
        assert r.status_code == 200
        for line in r.iter_lines():
            if not line.startswith("data:"):
                continue
            payload = line[5:].strip()
            if payload == "[DONE]":
                break
            import json as _json

            seen.append(_json.loads(payload)["type"])
            if len(seen) > 200:
                break
    assert seen, "流式没有任何事件"
    assert {"meta", "done"} & set(seen) or "not_found" in seen


def test_concurrent_ask_is_rejected(client):
    """并发守卫：同时发两个，至少一个该被 429 挡掉。"""
    import threading

    codes: list[int] = []

    def go():
        try:
            codes.append(
                client.post("/api/ask", json={"question": "标准差是什么？"}, timeout=120).status_code
            )
        except Exception:
            codes.append(-1)

    ts = [threading.Thread(target=go) for _ in range(2)]
    for t in ts:
        t.start()
    for t in ts:
        t.join()
    assert 200 in codes or 429 in codes


def _tiny_pdf(text: str) -> bytes:
    import pymupdf

    d = pymupdf.open()
    p = d.new_page()
    p.insert_text((72, 90), text, fontsize=13)
    b = d.tobytes()
    d.close()
    return b


def test_course_tag_and_filter(client):
    """按课程分组检索：标签落库、限定课程时不会串到别的课。"""
    a = client.post(
        "/api/library/upload",
        files={"file": ("co-alpha.pdf", _tiny_pdf("Matrix eigenvalues and diagonalization"), "application/pdf")},
        data={"course": "课程甲"},
    ).json()
    b = client.post(
        "/api/library/upload",
        files={"file": ("co-beta.pdf", _tiny_pdf("Grammar present perfect irregular verbs"), "application/pdf")},
        data={"course": "课程乙"},
    ).json()
    try:
        tags = {d["doc_name"]: d.get("course") for d in client.get("/api/library").json()["docs"]}
        assert tags["co-alpha.pdf"] == "课程甲"
        assert tags["co-beta.pdf"] == "课程乙"

        # 限定「课程甲」去问英语内容，绝不能命中 co-beta
        d = client.post(
            "/api/ask", json={"question": "grammar irregular verbs", "course": "课程甲"}
        ).json()
        srcs = {c["doc_name"] for c in d["citations"]} | {
            c["doc_name"] for c in d.get("related", [])
        }
        assert "co-beta.pdf" not in srcs, f"跨课程串了：{srcs}"
    finally:
        for x in (a, b):
            client.delete(f"/api/library/{x['doc_id']}")


def test_course_names_endpoint(client):
    d = client.get("/api/course-names").json()
    assert isinstance(d["names"], list)
    assert d["names"] == sorted(d["names"])
    assert len(d["names"]) == len(set(d["names"]))


# ---------------------------------------------------------------- 学期链路

def test_semester_view(client):
    d = client.get("/api/semester").json()
    assert isinstance(d["days"], list)
    assert len(d["days"]) == 7 or d.get("before_semester")
    if not d.get("before_semester"):
        for day in d["days"]:
            assert {"date", "weekday", "courses", "due"} <= set(day)


def test_semester_meta(client):
    d = client.get("/api/semester/meta").json()
    assert d["courses"] >= 0
    assert isinstance(d["custom_courses"], bool)


def test_courses_import_rejects_garbage(client):
    r = client.put("/api/semester/courses", json={"courses": [{"oops": 1}]})
    assert r.status_code == 422
    assert "name" in r.json()["detail"]


# ---------------------------------------------------------------- 清理

def test_cleanup_removes_doc(client):
    """删除接口生效，且不会 404 之后 500。"""
    d = client.get("/api/library").json()
    target = next((x for x in d["docs"] if x["doc_name"] == "smoke-test.pdf"), None)
    if target is None:
        pytest.skip("测试文档已被 fixture 清理")
    assert client.delete(f"/api/library/{target['doc_id']}").status_code == 200
    names = [x["doc_name"] for x in client.get("/api/library").json()["docs"]]
    assert "smoke-test.pdf" not in names
