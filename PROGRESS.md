# 进度状态（跨会话唯一真相）

> **给新会话的 AI：先读这个文件，再读 `docs/plans/2026-10-23-semester-assistant.md`。**
> 用户开场白通常是「读 PROGRESS.md，继续 Task N」。不要去重新调研比赛规则（摘要见 `docs/比赛要求摘要.md`），不要重新讨论已定决策（见 `docs/决策记录.md`）。

**最后更新：** 2026-10-25
**当前状态：** Task 1 完成，仓库已初始化，`/health` 验证通过（`llm_configured: false`，尚未建 `.env`）
**当前任务：** Task 2（PDF 解析与切片）——**必须在 10-27 前跑通**，为 10-31 预指导提交留出时间
**下一步具体动作：** 写 `backend/app/parser.py` 的 `parse_pdf()`，用一份公开教材 PDF 验证逐页文本与页码
**已完成的任务：** Task 1（项目骨架与记录纪律）
**已冻结的接口：**
- `config.py`：`ROOT`、`DEEPSEEK_API_KEY`、`DEEPSEEK_BASE_URL`、`DEEPSEEK_MODEL`、`CHROMA_DIR`、`DATA_DIR`、`SEMESTER_START`、`require_api_key()`
- `main.py`：`app`（FastAPI 实例），`GET /health` → `{status, llm_configured}`
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
