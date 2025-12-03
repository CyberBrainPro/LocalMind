import os
import uuid
from typing import List, Optional

from fastapi import FastAPI, HTTPException
from fastapi.responses import FileResponse, HTMLResponse
from fastapi.staticfiles import StaticFiles
from fastapi.middleware.cors import CORSMiddleware

from pydantic import BaseModel

import chromadb
from chromadb.config import Settings

from openai import OpenAI
from dotenv import load_dotenv


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

@app.get("/", response_class=HTMLResponse)
def serve_index():
    """
    访问根路径 / 时，返回 website/index.html
    """
    index_path = os.path.join("website", "index.html")
    if not os.path.exists(index_path):
        # 如果忘记放文件，给个提示
        return HTMLResponse(
            "<h1>LocalMind</h1><p>未找到 website/index.html，请确认文件路径。</p>",
            status_code=404,
        )
    return FileResponse(index_path)


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


class QueryResponse(BaseModel):
    answer: str
    context_chunks: List[str]


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

    docs = result.get("documents", [[]])[0]
    if not docs:
        return QueryResponse(
            answer="知识库中没有相关内容，请先导入文档。",
            context_chunks=[],
        )

    context = "\n\n---\n\n".join(docs)
    answer = chat_with_llm(req.question, context)

    return QueryResponse(answer=answer, context_chunks=docs)
