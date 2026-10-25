# 进度状态（跨会话唯一真相）

> **给新会话的 AI：先读这个文件，再读 `docs/plans/2026-10-23-semester-assistant.md`。**
> 用户开场白通常是「读 PROGRESS.md，继续 Task N」。不要去重新调研比赛规则（摘要见 `docs/比赛要求摘要.md`），不要重新讨论已定决策（见 `docs/决策记录.md`）。

**最后更新：** 2026-10-25
**当前状态：** Task 1、2、3、4、7a 完成。问答五个用例全过（有答案 / 库外 / 空库 / 中文 / 相关但无答案）；`.env` 已配置并实测调通 DeepSeek
**当前任务：** Task 6（界面）——**预指导提交需要能演示的东西，界面优先于 API 层**
**下一步具体动作：** Streamlit 单页：上传 PDF + 提问 + 引用卡片 + 学期视图；后端直接调 `qa.answer()`，暂不起 FastAPI
**已完成的任务：** Task 1（骨架）、Task 2（解析与切片）、Task 3（向量检索）、Task 4（问答与抗幻觉）、Task 7a（课表 + 作业 + 周视图 CLI）
**已冻结的接口：**
- `config.py`：`ROOT`、`DEEPSEEK_API_KEY`、`DEEPSEEK_BASE_URL`、`DEEPSEEK_MODEL`、`CHROMA_DIR`、`DATA_DIR`、`SEMESTER_START`、`require_api_key()`
- `main.py`：`app`（FastAPI 实例），`GET /health` → `{status, llm_configured}`
- `semester.py`：`load_courses()`、`load_assignments()`、`week_no(d)`、`week_monday(d)`、`assignments_due_on(d)`、`upcoming_assignments(d, within_days=14)`、`week_view(d) -> dict{week_no, monday, days[], course_count, upcoming[]}`，每天 `{date, weekday, is_today, courses[], due[]}`
- `parser.py`：`NoTextLayerError`、`file_doc_id(path) -> str`、`parse_pdf(path) -> ParsedDoc{doc_id, filename, pages[{page_no, text}], blank_pages[]}`，另有属性 `page_count`、`text_length`
- `chunker.py`：`chunk_doc(doc, size=600, overlap=80) -> list[Chunk{chunk_id, doc_id, page_no, ordinal, text}]`；不跨页；优先在句末/空行断开；chunk_id 形如 `{doc_id}-p{page}-{ordinal:03d}`
- `embedding.py`：`BGEEmbeddingFunction`（BAAI/bge-small-zh-v1.5，384 维，`embed_documents` 不加前缀 / `embed_query` 加指令前缀）、`MODEL_TAG="bge_zh"`、`MODEL_NAME`
- `store.py`：`Store(path?)`、`upsert(chunks) -> int`、`delete_doc(doc_id)`、`search(query, top_k=5) -> list[Hit{chunk_id, doc_id, page_no, text, distance, score}]`、`count()`、`docs()`；集合名 `chunks_bge_zh_v1`；数据在 `chroma_data/`（gitignore）
- `qa.py`：`answer(question, top_k=8, store?) -> Answer{status, text, citations[{index, chunk_id, doc_id, page_no, text}], searched[], best_distance}`；`MAX_DISTANCE=0.65`；`NO_ANSWER_MARK`；三层防线（阈值拦截 / prompt 约束 / 引用编号校验）
- CLI：`week [YYYY-MM-DD]`、`parse <pdf>`、`index <pdf>`、`search <问题>`、`ask <问题>`、`stats`
- `data/courses.json`：`{_meta, courses[{name, day, start_section, end_section, weeks[], start_time, end_time}]}`（已脱敏，无教师/教室）
- `data/assignments.json`：`{_meta, assignments[{id, course, title, due_date}]}`（示例数据，课程名对应真实课表，内容虚构）
- CLI：`uv run python -m backend.cli week [YYYY-MM-DD]`
**已放弃：** 「第三章是哪周学的」——课表不含教学进度，数据不支持（见决策记录 D10 追加项）
**阻塞项：** 无。**硬期限：2026-10-31 15:00 预指导提交**（源码网盘 + 介绍文档 + B 站视频）

## 更新规则

每完成一个 Task，必须回来改这四个字段：
1. `最后更新` 日期
2. `当前任务` → 下一项
3. `已完成的任务` 追加
4. `已冻结的接口` —— 已完成模块的函数签名，防止后续任务漂移

## 环境备忘

- 项目根目录：`D:\maybe\work\semester-assistant`
- **报名信息（UID 2119569、姓名、学校、手机号）在 `local/提交信息.md`，该目录已被 `.gitignore` 排除，绝不提交公开仓库**
- 网盘账号、B 站账号已就绪
- Python 用 `uv`；venv 与 torch 依赖放 **D 盘**，不占 C 盘
- 所有脚本用 `pwsh` 执行
- 本地运行，不部署公网
- DeepSeek key 放 `.env`，仓库 Public，`.env` 永不提交
