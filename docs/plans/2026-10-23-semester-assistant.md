# 学期助手（Semester Assistant）实施计划

> **执行方式：** 由灰鸦与 Claude Code 逐任务推进。每个任务结束时必须完成「验收 + 提交 + Prompt 留档」三件事。
> **比赛：** 第九届传智杯 · Vibe Coding 全栈应用速成挑战赛 · C 组（高职高专）· 个人赛
> **截止：** 2026-11-18（省赛报名 + 作品提交同一日期）

## 给新会话的读者（重要）

这个项目跨 26 天、跨多个会话窗口。**任何一个新窗口的 AI 都必须先读三个文件，再动手**：

1. `PROGRESS.md`（根目录）—— 做到哪了、下一步是什么、哪些接口已冻结
2. `docs/决策记录.md` —— 已定下的结论和理由，**不要重新讨论**
3. 本文件里当前 Task 那一节

`docs/比赛要求摘要.md` 替代上网重新调研规则。**不要为了确认比赛规则去搜索、也不要把已经排除的方案重新提一遍。**

**续接方式：** 灰鸦会说「读 PROGRESS.md，继续 Task N」。读完直接开工，不要复述计划、不要请求确认方向。


**Goal:** 做一个能回答课程资料问题、每个答案都带原文页码出处、并给出本周课业安排的本地 Web 应用。

**Architecture:** 本地全栈，无公网部署。前端 React 单页（Vite）→ 后端 FastAPI → 解析层（PyMuPDF）→ 向量库（Chroma 本地持久化）→ 大模型（DeepSeek，OpenAI 兼容协议）。核心设计约束：答案必须引用检索到的片段编号，无依据时输出 `NO_ANSWER`，由后端降级为「未找到」。

**Tech Stack:** Python 3.12 / uv / FastAPI / PyMuPDF / Chroma / sentence-transformers（BAAI/bge-small-zh-v1.5）/ DeepSeek API / React + Vite + Tailwind + shadcn-ui

**Spec:** `docs/产品定义.md`（本文件第一节即为其内容，任务执行时以本计划为准）

---

## Global Constraints

比赛与工程的双重约束，每个任务都隐含这些要求：

1. **截止 2026-11-18**，省赛作品提交入口在缴费后才开放，缴费金额待确认。
2. **Git 必须细粒度**：禁止 initial commit 一把梭。一次提交 = 一个可验证的小改动，提交信息写清「做了什么 + 引导 AI 的过程」。
3. **Prompt 历史必须留档**：至少 3 个核心功能迭代的完整链路（我的提问 → AI 建议 → 我如何纠偏）。落在 `docs/prompts/`。
4. **API key 绝不进仓库**：只用 `.env`，`.gitignore` 必须包含 `.env`。仓库 Public。
5. **数据红线**：班级花名册、学生姓名/学号/成绩等敏感数据**一律不入库、不进仓库、不进演示**。课表与作业数据自造或脱敏。
6. **成本控制**：DeepSeek 按量付费，单次开发期调用预算 ≤ 30 元；解析与向量化全部本地，不调用付费 OCR。
7. **不部署公网**：本赛道不要求在线演示，全部本地运行，演示用录屏完成。
8. **Windows 环境**：路径一律用 `pathlib`，不硬编码分隔符；脚本用 `pwsh` 执行。
9. **每完成一个任务必须更新 `PROGRESS.md`**（日期 / 当前任务 / 已完成 / 已冻结接口），并与该任务的代码一起提交。漏更新 = 下一个窗口从错误状态起步。

## Review Focus

比赛评委（以及任何照着 README 复现的人）最可能踩到的几类问题，每一条都要有对应的验收步骤：

1. **空知识库提问** → 必须返回「未找到」而不是编造答案，界面不能白屏。
2. **检索到的片段与答案不对应** → 引用编号必须逐条校验，存在性不合法就降级。
3. **扫描版 PDF（无文本层）** → 必须明确提示「该文档无文本层，无法解析」，不能静默入库空内容。
4. **首次运行缺 `.env` 或模型未下载** → README 必须覆盖，启动时报错信息要指向解决动作。
5. **超长文档（百页以上）** → 切片与入库不能卡死，需有进度反馈。

---

## 项目结构

```text
semester-assistant/
├── .env.example              # 环境变量模板（DEEPSEEK_API_KEY=）
├── .gitignore                # .env / .venv / chroma_data / node_modules
├── README.md                 # 十分钟复现指南（最终形态）
├── pyproject.toml            # uv 管理
├── docs/
│   ├── plans/                # 本计划
│   ├── prompts/              # Prompt 链留档（比赛证据）
│   └── technical-report.md   # 技术文档草稿（最终导出 PDF）
├── backend/
│   ├── app/
│   │   ├── main.py           # FastAPI 入口 + CORS
│   │   ├── config.py         # 读 .env
│   │   ├── models.py         # Pydantic 数据模型
│   │   ├── parser.py         # PDF → 结构化文本 + 页码
│   │   ├── chunker.py        # 切片
│   │   ├── store.py          # Chroma 读写
│   │   ├── qa.py             # 检索 + 生成 + 引用校验
│   │   └── semester.py       # 学期视图
│   ├── cli.py                # 命令行验收工具（不依赖前端）
│   ├── data/
│   │   ├── courses.json      # 自造课表
│   │   └── assignments.json  # 自造作业
│   └── samples/              # 测试用 PDF（公开教材章节）
└── frontend/
    ├── src/
    │   ├── App.tsx
    │   ├── pages/            # Chat / Library / Semester
    │   └── components/       # SourceCard / MessageBubble / WeekView
    └── package.json
```

---

## Task 1：项目骨架与记录纪律

**Files:**
- Create: `pyproject.toml`, `.gitignore`, `.env.example`, `README.md`（骨架）, `backend/app/main.py`, `backend/app/config.py`, `backend/cli.py`
- Create: `docs/prompts/00-记录规范.md`

**验收标准:**
- `uv run uvicorn app.main:app` 能起服务，`GET /health` 返回 `{"status":"ok"}`
- `git log --oneline` 至少 3 个提交，无 initial commit 一把梭
- `.gitignore` 覆盖 `.env`、`.venv`、`chroma_data/`、`node_modules/`

- [ ] **Step 1:** 建目录结构，`git init`，写 `.gitignore`（先写 ignore，防止误提交）
- [ ] **Step 2:** `uv init` + 添加依赖 `fastapi uvicorn python-dotenv pydantic`，写 `config.py`（读 `DEEPSEEK_API_KEY`，缺失时给出明确报错文案）
- [ ] **Step 3:** 写 `main.py` 的 `/health` 端点
- [ ] **Step 4:** 启动验证：`uv run uvicorn app.main:app --reload`，浏览器访问 `/health`
- [ ] **Step 5:** 写 `.env.example` 与 README 骨架（运行方式先写最短路径）
- [ ] **Step 6:** 提交：`git commit -m "chore: 初始化项目骨架与健康检查端点"`
- [ ] **Step 7:** 写 `docs/prompts/00-记录规范.md`——规定每次核心功能完成后要记录什么（见文末模板），并提交

**记录动作：** 本任务本身不产生核心 Prompt 链，但要建立留档目录与模板。

---

## Task 2：PDF 解析与切片（核心功能迭代 ①）

**Files:**
- Create: `backend/app/parser.py`, `backend/app/chunker.py`, `backend/app/models.py`
- Modify: `backend/cli.py`
- Create: `docs/prompts/01-解析与切片.md`

**Interfaces:**
- Produces: `parse_pdf(path: Path) -> ParsedDoc`，其中 `ParsedDoc {doc_id: str, filename: str, pages: list[Page]}`, `Page {page_no: int, text: str}`
- Produces: `chunk_doc(doc: ParsedDoc, size: int = 600, overlap: int = 80) -> list[Chunk]`，`Chunk {chunk_id: str, doc_id: str, page_no: int, text: str}`

**验收标准:**
- `uv run python cli.py parse samples/xxx.pdf` 打印页数与切片数
- 每片 `text` 非空，`page_no` 在 1..总页数 范围内
- 扫描版 PDF（无文本层）返回明确错误而非空结果

- [ ] **Step 1:** 写 `parse_pdf`（PyMuPDF `fitz`，逐页取 `get_text("text")`；全篇空白时抛 `NoTextLayerError`）
- [ ] **Step 2:** CLI 验证单篇解析，检查首尾页文本是否完整
- [ ] **Step 3:** 提交：`feat: 实现 PDF 逐页文本解析`
- [ ] **Step 4:** 写 `chunk_doc`（按字符切、带重叠、按页边界不跨页）
- [ ] **Step 5:** CLI 验证切片数量与页码范围
- [ ] **Step 6:** 提交：`feat: 实现按页边界的文本切片`
- [ ] **Step 7:** **Prompt 留档**——把这一轮与 AI 的对话整理进 `docs/prompts/01-解析与切片.md`（重点记录：双栏排版抽取乱序的问题、你如何引导 AI 调整切分策略），并提交

**记录动作：** 这是第 1 条 Prompt 链证据。

---

## Task 3：向量化与检索

**Files:**
- Create: `backend/app/store.py`
- Modify: `backend/cli.py`

**Interfaces:**
- Consumes: `Chunk`（Task 2）
- Produces: `upsert(chunks: list[Chunk]) -> int`、`search(query: str, top_k: int = 5) -> list[Hit]`，`Hit {chunk_id, doc_id, page_no, text, score}`

**验收标准:**
- 同一文档重复入库不产生重复记录（按 `chunk_id` 幂等）
- `uv run python cli.py search "第三章讲了什么"` 返回的 `Hit` 含页码与原文片段
- 空库检索返回空列表，不抛异常

- [ ] **Step 1:** 接入 Chroma（`PersistentClient(path="chroma_data")`），embedding 用本地 `BAAI/bge-small-zh-v1.5`（首次运行自动下载，README 需注明约 100MB）。**注意：sentence-transformers 会连带安装 torch，约 2–3GB，装在 D 盘 venv 里，别放 C 盘；如果装不动，退路是 Chroma 内置的 `all-MiniLM-L6-v2`（零额外依赖，中文效果打折，可接受）**
- [ ] **Step 2:** 实现 `upsert`（metadata 存 doc_id/page_no），CLI 入库一篇并打印条数
- [ ] **Step 3:** 提交：`feat: 接入本地向量库与嵌入模型`
- [ ] **Step 4:** 实现 `search`，验证三个不同问题的召回结果相关性
- [ ] **Step 5:** 提交：`feat: 实现向量检索与命中返回`
- [ ] **Step 6:** 验证幂等性：重复入库同一文档，条数不变

---

## Task 4：问答与引用校验（核心功能迭代 ②）

**Files:**
- Create: `backend/app/qa.py`
- Modify: `backend/cli.py`

**Interfaces:**
- Consumes: `search()`（Task 3）
- Produces: `answer(question: str, top_k: int = 5) -> Answer`，`Answer {status: "ok" | "not_found", text: str, citations: list[Citation], searched: list[str]}`，`Citation {index: int, chunk_id: str, doc_id: str, page_no: int, text: str}`

**验收标准（本项目的灵魂，逐条都要测）:**
- 有答案时：`citations` 中每个 `chunk_id` 都存在于本次检索结果中（不存在则整体降级为 `not_found`）
- 无依据时：模型输出 `NO_ANSWER` → 后端返回 `status="not_found"`，`text` 为固定话术，`searched` 列出已检索范围
- 空库提问：返回 `not_found`，不调用模型（省钱且不幻觉）
- 提问「作者是谁」这类需要具体细节的问题，答案里必须带 `[1]` 式引用标记

- [ ] **Step 1:** 写 prompt 模板（严格约束：只允许使用给定片段；每个结论后标注 `[n]`；无依据输出 `NO_ANSWER`）
- [ ] **Step 2:** 实现 `answer()` 主流程：检索 → 组装上下文 → 调用 DeepSeek → 解析引用标记
- [ ] **Step 3:** 实现引用校验层（正则提取 `[n]` → 检查越界 → 降级）
- [ ] **Step 4:** CLI 跑通三个用例：有答案、无答案、空库
- [ ] **Step 5:** 提交：`feat: 实现带引用校验的知识问答`
- [ ] **Step 6:** **Prompt 留档**——`docs/prompts/02-问答与抗幻觉.md`，重点记录：模型编造引用的现象、你如何用 prompt + 后处理两层约束把它压住

**记录动作：** 这是第 2 条 Prompt 链证据，也是技术文档「意图控制策略」的核心素材。

---

## Task 5：API 层

**Files:**
- Modify: `backend/app/main.py`, `backend/app/models.py`

**Interfaces:**
- Produces: `POST /api/ingest`（multipart 文件）→ `{doc_id, chunks}`；`POST /api/ask`（`{question}`）→ `Answer`；`GET /api/library` → `[{doc_id, filename, pages, chunks}]`

**验收标准:**
- 三个端点用 `curl` 或 FastAPI `/docs` 全部调通
- 上传同一文件两次，library 不重复
- 上传非 PDF 返回 400 与中文错误信息

- [ ] **Step 1:** 定义 Pydantic 模型
- [ ] **Step 2:** 实现 `/api/ingest`（含文件类型校验、临时文件清理）
- [ ] **Step 3:** 提交：`feat: 新增文档上传接口`
- [ ] **Step 4:** 实现 `/api/ask` 与 `/api/library`
- [ ] **Step 5:** 用 FastAPI 自带 `/docs` 手工验证三个端点
- [ ] **Step 6:** 提交：`feat: 新增问答与文档列表接口`

---

## Task 6：前端界面

**Files:**
- Create: `frontend/`（Vite + React + Tailwind + shadcn-ui）
- Create: `src/pages/Chat.tsx`, `src/pages/Library.tsx`, `src/components/SourceCard.tsx`

**验收标准:**
- 上传 PDF 后列表实时出现
- 提问后先出「检索中」状态，答案流式返回（或分块返回）
- 每条答案下方展示来源卡片：文件名 + 第 N 页 + 原文片段，点击可展开
- `not_found` 状态有独立视觉（不是红字报错，而是中性提示 + 已检索范围）
- 1280 宽下布局不溢出

- [ ] **Step 1:** 脚手架 + Tailwind + shadcn 初始化，跑通空白页
- [ ] **Step 2:** 提交：`chore: 初始化前端脚手架`
- [ ] **Step 3:** 实现 Library 页（上传 + 列表）
- [ ] **Step 4:** 提交：`feat: 文档库页面与上传`
- [ ] **Step 5:** 实现 Chat 页（提问、消息流、加载态）
- [ ] **Step 6:** 提交：`feat: 对话页面与消息流`
- [ ] **Step 7:** 实现 SourceCard（引用锚点、展开原文、页码定位）
- [ ] **Step 8:** 提交：`feat: 来源卡片与引用展示`
- [ ] **Step 9:** CORS 联调，跑通端到端

---

## Task 7：学期视图（核心功能迭代 ③）

**Files:**
- Create: `backend/app/semester.py`, `backend/data/courses.json`, `backend/data/assignments.json`
- Create: `frontend/src/pages/Semester.tsx`, `frontend/src/components/WeekView.tsx`

**Interfaces:**
- Produces: `week_view(date: date) -> WeekPlan`，`WeekPlan {week_no, days: [{date, courses, due_assignments}], review: [{course, last_studied, suggestion}]}`

**验收标准:**
- 给定任意日期，正确算出第几教学周（学期起始日写死为常量，配置在 `config.py`）
- 同日无课时显示「无课」，不空白
- 复习建议来自已入库文档的章节元数据，未入库的课程明确标注「暂无资料」
- 数据文件全部为自造/脱敏内容

- [ ] **Step 1:** 造课表与作业数据（脱敏，6 门课左右）
- [ ] **Step 2:** 实现 `week_view()` + 周次计算
- [ ] **Step 3:** 提交：`feat: 学期周视图与周次计算`
- [ ] **Step 4:** 实现 API `GET /api/semester?date=`
- [ ] **Step 5:** 提交：`feat: 学期视图接口`
- [ ] **Step 6:** 前端 WeekView 页面（卡片式周视图）
- [ ] **Step 7:** 提交：`feat: 学期周视图页面`
- [ ] **Step 8:** **Prompt 留档**——`docs/prompts/03-学期视图.md`：记录你如何把「散乱的课表/作业/资料」抽象成数据结构的过程（这一段最能体现意图控制）

**记录动作：** 这是第 3 条 Prompt 链证据。

---

## Task 8：健壮性与打磨

**Files:**
- Modify: `backend/app/*.py`, `frontend/src/pages/*.tsx`

**验收标准:**
- Review Focus 五条逐条人工验证通过
- 百页文档入库时有进度反馈，不卡死
- 断网/无 key 时，前端给出可读的错误提示
- 单次问答平均响应 ≤ 15 秒

- [ ] **Step 1:** 按 Review Focus 五条逐项测试并修复
- [ ] **Step 2:** 提交：`fix: 空库与扫描件等边界场景处理`
- [ ] **Step 3:** 大文档性能验证（找一篇 100+ 页 PDF）
- [ ] **Step 4:** UI 打磨：空状态、加载态、错误态、引用卡片细节

---

## Task 9：技术文档与演示视频

**Files:**
- Create: `docs/technical-report.md` → 导出 `docs/技术文档.pdf`（≤30 页）
- Create: `docs/演示脚本.md`

**验收标准:**
- PDF ≤30 页，三部分齐全：意图控制策略 / 架构设计 / 可复现性论证
- 视频 5–8 分钟、1080p、MP4，**其中 ≥2 分钟是 AI 协同过程录屏**
- 视频里能看清：提问 → 检索 → 带页码的回答 → 点击展开原文 → 学期视图

- [ ] **Step 1:** 把三条 Prompt 链（Task 2/4/7）整理进技术文档的「意图控制策略」一节
- [ ] **Step 2:** 画架构图（Mermaid 或手绘后截图），说明分层与约束点
- [ ] **Step 3:** 写可复现性论证（环境、依赖、数据来源、验证步骤）
- [ ] **Step 4:** 导出 PDF，检查页数与中文字体
- [ ] **Step 5:** 写演示脚本（分镜 + 每段停留时间），再录
- [ ] **Step 6:** 录 2 分钟 AI 协同段落：现场让 AI 改一个真实 bug，录下提问与纠偏全过程

---

## Task 10：复现验证与提交

**验收标准:**
- 在**干净的**目录克隆仓库，严格按 README 从零走到能用，全程 ≤ 10 分钟（不含模型下载）
- 仓库无 `.env`、无 API key、无真实个人数据（全文搜索确认）
- 四件材料齐：仓库 / README / 视频 / PDF 文档
- Prompt 链 3 条齐、git 历史细粒度

- [ ] **Step 1:** 另开目录 `git clone` 自测复现，记录耗时与卡点
- [ ] **Step 2:** 修 README 里所有对不上的步骤
- [ ] **Step 3:** 敏感信息全仓扫描（`grep -r "sk-"`、检查 `.env` 是否被追踪）
- [ ] **Step 4:** 缴费 → 拿到提交入口 → 上传四件材料
- [ ] **Step 5:** 提交后保留一份本地归档

---

## 排期（26 天，参考）

| 日期 | 任务 | 预计投入 |
|---|---|---|
| 10/23–10/24 | Task 1 骨架 + 前置确认（学校赛点、缴费） | 3–4 h |
| 10/25–10/27 | Task 2 解析与切片 | 4–5 h |
| 10/28–10/30 | Task 3 向量检索 | 4–5 h |
| 10/31–11/2 | Task 4 问答与引用校验 | 5–6 h |
| 11/3–11/5 | Task 5 API + Task 6 前端起步 | 5–6 h |
| 11/6–11/8 | Task 6 前端完成 | 5 h |
| 11/9–11/11 | Task 7 学期视图 | 4–5 h |
| 11/12–11/13 | Task 8 健壮性与打磨 | 3 h |
| 11/14–11/16 | Task 9 文档 + 视频 | 6–8 h |
| 11/17–11/18 | Task 10 复现验证 + 提交 | 3 h |

**缓冲：** 以上合计约 45–50 小时，留出 3 天缓冲。若落后，优先砍 Task 7 的复习建议（保留周课表），不要砍 Task 4 和 Task 9。

---

## Prompt 留档模板（`docs/prompts/NN-功能名.md`）

```markdown
# 功能：<名称>（YYYY-MM-DD）

## 目标
一句话说明这一轮要 AI 帮我做出什么。

## 关键提问（原文摘录）
1. <我实际输入的 prompt>
2. <追问 / 纠偏的 prompt>

## AI 的响应与问题
- 它给出的方案：
- 出问题的地方：（如：引用编号编造、页码错位、切分跨页）

## 我的引导与修复
- 我怎么定位问题：
- 我怎么改 prompt / 约束 / 后处理：
- 最终 diff 摘要：

## 结论
这次迭代沉淀下来的约束是什么（写进架构或 prompt 的那条规则）。
```
