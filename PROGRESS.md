# 进度状态（跨会话唯一真相）

> **给新会话的 AI：先读这个文件，再读 `docs/待办.md`。**
> 用户开场白通常是「读 PROGRESS.md，继续」。不要去重新调研比赛规则（摘要见 `docs/比赛要求摘要.md`），不要重新讨论已定决策（见 `docs/决策记录.md`）。
> 视频相关的流程与参数见 `docs/视频制作记录.md`。

**最后更新：** 2026-11-10
**当前状态：** 预指导已提交（2026-10-28）。**前端已全量迁移到 React**（2026-11-10），Streamlit 版已于 2026-11-10 删除。
**当前阶段：** 最终版冲刺（**2026-11-18 截止**，剩 8 天）
**下一步优先级：**
1. 前端评测结论落地（子 agent 评测中）
2. 演示视频重录（5–8 分钟，含 ≥2 分钟 AI 协同录屏）
3. 技术文档（≤30 页，20 页够）：意图控制 6–8 / 架构 5–6 / 可复现 4–5 / 封面目录 3–4
**已完成的任务：** 骨架、解析、切片、检索、问答与抗幻觉、Streamlit 界面、学期视图、课表导入、资料删除、模型配置面板、原页查看、耗时显示、演示视频、预指导提交、**React 前端全量迁移（API 层 + 界面 + open-claude-ui 组件整合）**
**已冻结的接口：**
- `config.py`：`ROOT`、`DEEPSEEK_API_KEY`、`DEEPSEEK_BASE_URL`、`DEEPSEEK_MODEL`、`CHROMA_DIR`、`DATA_DIR`、`SEMESTER_START`、`require_api_key()`
- `main.py`：`app`（FastAPI 实例），`GET /health` → `{status, llm_configured}`
- `semester.py`：`load_courses()`、`load_assignments()`、`week_no(d)`、`week_monday(d)`、`assignments_due_on(d)`、`upcoming_assignments(d, within_days=14)`、`week_view(d) -> dict{week_no, monday, days[], course_count, upcoming[], before_semester}`，每天 `{date, weekday, is_today, courses[], due[]}`
- `parser.py`：`NoTextLayerError`、`file_doc_id(path) -> str`、`parse_pdf(path) -> ParsedDoc{doc_id, filename, pages[{page_no, text}], blank_pages[]}`，另有属性 `page_count`、`text_length`
- `chunker.py`：`chunk_doc(doc, size=600, overlap=80) -> list[Chunk{chunk_id, doc_id, doc_name, page_no, ordinal, text}]`；不跨页；优先在句末/空行断开；chunk_id 形如 `{doc_id}-p{page}-{ordinal:03d}`
- `embedding.py`：`BGEEmbeddingFunction`（BAAI/bge-small-zh-v1.5，**512 维**，`embed_documents` 不加前缀 / `embed_query` 加指令前缀）、`MODEL_TAG="bge_zh"`、`MODEL_NAME`
- `store.py`：`Store(path?)`、`upsert(chunks) -> int`、`delete_doc(doc_id)`、`search(query, top_k=5) -> list[Hit{chunk_id, doc_id, doc_name, page_no, text, distance, score}]`、`count()`、`docs()[{doc_id, doc_name, chunks}]`；集合名 `chunks_bge_zh_v1`；数据在 `chroma_data/`（gitignore）
- `qa.py`：`answer(question, top_k=8, store?) -> Answer{status: ok|not_found|error, text, citations[{index, chunk_id, doc_id, doc_name, page_no, text}], related[], searched[], best_distance}`；`MAX_DISTANCE=0.65`；`NO_ANSWER_MARK`；三层防线（阈值拦截 / prompt 约束 / 引用编号校验）+ 同文档优先 `_select_context`
- `data/courses.json`：`{_meta, courses[{name, day, start_section, end_section, weeks[], start_time, end_time}]}`（已脱敏，无教师/教室）
- `data/assignments.json`：`{_meta, assignments[{id, course, title, due_date}]}`（示例数据，课程名对应真实课表，内容虚构）
- CLI：`week [YYYY-MM-DD]`、`parse <pdf>`、`index <pdf>`、`search <问题>`、`ask <问题>`、`stats`
- `api.py`（React 前端用，前缀 `/api`）：
  - 设置 `GET /settings`（不回 key，只回 `has_key`）、`PUT /settings`、`POST /settings/clear`
  - 资料库 `GET /library`、`POST /library/upload`（multipart）、`DELETE /library/{doc_id}`
  - 问答 `POST /ask`、`POST /ask/stream`（SSE，事件类型 meta/token/done/not_found/error）
  - 原页图 `GET /page/{doc_id}/{page_no}?dpi=`、`GET /page-count/{doc_id}`
  - 学期 `GET /semester?day=`、`GET /semester/meta`、`PUT /semester/courses`、`PUT /semester/assignments`、`POST /semester/reset`
- `qa.answer_stream(question, top_k=8, store=None)`：生成器，逐条 yield 事件字典；与 `answer()` 共用检索/上下文/引用校验
- **前端** `frontend/`：Vite + React 18 + TS + Tailwind；`npm run dev`（5173，代理到 8000）或 `npm run build`（产物给 FastAPI 直接服务）
  - 组件：`src/components/cds/` 来自 open-claude-ui（MIT），配色已由陶土橙改为靛蓝
  - 开发时改 `backend/` 后 uvicorn 需重启；改前端热更新即可
**已放弃：** 「第三章是哪周学的」——课表不含教学进度，数据不支持（见决策记录 D10 追加项）
**阻塞项：** 无。**硬期限：2026-11-18 最终版提交**（技术文档 ≤30 页 + 5–8 分钟视频 + GitHub 演进链）

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
- **改 `backend/` 下的代码后必须重启 uvicorn**：它不会重新 import 后端模块，进程里还是旧类。前端改 `frontend/src/` 则热更新即可
- 所有脚本用 `pwsh` 执行
- 本地运行，不部署公网
- DeepSeek key 放 `.env`，仓库 Public，`.env` 永不提交
