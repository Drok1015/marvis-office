from __future__ import annotations

import os
from dataclasses import dataclass
from pathlib import Path


@dataclass(frozen=True)
class Settings:
    deepseek_api_base_url: str
    deepseek_api_key: str
    deepseek_model: str
    workspace_root: Path

    @property
    def llm_enabled(self) -> bool:
        return bool(self.deepseek_api_key.strip())


def load_settings() -> Settings:
    backend_dir = Path(__file__).resolve().parents[1]
    default_workspace = backend_dir.parent

    return Settings(
        deepseek_api_base_url=os.getenv('DEEPSEEK_API_BASE_URL', 'https://api.deepseek.com').strip(),
        deepseek_api_key=os.getenv('DEEPSEEK_API_KEY', '').strip(),
        deepseek_model=os.getenv('DEEPSEEK_MODEL', 'deepseek-v4-flash').strip(),
        workspace_root=Path(os.getenv('MARVIS_WORKSPACE_ROOT', str(default_workspace))).resolve(),
    )
