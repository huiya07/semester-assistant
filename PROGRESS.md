# 进度状态（跨会话唯一真相）

> **给新会话的 AI：先读这个文件，再读 `docs/待办.md`。**
> 用户开场白通常是「读 PROGRESS.md，继续」。不要去重新调研比赛规则（摘要见 `docs/比赛要求摘要.md`），不要重新讨论已定决策（见 `docs/决策记录.md`）。
> 视频相关的流程与参数见 `docs/视频制作记录.md`。

**最后更新：** 2026-11-10（晚间）
**当前状态：** 代码已定稿（测试 20+14 全绿）。**⚠️ 31 个提交尚未推送到 GitHub，远端仍停在 6aac31f（10-28 预指导版）** —— 推送前评委 clone 到的是旧版。
**当前阶段：** 最终版冲刺（**2026-11-18 截止**，剩 8 天）
**下一步优先级（只剩一项）：**
1. **演示视频** —— 唯一未完成项，需本人在场
   - 硬要求：**5–8 分钟 / MP4 / 1080p(1920×1080,16:9) / ≥2 分钟 AI 协同过程复现**
   - ⚠️ **分辨率的坑**：屏幕是 2560×1600(16:10)，与 1080p(16:9) 比例不同。
     录之前先把窗口拉成接近 16:9，否则要么变形要么切内容
   - AI 协同段必须展示「**出问题 → 人怎么发现 → 怎么让它改**」，光看顺利路径不算协同
   - 结构建议与细节见 `docs/视频制作记录.md`「最终版硬性要求」节
2. 视频传 B 站后，链接填进提交表单（**禁止百度网盘**）
**已完成的任务：**
- 骨架、解析、切片、检索、问答与抗幻觉、学期视图、课表导入、资料删除、原页查看、耗时显示、预指导提交
- **React 全量迁移**（API 层 14 端点 + SSE 流式 + 五个界面 + open-claude-ui 组件整合）
- **按课程分组检索**（软分组：未分类始终参与）
- **多轮对话上下文**（最近 5 轮，仅用于消解指代）
- **页码类问题直取**（「第 N 页说了什么」不走语义检索）
- **首次引导**（三步高亮 + 三处跳过出口）
- **长回答可选收起**（默认全文）、侧边栏折叠、tab 滑动指示条
- **健壮性**：请求分档超时、错误分类、并发守卫 429、停止生成、幂等 GET 重试
- **测试**：后端 20 项 + 前端 14 项
- **两轮独立审查**：前端评测 19 项（修 15）、后端审查 7 项、评委视角从零跑测 4 项
- **文档**：作品介绍 8 页 PDF（6 张图）、技术文档 15 页 PDF
**已冻结的接口：**
- `config.py`：`ROOT`、`DEEPSEEK_API_KEY`、`DEEPSEEK_BASE_URL`、`DEEPSEEK_MODEL`、`CHROMA_DIR`、`DATA_DIR`、`SEMESTER_START`、`require_api_key()`
- `main.py`：`app`（FastAPI 实例），`GET /health` → `{status, llm_configured}`
- `semester.py`：`load_courses()`、`load_assignments()`、`week_no(d)`、`week_monday(d)`、`assignments_due_on(d)`、`upcoming_assignments(d, within_days=14)`、`week_view(d) -> dict{week_no, monday, days[], course_count, upcoming[], before_semester, courses_custom}`，每天 `{date, weekday, is_today, courses[], due[]}`；`_slot_text` 用 `.get()` 防止缺字段打 500
- `parser.py`：`NoTextLayerError`、`file_doc_id(path) -> str`、`parse_pdf(path) -> ParsedDoc{doc_id, filename, pages[{page_no, text}], blank_pages[]}`，另有属性 `page_count`、`text_length`
- `chunker.py`：`chunk_doc(doc, size=600, overlap=80) -> list[Chunk{chunk_id, doc_id, doc_name, page_no, ordinal, text}]`；不跨页；优先在句末/空行断开；chunk_id 形如 `{doc_id}-p{page}-{ordinal:03d}`
- `embedding.py`：`BGEEmbeddingFunction`（BAAI/bge-small-zh-v1.5，**512 维**，`embed_documents` 不加前缀 / `embed_query` 加指令前缀）、`MODEL_TAG="bge_zh"`、`MODEL_NAME`
- `store.py`：`Store(path?)`【构造时自动 `_ensure_course_field()` 给历史切片补 `course:""`】、`upsert(chunks, pdf_file, course)`、`replace_chunks(doc_id, chunks, pdf_file, course)`（**先写后清**，避免写入失败丢文档）、`delete_doc`、`search(query, top_k=5, course=None) -> list[Hit{chunk_id, doc_id, doc_name, page_no, text, distance, score, course}]`、`chunks_of_page(page_no, doc_id?, course?)`（页码直取）、`count()`、`docs()[{doc_id, doc_name, chunks, course}]`；集合名 `chunks_bge_zh_v1`；数据在 `chroma_data/`（gitignore）
- `qa.py`：`answer(question, top_k=8, store?, course=None, history=None) -> Answer{status: ok|not_found|error, text, citations[...], related[], searched[], best_distance}`；`answer_stream(同样参数)` 逐事件 yield；`MAX_DISTANCE=0.65`；三层防线（阈值拦截 / prompt 约束 / 引用编号校验）+ 同文档优先 `_select_context`；**页码优先**（问题含「第 N 页」走 `_page_hits()` 直取，实测这类问题语义距离 0.661 会被阈值误拦）；**历史注入**（`_history_messages()` 取最近 5 轮，仅用于消除「它」这类指代）
- `data/courses.json`：`{_meta, courses[{name, day, start_section, end_section, weeks[], start_time, end_time}]}`（已脱敏，无教师/教室）
- `data/assignments.json`：`{_meta, assignments[{id, course, title, due_date}]}`（示例数据，课程名对应真实课表，内容虚构）
- CLI：`week [YYYY-MM-DD]`、`parse <pdf>`、`index <pdf>`、`search <问题>`、`ask <问题>`、`stats`
- `api.py`（React 前端用，前缀 `/api`）：
  - 设置 `GET /settings`（不回 key，只回 `has_key`）、`PUT /settings`、`POST /settings/clear`
  - 资料库 `GET /library`、`POST /library/upload`（multipart，可带 `course` 表单字段）、`DELETE /library/{doc_id}`
  - 问答 `POST /ask`、`POST /ask/stream`（SSE，事件类型 meta/token/done/not_found/error）；body 可带 `course`、`history[{q,a}]`
  - 课程名 `GET /course-names`（前端下拉用）
  - 原页图 `GET /page/{doc_id}/{page_no}?dpi=`、`GET /page-count/{doc_id}`
  - 学期 `GET /semester?day=`、`GET /semester/meta`、`PUT /semester/courses`、`PUT /semester/assignments`、`POST /semester/reset`
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
- **`uv run` 每次重建 venv 的坑（2026-11-10 查清并修复）**：本机 `python.exe`(10-25 18:53, 元数据 3.14.10)
  与 `python3.exe`(10-25 01:59, 元数据 3.14.9) 两个入口实际都跑 3.14.10，但 uv 读的是**文件里嵌的版本元数据**，
  看到 3.14.9 与 venv 的 3.14.10 不一致就每次重建（21 秒 × 每次）。
  处置：用 `python.exe` 覆盖 `python3.exe`（备份 `python3.exe.bak-20261111`），已实测不再重建。
  另：**服务运行期间再跑 `uv run` 会报「拒绝访问」**（venv 被占用），跑 CLI 验收前先停服务。
- **启动方式**：`.venv/Scripts/python.exe -m uvicorn backend.app.main:app --port 8000 --host 127.0.0.1`
  （比 `uv run` 稳，不受上面那个坑影响；也用于静默启动）
