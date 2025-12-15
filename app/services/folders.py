import json
import os
from threading import Lock
from typing import Dict

from ..schemas import FolderConfig, ScanJob
from ..settings import FOLDER_CONFIG_FILE


FOLDER_CONFIGS: Dict[str, FolderConfig] = {}
SCAN_JOBS: Dict[str, ScanJob] = {}
scan_lock = Lock()


def load_folder_configs() -> None:
    """从本地 JSON 文件恢复文件夹配置"""
    global FOLDER_CONFIGS
    if not os.path.exists(FOLDER_CONFIG_FILE):
        return
    try:
        with open(FOLDER_CONFIG_FILE, "r", encoding="utf-8") as f:
            raw = json.load(f)
        FOLDER_CONFIGS = {
            fid: FolderConfig.parse_obj(cfg) for fid, cfg in raw.items()
        }
    except Exception as exc:  # pragma: no cover - 仅日志
        print("[WARN] 加载本地文件夹配置失败：", exc)


def save_folder_configs() -> None:
    """持久化文件夹配置"""
    try:
        data = {fid: json.loads(cfg.json()) for fid, cfg in FOLDER_CONFIGS.items()}
        with open(FOLDER_CONFIG_FILE, "w", encoding="utf-8") as f:
            json.dump(data, f, ensure_ascii=False, indent=2)
    except Exception as exc:  # pragma: no cover - 仅日志
        print("[WARN] 保存本地文件夹配置失败：", exc)

