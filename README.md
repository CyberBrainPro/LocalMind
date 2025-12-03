# LocalMind · 本地 AI 知识助手（Qwen 版 MVP）

LocalMind 是一个 **完全运行在本地的 AI 知识助手**，支持：

- 📚 将任意文本文档转换为可检索的知识库  
- 🔍 基于通义千问（Qwen）进行 RAG 智能问答  
- 🔐 文档不上传外网，隐私 100% 自主可控  
- 🧠 支持向量检索、上下文引用、知识片段解释  
- 💬 内置现代化聊天界面 `/chat`（Vue3 + 静态单页）  

本项目适用于：

- 个人知识管理  
- 本地资料的智能问答  
- 研发团队内部文档系统  
- 需要 **AI + 隐私** 的行业（法律、研究、企业内训等）  

本仓库为 **核心版本（Core）**，仅包含：

- 后端 API（FastAPI + ChromaDB）
- 对接 Qwen 大模型（LLM + Embedding）
- 无编译、可直接用的前端聊天页面

如果你需要 **一键安装版（桌面版 + 前端 + 打包）**  
请查看商业版计划（Coming soon）。

---

## ✨ 功能特点

### 🔍 本地知识库
- `/ingest`：导入文本并切片存储向量  
- `/query`：问题 → 向量检索 → 基于上下文回答  
- 支持 Qwen `text-embedding-v1` 向量模型

### 🤖 通义千问（Qwen）接入
- 兼容 OpenAI API（DashScope compatible mode）
- 可配置模型（如 qwen-plus / qwen-max）

### 💬 自带聊天页面
访问：

```

[http://127.0.0.1:8787/chat](http://127.0.0.1:8787/chat)

````

即可体验现代化聊天界面，可查看引用片段与历史对话。

### 🔐 100% 本地隐私
- 文档存储在本地  
- 向量索引存储在本地  
- 可在后续版本支持完全离线 LLM（Ollama / llama.cpp）

---

## 📦 安装与运行

### 1. 克隆仓库

```bash
git clone https://github.com/yourname/localmind.git
cd localmind
````

### 2. 安装依赖

推荐虚拟环境：

```bash
python -m venv .venv
source .venv/bin/activate              # macOS/Linux
# .venv\Scripts\activate               # Windows

pip install -r requirements.txt
```

### 3. 配置环境变量

创建 `.env`：

```env
LLM_API_KEY=你的通义千问APIKey
LLM_BASE_URL=https://dashscope.aliyuncs.com/compatible-mode/v1
LLM_MODEL=qwen-plus
```

### 4. 启动服务

```bash
uvicorn main:app --reload --port 8787
```

访问：

* API 文档：`http://127.0.0.1:8787/docs`
* 聊天界面：`http://127.0.0.1:8787/chat`

---

## 📁 项目结构

```
localmind/
├─ main.py              # 后端核心
├─ requirements.txt     # 依赖
└─ static/
   └─ chat.html         # Vue3 聊天界面
```

---

## 🧩 API 概览

### 导入文本

```bash
POST /ingest
{
  "text": "你的文档内容…",
  "doc_id": "可选",
  "title": "可选"
}
```

### 问答接口

```bash
POST /query
{
  "question": "你的问题？",
  "top_k": 5
}
```

返回答案 + 上下文切片。


