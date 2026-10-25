# 学期助手（Semester Assistant）

把你的课程资料、课表、作业截止时间喂进去，它回答问题时永远带原文出处，并且知道今天是第几周、你该复习什么。

> 第九届传智杯 · AI 创新应用挑战赛（Vibe Coding）参赛作品 · 个人赛 · C 组

## 当前状态

阶段一（省赛预指导）：后端骨架已跑通，解析 / 检索 / 问答 / 界面待实现。
进度见 [`PROGRESS.md`](PROGRESS.md)。

## 技术栈

- 后端：Python 3.12 + FastAPI + uvicorn
- 文档解析：PyMuPDF
- 检索：Chroma（本地持久化）
- 大模型：DeepSeek（OpenAI 兼容协议）
- 前端：阶段一用 Streamlit 验证闭环，最终版迁移到 React + Vite

## 快速开始

前置：Python 3.12+、[uv](https://docs.astral.sh/uv/)。

```bash
# 1. 安装依赖（uv 会自动创建 .venv）
uv sync

# 2. 配置环境变量
copy .env.example .env
# 编辑 .env，填入 DEEPSEEK_API_KEY

# 3. 启动 API
uv run uvicorn backend.app.main:app --reload
```

打开 http://127.0.0.1:8000/health ，应返回：

```json
{"status": "ok", "llm_configured": true}
```

`llm_configured` 为 `false` 说明 `.env` 里还没填 key，不影响服务启动。

接口文档：http://127.0.0.1:8000/docs

## 目录结构

```text
backend/           后端
  app/
    config.py      配置与 .env 读取
    main.py        FastAPI 入口
frontend/          （阶段二）React 前端
docs/              比赛材料、计划、Prompt 留档
local/             报名等私密信息（已 gitignore）
```

## 许可

本项目为个人参赛作品。
