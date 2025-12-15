import os

from dotenv import load_dotenv


load_dotenv()

LLM_API_KEY = os.getenv("LLM_API_KEY")
LLM_BASE_URL = os.getenv(
    "LLM_BASE_URL",
    "https://dashscope.aliyuncs.com/compatible-mode/v1",
)
LLM_MODEL = os.getenv("LLM_MODEL", "qwen-plus")

if not LLM_API_KEY:
    raise RuntimeError("请先在环境变量或 .env 中设置 LLM_API_KEY")

CHROMA_DB_DIR = "./localmind_db"
FOLDER_CONFIG_FILE = "./localmind_folders.json"

# 支持的文件类型
SUPPORTED_EXTENSIONS = {".txt", ".md", ".markdown"}

# 扫描时要跳过的文件类型
IGNORED_EXTENSIONS = {
    ".excalidraw.md",
    ".excalidraw",
}

