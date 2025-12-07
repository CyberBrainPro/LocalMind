import os
import uuid
from typing import List, Optional

from fastapi import FastAPI, HTTPException
from fastapi.responses import FileResponse, HTMLResponse
from fastapi.staticfiles import StaticFiles
from fastapi.middleware.cors import CORSMiddleware
from fastapi import BackgroundTasks
from fastapi.responses import RedirectResponse

from pydantic import BaseModel

import chromadb
from chromadb.config import Settings

from openai import OpenAI
from dotenv import load_dotenv

from datetime import datetime
from threading import Lock
from typing import Dict
from fastapi import Query
import json


# ========================
#  环境变量
# ========================
load_dotenv()

LLM_API_KEY = os.getenv("LLM_API_KEY")
LLM_BASE_URL = os.getenv("LLM_BASE_URL", "https://dashscope.aliyuncs.com/compatible-mode/v1")
LLM_MODEL = os.getenv("LLM_MODEL", "qwen-plus")

if not LLM_API_KEY:
    raise RuntimeError("请先在环境变量或 .env 中设置 LLM_API_KEY")


# ========================
#  初始化 LLM 客户端（Qwen）
# ========================
client = OpenAI(
    api_key=LLM_API_KEY,
    base_url=LLM_BASE_URL,
)


# ========================
#  初始化 Chroma 本地向量库
# ========================
CHROMA_DB_DIR = "./localmind_db"

chroma_client = chromadb.PersistentClient(
    path=CHROMA_DB_DIR,
    settings=Settings(anonymized_telemetry=False)
)

collection = chroma_client.get_or_create_collection("localmind_default")


# ========================
#  FastAPI 初始化 + CORS
# ========================
app = FastAPI(title="LocalMind MVP with Qwen", version="0.4.0")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],    # 开发阶段可以全开，后续再收紧
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


# ========================
#  静态资源挂载
# ========================

# 确保 static 目录存在（用于 chat.html）
if not os.path.exists("static"):
    os.makedirs("static")

# 如果你未来想在网站里引用本地资源（JS/CSS/图片），可以把它们放到 website/ 并通过 /website 访问
if not os.path.exists("website"):
    os.makedirs("website")

# 静态目录挂载
app.mount("/static", StaticFiles(directory="static"), name="static")
app.mount("/website", StaticFiles(directory="website"), name="website")


# ========================
#  页面路由：Landing Page + Chat
# ========================

@app.get("/")
def index():
    return RedirectResponse(url="/chat")


@app.get("/chat")
def serve_chat():
    """
    访问 /chat 时，返回 static/chat.html
    """
    chat_path = os.path.join("static", "chat.html")
    if not os.path.exists(chat_path):
        return HTMLResponse(
            "<h1>LocalMind Chat</h1><p>未找到 static/chat.html，请确认文件路径。</p>",
            status_code=404,
        )
    return FileResponse(chat_path)


@app.get("/admin")
def serve_admin():
    """
    后台管理页面：文件夹配置 + 扫描进度
    """
    admin_path = os.path.join("static", "admin.html")
    if not os.path.exists(admin_path):
        return HTMLResponse(
            "<h1>LocalMind Admin</h1><p>未找到 static/admin.html，请先创建。</p>",
            status_code=404,
        )
    return FileResponse(admin_path)


# ========================
#  数据模型
# ========================
class IngestRequest(BaseModel):
    text: str
    doc_id: Optional[str] = None
    title: Optional[str] = None


class IngestResponse(BaseModel):
    doc_id: str
    chunks: int


class QueryRequest(BaseModel):
    question: str
    top_k: int = 5


class ContextChunk(BaseModel):
    text: str
    metadata: Optional[dict] = None


class QueryResponse(BaseModel):
    answer: str
    context_chunks: List[ContextChunk]

# ========================
#  后台管理：文件夹配置 & 扫描任务
# ========================

class FolderConfig(BaseModel):
    id: str
    name: str
    path: str
    created_at: datetime
    last_scan_at: Optional[datetime] = None
    last_scan_status: Optional[str] = None
    last_scan_job_id: Optional[str] = None


class FolderCreateRequest(BaseModel):
    name: str
    path: str


class FolderListResponse(BaseModel):
    items: List[FolderConfig]


class ScanJob(BaseModel):
    id: str
    folder_id: str
    status: str  # pending / running / completed / error
    total_files: int = 0
    processed_files: int = 0
    error_message: Optional[str] = None
    started_at: datetime
    finished_at: Optional[datetime] = None


class ScanJobStatusResponse(BaseModel):
    id: str
    folder_id: str
    status: str
    total_files: int
    processed_files: int
    error_message: Optional[str] = None
    started_at: datetime
    finished_at: Optional[datetime] = None


FOLDER_CONFIG_FILE = "./localmind_folders.json"

FOLDER_CONFIGS: Dict[str, FolderConfig] = {}
SCAN_JOBS: Dict[str, ScanJob] = {}
scan_lock = Lock()


def load_folder_configs():
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
    except Exception as e:
        print("[WARN] 加载本地文件夹配置失败：", e)


def save_folder_configs():
    """把当前文件夹配置持久化到 JSON（支持 datetime）"""
    try:
        # 用 Pydantic 的 json() 帮我们处理 datetime → ISO 字符串
        data = {fid: json.loads(cfg.json()) for fid, cfg in FOLDER_CONFIGS.items()}
        with open(FOLDER_CONFIG_FILE, "w", encoding="utf-8") as f:
            json.dump(data, f, ensure_ascii=False, indent=2)
    except Exception as e:
        print("[WARN] 保存本地文件夹配置失败：", e)

# 启动时尝试恢复历史配置
load_folder_configs()

# 支持的文件后缀（MVP：只处理纯文本类型）
SUPPORTED_EXTENSIONS = {".txt", ".md", ".markdown"}

# 扫描时要忽略的文件扩展（excalidraw 是特殊格式，不能当 md 向量化）
IGNORED_EXTENSIONS = {
    ".excalidraw.md",  # Excalidraw 的复合格式，不是文本文档
    ".excalidraw",     # 如果有人用这种后缀
}

# ========================
# 工具函数 - 文本切分
# ========================
def chunk_text(text: str, max_chars: int = 500):
    text = text.strip()
    if len(text) <= max_chars:
        return [text]
    return [text[i:i + max_chars] for i in range(0, len(text), max_chars)]


# ========================
# 工具函数 - 向量生成（Qwen embedding）
# ========================
def embed_texts(texts: List[str]) -> List[List[float]]:
    resp = client.embeddings.create(
        model="text-embedding-v1",
        input=texts
    )
    return [item.embedding for item in resp.data]


# ========================
# 工具函数 - Chat（Qwen）
# ========================
def chat_with_llm(question: str, context: str) -> str:
    system_prompt = (
        "你是一个本地知识助手。"
        "你只能根据提供的上下文回答问题，不允许幻想、不允许胡编。"
        "如果上下文中没有答案，请回答：'我不知道'。"
    )

    user_prompt = (
        f"用户问题：{question}\n\n"
        f"以下是与问题相关的文档内容，请基于此回答：\n{context}"
    )

    completion = client.chat.completions.create(
        model=LLM_MODEL,
        messages=[
            {"role": "system", "content": system_prompt},
            {"role": "user", "content": user_prompt},
        ],
        temperature=0.2,
    )

    return completion.choices[0].message.content.strip()


def run_scan_folder(job_id: str):
    """后台任务：扫描文件夹并向量化"""
    job = SCAN_JOBS.get(job_id)
    if not job:
        return

    folder = FOLDER_CONFIGS.get(job.folder_id)
    if not folder:
        job.status = "error"
        job.error_message = "FolderConfig not found"
        job.finished_at = datetime.utcnow()
        return

    base_path = folder.path
    if not os.path.isdir(base_path):
        job.status = "error"
        job.error_message = f"目录不存在：{base_path}"
        job.finished_at = datetime.utcnow()
        return

    # 收集要处理的文件列表
    file_paths: List[str] = []
    for root, dirs, files in os.walk(base_path):
        for fname in files:
            # 判断是否在忽略列表
            lower_name = fname.lower()
            if any(lower_name.endswith(ext) for ext in IGNORED_EXTENSIONS):
                continue  # 直接跳过
            ext = os.path.splitext(fname)[1].lower()
            if ext in SUPPORTED_EXTENSIONS:
                file_paths.append(os.path.join(root, fname))

    job.total_files = len(file_paths)
    job.status = "running"

    # 简单策略：当前版本不做去重，后续可以按 folder_id/file_path 清理旧数据
    for idx, file_path in enumerate(file_paths, start=1):
        try:
            with open(file_path, "r", encoding="utf-8", errors="ignore") as f:
                text = f.read()

            if not text.strip():
                job.processed_files = idx
                continue

            rel_path = os.path.relpath(file_path, base_path)
            doc_id = f"{folder.id}:{rel_path}"

            chunks = chunk_text(text)
            embeddings = embed_texts(chunks)

            ids = [f"{doc_id}::chunk_{i}" for i in range(len(chunks))]
            metadatas = [
                {
                    "folder_id": folder.id,
                    "folder_name": folder.name,
                    "file_path": rel_path,
                    "chunk_index": i,
                }
                for i in range(len(chunks))
            ]

            collection.add(
                ids=ids,
                documents=chunks,
                embeddings=embeddings,
                metadatas=metadatas,
            )

        except Exception as e:
            job.error_message = f"{file_path}: {e}"
        finally:
            job.processed_files = idx

    job.status = "completed"
    job.finished_at = datetime.utcnow()
    folder.last_scan_at = job.finished_at
    folder.last_scan_status = job.status
    folder.last_scan_job_id = job.id
    save_folder_configs()


# ========================
# API: 健康检查 / 调试
# ========================
@app.get("/api/status")
def api_status():
    return {
        "message": "LocalMind MVP (Qwen version) running",
        "model": LLM_MODEL,
        "vector_db": CHROMA_DB_DIR,
        "routes": {
            "landing_page": "/",
            "chat_page": "/chat",
            "ingest_api": "/ingest",
            "query_api": "/query",
        },
    }


# ========================
# API: 导入文本
# ========================
@app.post("/ingest", response_model=IngestResponse)
def ingest_text(req: IngestRequest):
    if not req.text.strip():
        raise HTTPException(status_code=400, detail="text 不能为空")

    doc_id = req.doc_id or str(uuid.uuid4())
    title = req.title or f"Doc-{doc_id[:8]}"

    chunks = chunk_text(req.text)
    embeddings = embed_texts(chunks)

    ids = [f"{doc_id}_{i}" for i in range(len(chunks))]
    metadatas = [
        {"doc_id": doc_id, "chunk_index": i, "title": title}
        for i in range(len(chunks))
    ]

    collection.add(
        ids=ids,
        documents=chunks,
        metadatas=metadatas,
        embeddings=embeddings,
    )

    return IngestResponse(doc_id=doc_id, chunks=len(chunks))


# ========================
# API: 问答
# ========================
@app.post("/query", response_model=QueryResponse)
def query_knowledge(req: QueryRequest):
    if not req.question.strip():
        raise HTTPException(status_code=400, detail="question 不能为空")

    qvec = embed_texts([req.question])[0]

    result = collection.query(
        query_embeddings=[qvec],
        n_results=req.top_k,
    )

    docs = (result.get("documents") or [[]])[0]
    metas = (result.get("metadatas") or [[]])[0]

    if not docs:
        return QueryResponse(
            answer="知识库中没有相关内容，请先导入文档。",
            context_chunks=[],
        )

    # 构造上下文字符串给 LLM 使用
    context = "\n\n---\n\n".join(docs)

    answer = chat_with_llm(req.question, context)

    # 把文档 + 元数据一起返回前端
    context_chunks = []
    for i, d in enumerate(docs):
        meta = metas[i] if i < len(metas) else None
        context_chunks.append(ContextChunk(text=d, metadata=meta))

    return QueryResponse(answer=answer, context_chunks=context_chunks)

# ========================
# API: 文件夹配置管理
# ========================

@app.get("/folders", response_model=FolderListResponse)
def list_folders(q: Optional[str] = None):
    """
    列出当前配置的所有监控文件夹，可选按名称/路径模糊搜索
    """
    items = list(FOLDER_CONFIGS.values())
    if q:
        q_lower = q.lower()
        items = [
            f
            for f in items
            if q_lower in f.name.lower() or q_lower in f.path.lower()
        ]
    return FolderListResponse(items=items)

@app.get("/files/raw")
def get_raw_file(
    folder_id: str = Query(..., description="FolderConfig 的 ID"),
    path: str = Query(..., description="相对该 folder 的文件路径"),
):
    """
    根据 folder_id + 相对路径，返回原始文件内容。
    用于在前端“引用来源”中点击预览/下载。
    """
    folder = FOLDER_CONFIGS.get(folder_id)
    if not folder:
        # 尝试从本地 JSON 重新加载一遍（可能是刚重启服务）
        load_folder_configs()
        folder = FOLDER_CONFIGS.get(folder_id)

    if not folder:
        raise HTTPException(status_code=404, detail="未找到对应的文件夹配置")

    base = os.path.realpath(folder.path)
    target = os.path.realpath(os.path.join(folder.path, path))

    if not target.startswith(base):
        raise HTTPException(status_code=400, detail="非法路径")

    if not os.path.exists(target):
        raise HTTPException(status_code=404, detail="文件不存在")

    filename = os.path.basename(target)
    return FileResponse(target, filename=filename)

    # 计算绝对路径，并做一次越界防护
    base = os.path.realpath(folder.path)
    target = os.path.realpath(os.path.join(folder.path, path))

    if not target.startswith(base):
        raise HTTPException(status_code=400, detail="非法路径")

    if not os.path.exists(target):
        raise HTTPException(status_code=404, detail="文件不存在")

    # FileResponse 默认是 inline，浏览器会尽量预览，不行就下载
    filename = os.path.basename(target)
    return FileResponse(target, filename=filename)

@app.post("/folders", response_model=FolderConfig)
def create_folder(req: FolderCreateRequest):
    """
    新增一个监控文件夹
    """
    path = os.path.abspath(req.path)
    if not os.path.isdir(path):
        raise HTTPException(status_code=400, detail="path 不是有效的文件夹")

    folder_id = str(uuid.uuid4())
    cfg = FolderConfig(
        id=folder_id,
        name=req.name,
        path=path,
        created_at=datetime.utcnow(),
    )
    FOLDER_CONFIGS[folder_id] = cfg
    save_folder_configs()
    return cfg


@app.delete("/folders/{folder_id}")
def delete_folder(folder_id: str):
    """
    删除一个监控文件夹配置（不删除向量库中已有数据）
    """
    if folder_id in FOLDER_CONFIGS:
        del FOLDER_CONFIGS[folder_id]
        save_folder_configs()
        return {"ok": True}
    raise HTTPException(status_code=404, detail="未找到该文件夹配置")

# ========================
# API: 扫描文件夹 & 进度查询
# ========================

@app.post("/folders/{folder_id}/scan", response_model=ScanJob)
def start_scan(folder_id: str, background_tasks: BackgroundTasks):
    """
    启动一个扫描任务（后台执行），返回 job 信息
    """
    folder = FOLDER_CONFIGS.get(folder_id)
    if not folder:
        raise HTTPException(status_code=404, detail="未找到该文件夹配置")

    job_id = str(uuid.uuid4())
    job = ScanJob(
        id=job_id,
        folder_id=folder_id,
        status="pending",
        total_files=0,
        processed_files=0,
        started_at=datetime.utcnow(),
    )
    SCAN_JOBS[job_id] = job

    background_tasks.add_task(run_scan_folder, job_id)
    return job


@app.get("/scan-jobs/{job_id}", response_model=ScanJobStatusResponse)
def get_scan_job(job_id: str):
    """
    查询单个扫描任务的进度
    """
    job = SCAN_JOBS.get(job_id)
    if not job:
        raise HTTPException(status_code=404, detail="未找到扫描任务")
    return ScanJobStatusResponse(**job.dict())


@app.get("/scan-jobs", response_model=List[ScanJobStatusResponse])
def list_scan_jobs(folder_id: Optional[str] = None):
    """
    （可选）列出所有扫描任务，支持按 folder_id 过滤
    """
    jobs = list(SCAN_JOBS.values())
    if folder_id:
        jobs = [j for j in jobs if j.folder_id == folder_id]
    return [ScanJobStatusResponse(**j.dict()) for j in jobs]


