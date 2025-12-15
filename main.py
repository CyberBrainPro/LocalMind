import os
import uuid
from datetime import datetime
from typing import List, Optional

from fastapi import BackgroundTasks, FastAPI, HTTPException, Query
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import FileResponse, HTMLResponse, RedirectResponse
from fastapi.staticfiles import StaticFiles

from app.clients import collection
from app.schemas import (
    ContextChunk,
    FolderConfig,
    FolderCreateRequest,
    FolderListResponse,
    IngestRequest,
    IngestResponse,
    QueryRequest,
    QueryResponse,
    ScanJob,
    ScanJobStatusResponse,
    VectorListResponse,
    VectorItem,
)
from app.services.folders import (
    FOLDER_CONFIGS,
    SCAN_JOBS,
    load_folder_configs,
    save_folder_configs,
)
from app.services.llm import chat_with_llm, chunk_text, embed_texts
from app.services.scanner import run_scan_folder
from app.settings import CHROMA_DB_DIR, LLM_MODEL


app = FastAPI(title="LocalMind MVP with Qwen", version="0.4.0")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


# ========================
#  静态资源挂载
# ========================
for dirname in ("static", "website"):
    if not os.path.exists(dirname):
        os.makedirs(dirname)

app.mount("/static", StaticFiles(directory="static"), name="static")
app.mount("/website", StaticFiles(directory="website"), name="website")


# 启动时加载文件夹配置
load_folder_configs()


@app.get("/")
def index():
    return RedirectResponse(url="/chat")


@app.get("/chat")
def serve_chat():
    chat_path = os.path.join("static", "chat.html")
    if not os.path.exists(chat_path):
        return HTMLResponse(
            "<h1>LocalMind Chat</h1><p>未找到 static/chat.html，请确认文件路径。</p>",
            status_code=404,
        )
    return FileResponse(chat_path)


@app.get("/admin")
def serve_admin():
    admin_path = os.path.join("static", "admin.html")
    if not os.path.exists(admin_path):
        return HTMLResponse(
            "<h1>LocalMind Admin</h1><p>未找到 static/admin.html，请先创建。</p>",
            status_code=404,
        )
    return FileResponse(admin_path)


@app.get("/vectors")
def serve_vectors():
    vec_page = os.path.join("static", "vectors.html")
    if not os.path.exists(vec_page):
        return HTMLResponse(
            "<h1>Vector Store Viewer</h1><p>未找到 static/vectors.html，请先创建。</p>",
            status_code=404,
        )
    return FileResponse(vec_page)


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

    context = "\n\n---\n\n".join(docs)
    answer = chat_with_llm(req.question, context)

    context_chunks = []
    for i, doc in enumerate(docs):
        meta = metas[i] if i < len(metas) else None
        context_chunks.append(ContextChunk(text=doc, metadata=meta))

    return QueryResponse(answer=answer, context_chunks=context_chunks)


@app.get("/folders", response_model=FolderListResponse)
def list_folders(q: Optional[str] = None):
    items = list(FOLDER_CONFIGS.values())
    if q:
        q_lower = q.lower()
        items = [
            cfg
            for cfg in items
            if q_lower in cfg.name.lower() or q_lower in cfg.path.lower()
        ]
    return FolderListResponse(items=items)


@app.get("/files/raw")
def get_raw_file(
    folder_id: str = Query(..., description="FolderConfig 的 ID"),
    path: str = Query(..., description="相对该 folder 的文件路径"),
):
    folder = FOLDER_CONFIGS.get(folder_id)
    if not folder:
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


@app.get("/api/vector-store", response_model=VectorListResponse)
def list_vector_store(
    limit: int = Query(20, ge=1, le=200, description="返回的记录数量"),
    offset: int = Query(0, ge=0, description="跳过的记录数量"),
):
    try:
        total = collection.count()
        data = collection.get(
            limit=limit,
            offset=offset,
            include=["documents", "metadatas"],
        )
    except Exception as exc:
        raise HTTPException(status_code=500, detail=f"查询向量库失败: {exc}")

    ids = data.get("ids") or []
    docs = data.get("documents") or []
    metas = data.get("metadatas") or []

    items: List[VectorItem] = []
    for idx, vector_id in enumerate(ids):
        document = docs[idx] if idx < len(docs) else ""
        metadata = metas[idx] if idx < len(metas) else None
        items.append(
            VectorItem(
                id=vector_id,
                document=document or "",
                metadata=metadata,
            )
        )

    return VectorListResponse(
        items=items,
        total=total,
        limit=limit,
        offset=offset,
    )


@app.post("/folders", response_model=FolderConfig)
def create_folder(req: FolderCreateRequest):
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
    if folder_id in FOLDER_CONFIGS:
        del FOLDER_CONFIGS[folder_id]
        save_folder_configs()
        return {"ok": True}
    raise HTTPException(status_code=404, detail="未找到该文件夹配置")


@app.post("/folders/{folder_id}/scan", response_model=ScanJob)
def start_scan(folder_id: str, background_tasks: BackgroundTasks):
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
    job = SCAN_JOBS.get(job_id)
    if not job:
        raise HTTPException(status_code=404, detail="未找到扫描任务")
    return ScanJobStatusResponse(**job.dict())


@app.get("/scan-jobs", response_model=List[ScanJobStatusResponse])
def list_scan_jobs(folder_id: Optional[str] = None):
    jobs = list(SCAN_JOBS.values())
    if folder_id:
        jobs = [job for job in jobs if job.folder_id == folder_id]
    return [ScanJobStatusResponse(**job.dict()) for job in jobs]
