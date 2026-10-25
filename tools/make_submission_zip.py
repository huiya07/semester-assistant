"""打提交包：源码 + 作品介绍 PDF + 一段说明，输出到项目外。

排除：.git / .venv / chroma_data / .env / local / 原件留底 / 缓存，
避免把密钥、个人报名信息和几百 MB 依赖打进包。

用法：
    uv run python tools/make_submission_zip.py
"""

from __future__ import annotations

import subprocess
import zipfile
from datetime import date
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
OUT = ROOT.parent / f"semester-assistant-提交包-{date.today():%Y%m%d}.zip"

SKIP_SUFFIX = {".pyc", ".mp4", ".mov"}

NOTE = """学期助手（Semester Assistant）
第九届传智杯 · AI 创新应用挑战赛（Vibe Coding）· 个人赛 · C 组

【这是什么】
课程资料问答 + 学期周视图的学习助手：上传 PDF 后提问，答案带页码出处，
找不到会明确说找不到；另有一张「这周该做什么」的课表/作业视图。

【怎么跑】（需要 Python 3.12+ 和 uv）
  1. uv sync
  2. copy .env.example .env   然后把 DEEPSEEK_API_KEY 填进去
  3. uv run streamlit run app.py
  浏览器打开 http://127.0.0.1:8501

  ★ 首次运行需要联网下载：Python 依赖约 1GB + 中文嵌入模型约 100MB。
    嵌入模型已默认走国内镜像 hf-mirror.com，无需额外配置。
    依赖下载慢可先设镜像：$env:UV_INDEX_URL="https://pypi.tuna.tsinghua.edu.cn/simple"

  也可以跳过改 .env：界面打开后直接在「⚙ 模型配置」里填 Key。

【自带示例资料】
  backend/samples/sample-lecture-notes.pdf
  无版权的 3 页中文讲义，直接上传即可跑通全流程。

【文档】
  作品介绍.pdf                     作品介绍（7 项要求）
  docs/技术说明.md                 架构与关键设计（如有）
  docs/prompts/                    开发过程中的 Prompt 链留档

【源码仓库】
  https://github.com/huiya07/semester-assistant

【说明】
  API Key 不包含在包内，需自行配置；项目的全部计算均在本机完成。
"""


def tracked_files() -> list[Path]:
    """用 git 的跟踪列表，天然遵循 .gitignore。

    这样 .env、local/、chroma_data/、未跟踪的第三方 PDF 都不会被打进包里 ——
    手工维护排除规则漏过一次（把 local/ 和 arXiv 论文打进去了），不再手工列举。
    """
    out = subprocess.run(
        ["git", "-C", str(ROOT), "ls-files", "-z"],
        capture_output=True,
        check=True,
    ).stdout.decode("utf-8")
    rels = [p for p in out.split("\0") if p.strip()]
    return [ROOT / r for r in rels if (ROOT / r).is_file()]


def main() -> None:
    files = [p for p in tracked_files() if p.suffix not in SKIP_SUFFIX]

    with zipfile.ZipFile(OUT, "w", compression=zipfile.ZIP_DEFLATED, compresslevel=9) as z:
        for f in sorted(files):
            z.write(f, Path("semester-assistant") / f.relative_to(ROOT))
        z.writestr("提交说明.txt", NOTE)

    size_mb = OUT.stat().st_size / 1024 / 1024
    print(f"已生成 {OUT}（{size_mb:.1f} MB，{len(files)} 个文件）")


if __name__ == "__main__":
    main()
