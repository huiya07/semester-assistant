# 学期助手（Semester Assistant）

把你的课程资料、课表、作业截止时间喂进去：**问资料里的问题，答案永远带页码出处；找不到就说找不到；顺便告诉你这周该做什么。**

> 第九届传智杯 · AI 创新应用挑战赛（Vibe Coding 全栈应用速成）· 个人赛 · C 组
>
> **完整提交包**（打包源码 + 两份 PDF 文档 + AI 对话记录）见比赛提交表单中的网盘链接。

## 它解决什么

课程资料散在 PPT、PDF、教材里，复习时常常只记得「老师讲过」却翻不到在第几页；
课表和作业又散在另一个地方。这个项目把两件事放在一条时间轴上：

- **资料问答**：上传 PDF，提问，答案标注 `[1]`，点开是「《某资料》第 N 页」的原文
- **可信度三态**：有依据 → 直接答；相关但没答案 → 说明看到了什么，把原文摆给你；完全不相关 → 明说没检索到
- **按课程分组**：上传时可选归属课程，提问时可限定在某一门课里检索（未分类的资料始终参与，不会因为选课而消失）
- **这周该做什么**：第几教学周、这周有哪些课、两周内有哪些作业到期；作业块可点开看完整标题
- **首次引导**：第一次打开时逐步高亮「添加资料 → 提问 → 周视图」，可随时跳过

## 技术栈

| 层 | 选型 | 说明 |
|---|---|---|
| 界面 | React 18 + TypeScript + Tailwind | `frontend/`，组件与设计令牌部分来自 open-claude-ui（MIT） |
| 文档解析 | PyMuPDF | 逐页提取文本，不做 OCR，扫描件会明确报错 |
| 切片 | 自实现 | 按页切分不跨页；优先在句末/空行断开（句末结尾率 80%） |
| 向量库 | Chroma（本地持久化） | 数据落在 `chroma_data/` |
| 嵌入模型 | BAAI/bge-small-zh-v1.5 | 中文检索；英文模型实测对中文完全无效 |
| 大模型 | DeepSeek（OpenAI 兼容协议） | 温度 0，只依据检索片段作答 |

## 快速开始

前置：**Python 3.12+**、[uv](https://docs.astral.sh/uv/)、**Node.js 18+**（构建前端需要）。

### 方式一：一键脚本（推荐，国内网络已加速）

```powershell
.\setup.ps1
```

脚本依次做三件事：从华为云镜像装后端依赖 → 构建前端 → 启动服务。

### 方式二：手动四步

```powershell
# 1. 后端依赖（国内建议加镜像参数，见下）
uv sync --default-index https://repo.huaweicloud.com/repository/pypi/simple

# 2. 构建前端
cd frontend
npm install --registry=https://registry.npmmirror.com
npm run build
cd ..

# 3. 配置环境变量（也可以跳过，启动后在界面里填）
copy .env.example .env
# 编辑 .env，填入 DEEPSEEK_API_KEY=你的key

# 4. 启动
uv run uvicorn backend.app.main:app --port 8000
```

浏览器打开 http://127.0.0.1:8000 。

> **如果 `uv run` 每次启动都在重建 venv**（输出 `Creating virtual environment` / `Installed N packages`），
> 说明机器上有多个 Python 版本、uv 选错了。两个办法：
> ① 直接用 venv 里的解释器：`.venv\Scripts\python.exe -m uvicorn backend.app.main:app --port 8000`
> ② 或加 `--no-sync`：`uv run --no-sync uvicorn backend.app.main:app --port 8000`
> 另外，**服务运行期间再执行 `uv run` 会报「拒绝访问」**（venv 被占用），跑命令行验收前先停服务。

前端已在开发时热更新：`cd frontend && npm run dev`（5173 端口，自动代理到 8000）。

### 首次运行会下载什么

这一节很重要：程序本身不联网，但**首次运行需要从网上取两样东西**。

| 需要下载 | 大小 | 能否直连 | 说明 |
|---|---|---|---|
| Python 依赖（`uv sync`） | 约 1 GB | 官方源在这里 **403 拒绝** | 用 `--default-index` 走华为云，实测 7.5 MB/s |
| 中文嵌入模型 `bge-small-zh-v1.5` | 约 100 MB | **不能直连** | 代码已默认走 `hf-mirror.com` 镜像，无需额外配置 |
| 前端依赖（`npm install`） | 约 150 MB | 可以 | 国内建议 `--registry=https://registry.npmmirror.com` |
| DeepSeek API | — | 可以 | 需要自行申请 API Key |

镜像源实测（同一台机器，2026-10-26）：

| 源 | 状态 |
|---|---|
| 华为云 `repo.huaweicloud.com` | ✅ 0.05s 响应 / 7.5 MB/s 下载 |
| 阿里云 `mirrors.aliyun.com` | ✅ 0.09s 响应 |
| 清华 TUNA | ❌ 本机连续失败（HTTP 000） |
| 官方 PyPI | ⚠️ 索引可达，但 wheel 下载 **403** |

依赖里的 PyTorch 占了大头，装完整个 `.venv` 约 1 GB。

启动后**第一次提问**才加载嵌入模型（懒加载，约 10–30 秒），期间页面正常显示，第一条回答会明显慢一些。模型加载完就常驻内存，后续提问不再等。

如果想让模型走官方源（海外网络），先设置环境变量再启动：

```powershell
$env:HF_ENDPOINT = "https://huggingface.co"
```

### 准备资料

仓库自带一份**无版权的示例讲义**（虚构的数据分析入门内容），clone 下来就能直接跑通全流程：

```text
backend/samples/sample-lecture-notes.pdf
```

也可以上传你自己的 PDF（任何带文本层的都行）。示例讲义可用脚本重新生成：

```powershell
uv run python tools/make_sample_pdf.py
```

想用真实论文测试：

```powershell
curl.exe -L -o backend\samples\attention.pdf "https://arxiv.org/pdf/1706.03762v7"
```

然后在界面左侧上传文件，点「加入资料库」。

> 扫描版 PDF（无文本层）会被明确拒绝，本项目不做 OCR。

## 命令行验收（可选，不依赖界面）

```powershell
uv run python -m backend.cli week                    # 本周课表 + 到期作业（服务需先停）
uv run python -m backend.cli week 2026-10-30         # 指定日期所在周
uv run python -m backend.cli parse backend\samples\sample-lecture-notes.pdf   # 解析并切片，打印统计
uv run python -m backend.cli index backend\samples\sample-lecture-notes.pdf   # 入库
uv run python -m backend.cli search "注意力头数量"      # 只看检索结果
uv run python -m backend.cli ask "有多少个注意力头"      # 完整问答（会调用大模型）
uv run python -m backend.cli stats                   # 库内文档与切片数
```

## 目录结构

```text
frontend/               React 前端（真实入口；npm run build 产物由 FastAPI 直接服务）
backend/
  app/
    config.py           读 .env，路径常量
    parser.py           PDF → 逐页文本（doc_id 由内容哈希决定）
    chunker.py          切片，不跨页，优先句末断开
    embedding.py        BGE 中文嵌入（Chroma 1.x 接口）
    store.py            Chroma 读写与检索
    qa.py               检索 → 生成 → 引用校验（三层抗幻觉）
    semester.py         周次计算与周视图
    api.py              REST 接口层（14 个端点：设置/资料库/问答/流式/原页/学期）
    main.py             FastAPI 入口，挂载 api 路由与前端静态文件
    render.py           PDF 页渲染为 PNG（出处对照用）
    settings.py         运行期模型配置（界面保存优先于 .env）
  cli.py                命令行验收工具
  data/
    courses.json        课表（已脱敏，无教师/教室）
    assignments.json    作业示例（课程名对应真实课表，内容虚构）
docs/                   计划、决策记录、Prompt 留档
tools/build_courses.py  个人课表 → courses.json（开发期工具）
```

## 抗幻觉的三层设计

1. **检索层**：最佳距离 > 0.65 直接返回「没检索到」，不调用大模型
2. **提示层**：system prompt 约束「只用给定片段、每条结论标 [n]」；能答多少答多少，
   资料未覆盖的方面单独标注，完全无关才输出 `NO_ANSWER`
3. **后处理层**：正则校验答案里的 `[n]` 是否真实存在；引用全部越界即判定为编造，整体降级

## 数据说明

- 课表 `courses.json` 由个人课表转换，**已去除教师姓名与教室**
- 作业 `assignments.json` 是示例数据，不包含任何真实个人信息
- `.env`、`chroma_data/`、`local/` 均不进入版本库

## 自测

两条冒烟测试，覆盖后端接口与前端交互：

```bash
# 后端（20 项，约 6 秒）
# 前置：uv run uvicorn backend.app.main:app --port 8000
uv run pytest tests/test_smoke.py -v

# 前端端到端（14 项，Playwright 驱动系统 Edge）
# 前置：后端已启动；Playwright 装在全局 Python

python -X utf8 tests/ui_smoke.py
```

后端测试不依赖任何用户数据：测试用的 PDF 由 PyMuPDF 现场生成、用完删除，
问答部分会幂等地上传仓库自带的示例讲义（内容哈希固定，不会产生副本）。

## 第三方组件与致谢

前端部分组件与设计令牌来自 [Caho1/open-claude-ui](https://github.com/Caho1/open-claude-ui)（MIT License）：

- `frontend/src/components/cds/` —— `ConfirmationDialog`、`CdsButton`、`ScrollFadeContainer`、`StatusIndicators`
- `frontend/src/styles/cds-theme.css` —— 183 个设计令牌

使用方式为**按原样引入后替换配色体系**：CDS 原有的陶土橙（`--cds-clay: #d97757`）已整体映射为本项目的靛蓝主色，
不构成对 Claude Desktop 视觉的复制。原项目的 MIT 许可与版权声明随源码保留。

## License

个人参赛作品，仅供评审与学习参考。
