"""学期助手 —— Streamlit 界面。

运行：
    uv run streamlit run app.py

阶段一用 Streamlit 验证完整闭环（上传 → 提问 → 带页码引用 → 周视图），
最终版再迁到 React。讨论见 docs/决策记录.md D4。
"""

from __future__ import annotations

import json
import shutil
import tempfile
from datetime import date
from pathlib import Path

import streamlit as st

from backend.app.chunker import chunk_doc
from backend.app.parser import NoTextLayerError, parse_pdf
from backend.app.qa import answer
from backend.app.render import page_count, render_page
from backend.app.semester import week_view
from backend.app.settings import LLMSettings, load as load_settings, save as save_settings
from backend.app.store import Store

st.set_page_config(page_title="学期助手", page_icon="📚", layout="wide")


@st.dialog("确认删除")
def confirm_delete(doc_id: str, doc_name: str, chunks: int) -> None:
    st.markdown(f"要删除 **《{doc_name}》** 吗？")
    st.caption(f"将删除 {chunks} 个检索片段与留底的原件，并清空当前对话。此操作无法撤销。")
    col_yes, col_no = st.columns(2)
    if col_yes.button("确认删除", type="primary", use_container_width=True):
        get_store().purge_document(doc_id)
        st.session_state.pop("history", None)
        st.rerun()
    if col_no.button("取消", use_container_width=True):
        st.rerun()


def show_citation(c, title_prefix: str, key_prefix: str) -> None:
    """出处卡片：默认收起。

    展开后：
    1. 多页文档提示「当前只展示第 N 页 / 共 M 页」，避免误以为这就是全部
    2. 你问到的片段
    3. 一个控件选原页显示范围（不展开 / 仅该页 / 全部页）

    key_prefix 必须在整页内唯一（用「消息序号 + 卡片类型」），
    否则 citations 与 related、或不同消息之间会撞 key。
    """
    total = page_count(Path(c["pdf_file"])) if c.get("pdf_file") else 0

    with st.expander(f"{title_prefix} · 《{c['doc_name']}》第 {c['page_no']} 页"):
        if total > 1:
            st.caption(
                f"⚠ 本文档共 {total} 页，下面是**第 {c['page_no']} 页**，不是全文。"
            )

        st.caption("🎯 你问到的部分")
        st.info(c["text"])

        pdf = Path(c["pdf_file"]) if c.get("pdf_file") else None
        base_key = f"{key_prefix}_{c['page_no']}_{c['index']}"

        if total <= 1:
            if st.toggle("🔍 查看原页", key=base_key + "_one"):
                png = render_page(pdf, c["page_no"]) if pdf else None
                if png:
                    st.image(png, width="stretch")
                else:
                    st.caption("（原件不在本地）")
            return

        # 多页文档：一个控件决定范围，避免「单页」和「全部」各渲染一次
        scope = st.radio(
            "原页显示范围",
            options=["不展开", f"仅第 {c['page_no']} 页", f"全部 {total} 页"],
            horizontal=True,
            key=base_key + "_radio",
            label_visibility="collapsed",
        )
        if scope == "不展开":
            return
        if scope.startswith("仅"):
            pages = [c["page_no"]]
        else:
            if total > 20:
                st.caption(f"共 {total} 页，页数较多，只展开前 20 页 + 当前页")
                pages = list(range(1, 21))
                if c["page_no"] not in pages:
                    pages.append(c["page_no"])  # 命中的页必须在里面
            else:
                pages = list(range(1, total + 1))

        for p in pages:
            png = render_page(pdf, p) if pdf else None
            if png:
                if len(pages) > 1:
                    st.caption(f"第 {p} 页")
                st.image(png, width="stretch")
            else:
                st.caption(f"（第 {p} 页无法读取）")


@st.cache_resource(show_spinner="正在加载嵌入模型…")
def get_store() -> Store:
    return Store()


store = get_store()

# ---------------- 侧边栏：资料库 ----------------
with st.sidebar:
    st.title("📚 学期助手")
    st.caption("资料问答 · 每条结论都带页码出处")

    up = st.file_uploader("添加资料（PDF）", type=["pdf"])
    if up is not None and st.button("加入资料库", type="primary", use_container_width=True):
        with st.spinner("解析并建立索引…"):
            # 用独立临时目录并保留原文件名：doc_name 取自文件名，
            # 否则侧边栏和出处会显示成 upload_xxx.pdf
            tmpdir = Path(tempfile.mkdtemp())
            tmp = tmpdir / up.name
            try:
                tmp.write_bytes(up.getbuffer())
                doc = parse_pdf(tmp)
            except NoTextLayerError as e:
                st.error(str(e))
            except Exception as e:  # 损坏文件、0 字节、伪装成 pdf 的其它格式
                st.error(f"无法解析 {up.name}：{type(e).__name__}。请确认是完整的 PDF 文件。")
            else:
                store.delete_doc(doc.doc_id)
                pdf_file = store.store_pdf(tmp, doc.doc_id)
                n = store.upsert(chunk_doc(doc), pdf_file=pdf_file)
                st.success(f"已入库：{doc.filename}\n\n{doc.page_count} 页 · {n} 个片段")
            finally:
                shutil.rmtree(tmpdir, ignore_errors=True)

    st.divider()
    docs = store.docs()
    st.caption(f"资料库：{len(docs)} 篇 / {store.count()} 个片段")
    for d in docs:
        col_name, col_del = st.columns([5, 1], vertical_alignment="center")
        col_name.caption(f"· {d['doc_name']}（{d['chunks']} 片）")
        if col_del.button(
            "🗑", key=f"del_{d['doc_id']}", help=f"删除《{d['doc_name']}》"
        ):
            confirm_delete(d["doc_id"], d["doc_name"], d["chunks"])
    if not docs:
        st.caption("还是空的，先传一份 PDF。")

# ---------------- 主区顶部：模型配置 ----------------
settings_now = load_settings()
with st.expander(
    "⚙ 模型配置" + ("" if settings_now.ready else " · ⚠ 还没配置 Key，点这展开"),
    expanded=not settings_now.ready,
):
    st.caption("支持任何 OpenAI 兼容端点。保存后写入 `local/settings.json`，不进仓库。")

    if cfg_msg := st.session_state.pop("cfg_msg", None):
        (st.success if cfg_msg[0] == "success" else st.info)(cfg_msg[1])

    with st.form("llm_settings"):
        base_url = st.text_input("API Base URL", value=settings_now.base_url)
        api_key = st.text_input(
            "API Key",
            value="",
            type="password",
            placeholder="已配置，留空表示不改" if settings_now.ready else "sk-...",
            key="cfg_api_key",
        )
        model = st.text_input("模型名", value=settings_now.model)
        col_save, col_clear = st.columns(2)
        submitted = col_save.form_submit_button("保存", type="primary", use_container_width=True)
        cleared = col_clear.form_submit_button("清除（回退到 .env）", use_container_width=True)

    if submitted:
        new_key = api_key.strip() or settings_now.api_key
        if not new_key:
            st.error("API Key 不能为空。")
        else:
            save_settings(LLMSettings(base_url.strip(), new_key, model.strip()))
            st.session_state["cfg_msg"] = ("success", "已保存，下一条消息生效。")
            st.rerun()
    if cleared:
        from backend.app.settings import clear as clear_settings

        clear_settings()
        st.session_state.pop("cfg_api_key", None)
        st.session_state["cfg_msg"] = ("info", "已清除界面配置，回退到 .env。")
        st.rerun()

# ---------------- 主区 ----------------
tab_ask, tab_week = st.tabs(["💬 资料问答", "📅 这周该做什么"])

with tab_ask:
    if "history" not in st.session_state:
        st.session_state.history = []

    if not st.session_state.history:
        if store.count() == 0:
            st.markdown("### 三步就能用起来")
            st.markdown(
                "**① 加一份资料**　\n"
                "左侧「添加资料」上传 PDF，然后点「加入资料库」。\n"
                "仓库自带一份示例讲义，路径直接复制：\n\n"
                "```text\nbackend/samples/sample-lecture-notes.pdf\n```"
            )
            st.markdown(
                "**② 提问**　\n"
                "在下方输入框问资料里的内容，每个回答都会标 `[1]` 这样的出处。"
            )
            st.markdown(
                "**③ 核对**　\n"
                "点开出处，能看到命中的原文，还可以展开原页对照。"
            )
            st.info("资料里没有的内容，它会直接说找不到，并把最接近的原文摆出来——不会编。")
        else:
            first_doc = store.docs()[0]["doc_name"]
            st.markdown("#### 试试问：")
            st.markdown(
                f"- 这份资料讲了什么？\n"
                f"- 《{first_doc}》的第 1 页说了什么？\n"
                f"- 这份资料里没有的内容（看它会不会老实说找不到）"
            )

    for mi, item in enumerate(st.session_state.history):
        with st.chat_message("user"):
            st.markdown(item["q"])
        with st.chat_message("assistant", avatar="⚠️" if item["status"] == "error" else None):
            if item["status"] == "error":
                st.error(item["text"])
            else:
                st.markdown(item["text"])
            if item["status"] == "not_found" and item.get("searched"):
                st.caption("🔍 " + item["searched"])
            for c in item["citations"]:
                show_citation(c, f"📄 出处 [{c['index']}]", f"m{mi}_cite")
            for c in item.get("related", []):
                show_citation(c, "📄 最接近的内容", f"m{mi}_rel")

    q = st.chat_input("问点什么…")
    if q:
        with st.spinner("检索并回答…"):
            res = answer(q, store=store)
        st.session_state.history.append(
            {
                "q": q,
                "status": res.status,
                "text": res.text,
                "citations": [
                    {
                        "index": c.index,
                        "doc_id": c.doc_id,
                        "doc_name": c.doc_name,
                        "page_no": c.page_no,
                        "text": c.text,
                        "pdf_file": c.pdf_file,
                    }
                    for c in res.citations
                ],
                "related": [
                    {
                        "index": c.index,
                        "doc_id": c.doc_id,
                        "doc_name": c.doc_name,
                        "page_no": c.page_no,
                        "text": c.text,
                        "pdf_file": c.pdf_file,
                    }
                    for c in res.related
                ],
                "searched": "；".join(res.searched),
            }
        )
        st.rerun()

with tab_week:
    st.caption("示例数据 · 可在下方导入自己的课表与作业")
    view = None
    try:
        view = week_view(date.today())
    except Exception as e:  # 数据异常不能把整页打挂，且必须留一条恢复出路
        st.error(f"课表数据有误：{type(e).__name__}: {e}")
        from backend.app.semester import USER_DATA_DIR as _UD, reload_data as _reload

        if st.button("⚠ 恢复默认数据（删除已导入）"):
            for p in (_UD / "courses.json", _UD / "assignments.json"):
                p.unlink(missing_ok=True)
            _reload()
            st.rerun()

    if view is None:
        pass
    elif view.get("before_semester"):
        st.info(f"学期还没开始（开学日 {view['monday']}）。")
    else:
        st.subheader(f"第 {view['week_no']} 周 · {view['monday']} 起")

        cols = st.columns(7)
        for col, day in zip(cols, view["days"]):
            with col:
                st.markdown(f"**{day['weekday']}**" + (" 🔵" if day["is_today"] else ""))
                st.caption(day["date"][5:])
                if not day["courses"] and not day["due"]:
                    st.caption("—")
                    continue
                for c in day["courses"]:
                    st.markdown(f"{c['name']}")
                    st.caption(c["slot"])
                for a in day["due"]:
                    st.markdown(f":red[⚠ {a['course']}]")
                    st.caption(a["title"])

    if view is None:
        pass
    elif view["upcoming"]:
        st.divider()
        st.markdown("**接下来两周要交**")
        for a in view["upcoming"]:
            st.markdown(f"- `{a['due_date']}` **{a['course']}** · {a['title']}")
    else:
        st.divider()
        st.caption("接下来两周没有到期作业。")

    # ---- 导入 / 管理 ----
    st.divider()
    with st.expander("📥 导入 / 管理课表与作业"):
        from backend.app.semester import (
            USER_DATA_DIR,
            load_assignments,
            load_courses,
            reload_data,
            validate_assignments,
            validate_courses,
        )

        user_c = USER_DATA_DIR / "courses.json"
        user_a = USER_DATA_DIR / "assignments.json"
        st.caption(
            f"当前课表：**{len(load_courses())}** 条（{'自定义' if user_c.exists() else '示例'}）　·　"
            f"当前作业：**{len(load_assignments())}** 条（{'自定义' if user_a.exists() else '示例'}）"
        )

        with st.form("import_form"):
            f_c = st.file_uploader("课表 JSON（含 courses 数组）", type=["json"])
            f_a = st.file_uploader("作业 JSON（含 assignments 数组）", type=["json"])
            saved = False
            if st.form_submit_button("保存导入", type="primary"):
                for f, target, key in ((f_c, user_c, "courses"), (f_a, user_a, "assignments")):
                    if f is None:
                        continue
                    try:
                        data = json.loads(f.getvalue().decode("utf-8"))
                    except Exception as e:
                        st.error(f"{f.name} 不是合法 JSON：{e}")
                        continue
                    if isinstance(data, list):
                        data = {key: data}
                    if not isinstance(data, dict) or key not in data:
                        st.error(f"{f.name} 缺少 `{key}` 数组")
                        continue
                    ok, err = (
                        validate_courses(data) if key == "courses" else validate_assignments(data)
                    )
                    if not ok:
                        st.error(f"{f.name} 格式不对：{err}")
                        continue
                    USER_DATA_DIR.mkdir(parents=True, exist_ok=True)
                    target.write_text(
                        json.dumps(data, ensure_ascii=False, indent=2), encoding="utf-8"
                    )
                    saved = True
                if saved:
                    reload_data()
                    st.success("已导入")
                    st.rerun()

        if user_c.exists() or user_a.exists():
            if st.button("恢复默认（删除已导入的数据）"):
                for p in (user_c, user_a):
                    p.unlink(missing_ok=True)
                reload_data()
                st.success("已恢复为仓库自带的示例数据")
                st.rerun()
