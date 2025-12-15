import json
import os
from datetime import datetime
from typing import List

from ..clients import collection
from ..schemas import ScanJob
from ..settings import IGNORED_EXTENSIONS, SUPPORTED_EXTENSIONS
from .folders import FOLDER_CONFIGS, SCAN_JOBS, save_folder_configs
from .llm import chunk_text, embed_texts, summarize_document


def run_scan_folder(job_id: str) -> None:
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

    file_paths = _collect_files(base_path)
    job.total_files = len(file_paths)
    job.status = "running"

    for idx, file_path in enumerate(file_paths, start=1):
        try:
            with open(file_path, "r", encoding="utf-8", errors="ignore") as f:
                text = f.read()

            if not text.strip():
                job.processed_files = idx
                continue

            rel_path = os.path.relpath(file_path, base_path)
            doc_id = f"{folder.id}:{rel_path}"

            summary_data = summarize_document(text)
            doc_summary = summary_data.get("summary", "")
            raw_keywords = summary_data.get("keywords", [])
            if isinstance(raw_keywords, list):
                doc_keywords = json.dumps(raw_keywords, ensure_ascii=False)
            elif raw_keywords is None:
                doc_keywords = ""
            else:
                doc_keywords = str(raw_keywords)

            stat = os.stat(file_path)
            mtime = datetime.fromtimestamp(stat.st_mtime)

            chunks = chunk_text(text)
            if not chunks:
                job.processed_files = idx
                continue

            embeddings = embed_texts(chunks)
            ids = [f"{doc_id}::chunk_{i}" for i in range(len(chunks))]

            metadatas = [
                {
                    "folder_id": folder.id,
                    "folder_name": folder.name,
                    "file_path": rel_path,
                    "file_name": os.path.basename(rel_path),
                    "chunk_index": i,
                    "doc_summary": doc_summary,
                    "doc_keywords": doc_keywords,
                    "file_modified_at": mtime.isoformat(),
                    "year": mtime.year,
                    "month": mtime.month,
                }
                for i in range(len(chunks))
            ]

            collection.add(
                ids=ids,
                documents=chunks,
                embeddings=embeddings,
                metadatas=metadatas,
            )

        except Exception as exc:
            job.error_message = f"{file_path}: {exc}"
        finally:
            job.processed_files = idx

    job.status = "completed"
    job.finished_at = datetime.utcnow()
    folder.last_scan_at = job.finished_at
    folder.last_scan_status = job.status
    folder.last_scan_job_id = job.id
    save_folder_configs()


def _collect_files(base_path: str) -> List[str]:
    file_paths: List[str] = []
    for root, _, files in os.walk(base_path):
        for fname in files:
            lower_name = fname.lower()
            if any(lower_name.endswith(ext) for ext in IGNORED_EXTENSIONS):
                continue
            ext = os.path.splitext(fname)[1].lower()
            if ext in SUPPORTED_EXTENSIONS:
                file_paths.append(os.path.join(root, fname))
    return file_paths
