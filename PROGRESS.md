# 进度状态（跨会话唯一真相）

> **给新会话的 AI：先读这个文件，再读 `docs/plans/2026-10-23-semester-assistant.md`。**
> 用户开场白通常是「读 PROGRESS.md，继续 Task N」。不要去重新调研比赛规则（摘要见 `docs/比赛要求摘要.md`），不要重新讨论已定决策（见 `docs/决策记录.md`）。
> **待办与缺口看 `docs/待办.md`**，不要翻历史对话。

**最后更新：** 2026-10-25
**当前状态：** Task 1、2、3、4、6、7a 完成。Streamlit 界面端到端跑通（上传 → 提问 → 引用卡片 → 周视图），AppTest 验证 0 异常
**当前任务：** Task 9（作品介绍文档 + 演示视频）——**预指导要交的就是这两样**
**下一步具体动作：** 写预指导版作品介绍文档（7 项要求）→ 录 3~5 分钟演示视频 → 传 B 站
**已完成的任务：** Task 1（骨架）、Task 2（解析与切片）、Task 3（向量检索）、Task 4（问答与抗幻觉）、Task 6（Streamlit 界面）、Task 7a（课表 + 作业 + 周视图）
**已冻结的接口：**
- `config.py`：`ROOT`、`DEEPSEEK_API_KEY`、`DEEPSEEK_BASE_URL`、`DEEPSEEK_MODEL`、`CHROMA_DIR`、`DATA_DIR`、`SEMESTER_START`、`require_api_key()`
- `main.py`：`app`（FastAPI 实例），`GET /health` → `{status, llm_configured}`
- `semester.py`：`load_courses()`、`load_assignments()`、`week_no(d)`、`week_monday(d)`、`assignments_due_on(d)`、`upcoming_assignments(d, within_days=14)`、`week_view(d) -> dict{week_no, monday, days[], course_count, upcoming[], before_semester}`，每天 `{date, weekday, is_today, courses[], due[]}`
- `parser.py`：`NoTextLayerError`、`file_doc_id(path) -> str`、`parse_pdf(path) -> ParsedDoc{doc_id, filename, pages[{page_no, text}], blank_pages[]}`，另有属性 `page_count`、`text_length`
- `chunker.py`：`chunk_doc(doc, size=600, overlap=80) -> list[Chunk{chunk_id, doc_id, doc_name, page_no, ordinal, text}]`；不跨页；优先在句末/空行断开；chunk_id 形如 `{doc_id}-p{page}-{ordinal:03d}`
- `embedding.py`：`BGEEmbeddingFunction`（BAAI/bge-small-zh-v1.5，**512 维**，`embed_documents` 不加前缀 / `embed_query` 加指令前缀）、`MODEL_TAG="bge_zh"`、`MODEL_NAME`
- `store.py`：`Store(path?)`、`upsert(chunks) -> int`、`delete_doc(doc_id)`、`search(query, top_k=5) -> list[Hit{chunk_id, doc_id, doc_name, page_no, text, distance, score}]`、`count()`、`docs()[{doc_id, doc_name, chunks}]`；集合名 `chunks_bge_zh_v1`；数据在 `chroma_data/`（gitignore）
- `qa.py`：`answer(question, top_k=8, store?) -> Answer{status: ok|not_found|error, text, citations[{index, chunk_id, doc_id, doc_name, page_no, text}], related[], searched[], best_distance}`；`MAX_DISTANCE=0.65`；`NO_ANSWER_MARK`；三层防线（阈值拦截 / prompt 约束 / 引用编号校验）+ 同文档优先 `_select_context`
- `app.py`：Streamlit 界面，`uv run streamlit run app.py`，两个 tab（资料问答 / 这周该做什么）
- `data/courses.json`：`{_meta, courses[{name, day, start_section, end_section, weeks[], start_time, end_time}]}`（已脱敏，无教师/教室）
- `data/assignments.json`：`{_meta, assignments[{id, course, title, due_date}]}`（示例数据，课程名对应真实课表，内容虚构）
- CLI：`week [YYYY-MM-DD]`、`parse <pdf>`、`index <pdf>`、`search <问题>`、`ask <问题>`、`stats`
**已放弃：** 「第三章是哪周学的」——课表不含教学进度，数据不支持（见决策记录 D10 追加项）
**阻塞项：** 无。**硬期限：2026-10-31 15:00 预指导提交**（源码网盘 + 介绍文档 + B 站视频）

## 更新规则

每完成一个 Task，必须回来改这四个字段：
1. `最后更新` 日期
2. `当前任务` → 下一项
3. `已完成的任务` 追加
4. `已冻结的接口` —— 已完成模块的函数签名，防止后续任务漂移

## 环境备忘

- 项目根目录：本仓库根（跨会话时用 git 仓库位置定位，不写死绝对路径）
- **报名信息（UID、姓名、学校、手机号）在 `local/提交信息.md`，该目录已被 `.gitignore` 排除，绝不提交公开仓库，文档里也不要写具体号码**
- 网盘账号、B 站账号已就绪
- Python 用 `uv`；venv 与 torch 依赖放 **D 盘**，不占 C 盘
- **改 `backend/` 下的代码后必须重启 Streamlit 进程**：它的热重载只重跑 `app.py`，不会重新 import 后端模块，
  否则会出现「类已更新但进程里还是旧类」的 AttributeError（2026-10-25 实际踩过）
- 所有脚本用 `pwsh` 执行
- 本地运行，不部署公网
- DeepSeek key 放 `.env`，仓库 Public，`.env` 永不提交
