# 学期助手（Semester Assistant）

把你的课程资料、课表、作业截止时间喂进去：**问资料里的问题，答案永远带页码出处；找不到就说找不到；顺便告诉你这周该做什么。**

> 第九届传智杯 · AI 创新应用挑战赛（Vibe Coding 全栈应用速成）· 个人赛 · C 组

## 它解决什么

课程资料散在 PPT、PDF、教材里，复习时常常只记得「老师讲过」却翻不到在第几页；
课表和作业又散在另一个地方。这个项目把两件事放在一条时间轴上：

- **资料问答**：上传 PDF，提问，答案标注 `[1]`，点开是「《某资料》第 N 页」的原文
- **可信度三态**：有依据 → 直接答；相关但没答案 → 说明看到了什么，把原文摆给你；完全不相关 → 明说没检索到
- **这周该做什么**：第几教学周、这周有哪些课、两周内有哪些作业到期

## 技术栈

| 层 | 选型 | 说明 |
|---|---|---|
| 界面 | Streamlit | 阶段一用来快速验证闭环，单文件 `app.py` |
| 文档解析 | PyMuPDF | 逐页提取文本，不做 OCR，扫描件会明确报错 |
| 切片 | 自实现 | 按页切分不跨页；优先在句末/空行断开（句末结尾率 80%） |
| 向量库 | Chroma（本地持久化） | 数据落在 `chroma_data/` |
| 嵌入模型 | BAAI/bge-small-zh-v1.5 | 中文检索；英文模型实测对中文完全无效 |
| 大模型 | DeepSeek（OpenAI 兼容协议） | 温度 0，只依据检索片段作答 |

## 快速开始

前置：**Python 3.12+**、[uv](https://docs.astral.sh/uv/)。

```powershell
# 1. 安装依赖（uv 自动创建 .venv）
uv sync

# 2. 配置环境变量
copy .env.example .env
# 编辑 .env，填入 DEEPSEEK_API_KEY=你的key

# 3. 启动界面
uv run streamlit run app.py
```

浏览器打开 http://127.0.0.1:8501 。

### 首次运行会下载什么

这一节很重要：程序本身不联网，但**首次运行需要从网上取两样东西**。

| 需要下载 | 大小 | 能否直连 | 说明 |
|---|---|---|---|
| Python 依赖（`uv sync`） | 约 1 GB | 通常可以，但慢 | 慢的话设镜像：`$env:UV_INDEX_URL="https://pypi.tuna.tsinghua.edu.cn/simple"` |
| 中文嵌入模型 `bge-small-zh-v1.5` | 约 100 MB | **不能直连** | 代码已默认走 `hf-mirror.com` 镜像，无需额外配置 |
| DeepSeek API | — | 可以 | 需要自行申请 API Key |

依赖里的 PyTorch 占了大头，装完整个 `.venv` 约 1 GB。首次启动加载模型需要 10–30 秒，界面会显示「正在加载嵌入模型…」。

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
uv run python -m backend.cli week                    # 本周课表 + 到期作业
uv run python -m backend.cli week 2026-10-30         # 指定日期所在周
uv run python -m backend.cli parse backend\samples\attention.pdf   # 解析并切片，打印统计
uv run python -m backend.cli index backend\samples\attention.pdf   # 入库
uv run python -m backend.cli search "注意力头数量"      # 只看检索结果
uv run python -m backend.cli ask "有多少个注意力头"      # 完整问答（会调用大模型）
uv run python -m backend.cli stats                   # 库内文档与切片数
```

## 目录结构

```text
app.py                  Streamlit 界面（真实入口）
backend/
  app/
    config.py           读 .env，路径常量
    parser.py           PDF → 逐页文本（doc_id 由内容哈希决定）
    chunker.py          切片，不跨页，优先句末断开
    embedding.py        BGE 中文嵌入（Chroma 1.x 接口）
    store.py            Chroma 读写与检索
    qa.py               检索 → 生成 → 引用校验（三层抗幻觉）
    semester.py         周次计算与周视图
    main.py             FastAPI 入口（目前只有 /health）
  cli.py                命令行验收工具
  data/
    courses.json        课表（已脱敏，无教师/教室）
    assignments.json    作业示例（课程名对应真实课表，内容虚构）
docs/                   计划、决策记录、Prompt 留档
tools/build_courses.py  个人课表 → courses.json（开发期工具）
```

## 抗幻觉的三层设计

1. **检索层**：最佳距离 > 0.65 直接返回「没检索到」，不调用大模型
2. **提示层**：system prompt 约束「只用给定片段、每条结论标 [n]、没有依据只输出 NO_ANSWER」
3. **后处理层**：正则校验答案里的 `[n]` 是否真实存在；引用全部越界即判定为编造，整体降级

## 数据说明

- 课表 `courses.json` 由个人课表转换，**已去除教师姓名与教室**
- 作业 `assignments.json` 是示例数据，不包含任何真实个人信息
- `.env`、`chroma_data/`、`local/` 均不进入版本库

## License

个人参赛作品，仅供评审与学习参考。
