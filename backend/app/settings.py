"""运行期可改的模型配置。

优先级：界面保存的 local/settings.json > .env > 默认值。
local/ 已在 .gitignore 里，密钥不会进仓库；界面只写这一个文件，不改 .env。
"""

from __future__ import annotations

import json
from dataclasses import asdict, dataclass
from pathlib import Path

from .config import DEEPSEEK_API_KEY, DEEPSEEK_BASE_URL, DEEPSEEK_MODEL, ROOT

SETTINGS_FILE = ROOT / "local" / "settings.json"


@dataclass
class LLMSettings:
    base_url: str
    api_key: str
    model: str

    @property
    def ready(self) -> bool:
        return bool(self.api_key.strip())


def load() -> LLMSettings:
    """读配置：界面保存过的优先，其次 .env，最后默认值。"""
    if SETTINGS_FILE.exists():
        try:
            data = json.loads(SETTINGS_FILE.read_text(encoding="utf-8"))
            return LLMSettings(
                base_url=data.get("base_url") or DEEPSEEK_BASE_URL,
                api_key=data.get("api_key") or DEEPSEEK_API_KEY,
                model=data.get("model") or DEEPSEEK_MODEL,
            )
        except (json.JSONDecodeError, OSError):
            pass  # 文件坏了就退回环境变量
    return LLMSettings(
        base_url=DEEPSEEK_BASE_URL,
        api_key=DEEPSEEK_API_KEY,
        model=DEEPSEEK_MODEL,
    )


def save(settings: LLMSettings) -> Path:
    SETTINGS_FILE.parent.mkdir(parents=True, exist_ok=True)
    SETTINGS_FILE.write_text(
        json.dumps(asdict(settings), ensure_ascii=False, indent=2),
        encoding="utf-8",
    )
    return SETTINGS_FILE


def clear() -> None:
    SETTINGS_FILE.unlink(missing_ok=True)
