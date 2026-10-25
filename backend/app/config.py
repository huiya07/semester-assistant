"""全局配置。

所有环境相关的东西只在这里读一次，其它模块 import 这个模块拿常量。
API key 只从 .env 读，绝不写死、绝不进仓库。
"""

from __future__ import annotations

import os
from pathlib import Path

from dotenv import load_dotenv

# 项目根目录：backend/app/config.py -> backend/app -> backend -> 根
ROOT = Path(__file__).resolve().parents[2]

load_dotenv(ROOT / ".env")

# --- 大模型 ---
DEEPSEEK_API_KEY = os.getenv("DEEPSEEK_API_KEY", "").strip()
DEEPSEEK_BASE_URL = os.getenv("DEEPSEEK_BASE_URL", "https://api.deepseek.com").strip()
DEEPSEEK_MODEL = os.getenv("DEEPSEEK_MODEL", "deepseek-flash").strip()

# --- 存储 ---
CHROMA_DIR = ROOT / "chroma_data"
DATA_DIR = ROOT / "backend" / "data"
# 入库时把原 PDF 复制到这里，保证「点出处看原页」永远能回溯
PDF_STORE_DIR = DATA_DIR / "pdfs"

# --- 学期 ---
# 学期第一周周一的日期，用于计算当前教学周。按学校实际校历改。
SEMESTER_START = os.getenv("SEMESTER_START", "2026-09-07")


def require_api_key() -> str:
    """需要调用大模型的入口先调它，缺 key 时给出可执行的报错提示。"""
    if not DEEPSEEK_API_KEY:
        raise RuntimeError(
            "未配置 DEEPSEEK_API_KEY。请在项目根目录创建 .env 文件，"
            "内容为 DEEPSEEK_API_KEY=你的key（可参照 .env.example）。"
        )
    return DEEPSEEK_API_KEY
