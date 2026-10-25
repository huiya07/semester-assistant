"""学期助手 —— Streamlit 界面。

运行：
    uv run streamlit run app.py

阶段一用 Streamlit 验证完整闭环（上传 → 提问 → 带页码引用 → 周视图），
最终版再迁到 React。讨论见 docs/决策记录.md D4。
"""

from __future__ import annotations

import tempfile
from datetime import date
from pathlib import Path

import streamlit as st

from backend.app.chunker import chunk_doc
from backend.app.parser import NoTextLayerError, parse_pdf
from backend.app.qa import answer
from backend.app.semester import week_view
from backend.app.store import Store

st.set_page_config(page_title="学期助手", page_icon="📚", layout="wide")


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
            tmp = Path(tempfile.gettempdir()) / f"upload_{up.name}"
            tmp.write_bytes(up.getbuffer())
            try:
                doc = parse_pdf(tmp)
            except NoTextLayerError as e:
                st.error(str(e))
            else:
                store.delete_doc(doc.doc_id)
                n = store.upsert(chunk_doc(doc))
                st.success(f"已入库：{doc.filename}\n\n{doc.page_count} 页 · {n} 个片段")

    st.divider()
    docs = store.docs()
    st.caption(f"资料库：{len(docs)} 篇 / {store.count()} 个片段")
    for d in docs:
        st.caption(f"· {d['doc_name']}（{d['chunks']} 片）")
    if not docs:
        st.caption("还是空的，先传一份 PDF。")

# ---------------- 主区 ----------------
tab_ask, tab_week = st.tabs(["💬 资料问答", "📅 这周该做什么"])

with tab_ask:
    if "history" not in st.session_state:
        st.session_state.history = []

    if not st.session_state.history:
        st.markdown("#### 试试问：")
        st.markdown(
            "- 习题 1.1 有哪些题目\n"
            "- How many attention heads does the base model use?\n"
            "- 这份资料里没有的内容（看它会不会老实说找不到）"
        )

    for item in st.session_state.history:
        with st.chat_message("user"):
            st.markdown(item["q"])
        with st.chat_message("assistant"):
            st.markdown(item["text"])
            if item["status"] == "not_found" and item.get("searched"):
                st.caption("🔍 " + item["searched"])
            for c in item["citations"]:
                with st.expander(f"📄 出处 [{c['index']}] · 第 {c['page_no']} 页"):
                    st.write(c["text"])

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
                    {"index": c.index, "page_no": c.page_no, "text": c.text}
                    for c in res.citations
                ],
                "searched": "；".join(res.searched),
            }
        )
        st.rerun()

with tab_week:
    view = week_view(date.today())
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

    if view["upcoming"]:
        st.divider()
        st.markdown("**接下来两周要交**")
        for a in view["upcoming"]:
            st.markdown(f"- `{a['due_date']}` **{a['course']}** · {a['title']}")
    else:
        st.divider()
        st.caption("接下来两周没有到期作业。")
