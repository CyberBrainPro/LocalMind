from datetime import datetime
from typing import Any, Dict, List, Optional

from pydantic import BaseModel


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


class VectorItem(BaseModel):
    id: str
    document: str
    metadata: Optional[Dict[str, Any]] = None


class VectorListResponse(BaseModel):
    items: List[VectorItem]
    total: int
    limit: int
    offset: int
