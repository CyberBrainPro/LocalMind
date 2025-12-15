<p align="center">
  <img src="/assets/logo.png" alt="LocalMind Logo" width="96">
</p>

<h1 align="center">LocalMind · 本地 AI 知识助手</h1>

<p align="center">
  <b>把你的本地文档变成可对话的私有知识库，隐私本地化，全程自主掌控。</b><br>
  支持 Qwen（通义千问）模型、本地向量库、现代化前端界面。
</p>

<p align="center">
  <a href="#-快速开始">⚡ 快速开始</a> ·
  <a href="#-主要特性">✨ 功能特色</a> ·
  <a href="#-预览">🖼 预览</a> ·
  <a href="#-路线图-roadmap">🗺 Roadmap</a> ·
  <a href="#-license">📜 License</a>
</p>

---

<p align="center">
  <a href="https://github.com/CyberBrainPro/LocalMind/stargazers">
    <img src="https://img.shields.io/github/stars/CyberBrainPro/LocalMind?style=flat-square&color=3b82f6" />
  </a>
  <a href="https://github.com/CyberBrainPro/LocalMind/issues">
    <img src="https://img.shields.io/github/issues/CyberBrainPro/LocalMind?style=flat-square&color=f97316" />
  </a>
  <a href="https://github.com/CyberBrainPro/LocalMind/blob/main/LICENSE">
    <img src="https://img.shields.io/github/license/CyberBrainPro/LocalMind?style=flat-square&color=22c55e" />
  </a>
  <img src="https://img.shields.io/badge/Python-3.10+-3776ab?style=flat-square&logo=python&logoColor=white" />
  <img src="https://img.shields.io/badge/FastAPI-0.111+-009688?style=flat-square&logo=fastapi&logoColor=white" />
  <img src="https://img.shields.io/badge/LLM-Qwen%20(通义千问)-8b5cf6?style=flat-square" />
  <img src="https://img.shields.io/badge/VectorDB-Chroma-22c55e?style=flat-square" />
</p>

---

## 🧠 什么是 LocalMind？

**LocalMind 是一个完全运行在本地的 AI 知识助手。**

它可以：

- 将你的本地文档（文本）转成知识库  
- 使用向量检索理解文件内容  
- 通过 Qwen（通义千问）进行智能问答  
- 提供现代化前端对话界面 `/chat`  
- 文档与向量全部存储在本机，隐私 0 泄漏  

你可以把它理解为：

> **“国产 Obsidian + RAG AI 的轻量版本地知识助手 MVP”**

未来会提供桌面版本、一键安装、自动解析 PDF/Word/Markdown 的 Pro 版本。

---

## 🖼 预览

<p align="center">
  <img src="/assets/screenshot-chat.png" width="85%" alt="LocalMind Chat UI">
</p>

<p align="center"><em>▲ LocalMind 内置聊天界面，可查看引用知识块与上下文。</em></p>

<p align="center">
  <img src="/assets/screenshot-admin.png" width="85%" alt="LocalMind Chat UI">
</p>

<p align="center"><em>▲ LocalMind 内置管理界面，可查看和配置本地知识库目录。</em></p>

---

## ⚡ 快速开始

<div align="center">

| 步骤 | 操作 |
|------|------|
| 1️⃣ | `git clone https://github.com/CyberBrainPro/LocalMind.git` |
| 2️⃣ | 安装依赖：`pip install -r requirements.txt` |
| 3️⃣ | 创建 `.env` 并填入 Qwen API Key |
| 4️⃣ | 启动服务：`uvicorn main:app --reload --port 8787` |
| 5️⃣ | （可选）若修改前端，在 `webui/` 中运行 `npm install && npm run build`，产物会输出到 `static/` |
| 6️⃣ | 访问：`http://127.0.0.1:8787/chat` |

</div>

### 🔧 前端构建说明

前端源码位于 `webui/`（Vite + Vue3），构建步骤如下：

```bash
cd webui
npm install          # 首次安装依赖；在不同架构的机器上请重新执行
npm run dev          # 本地预览（可选）
npm run build        # 构建产物，自动写入 ../static
```

> 注意：如果换机器或切换芯片架构，请删除 `webui/node_modules` 并重新 `npm install`，以避免 esbuild 等二进制依赖报错。

## 🧩 环境变量配置（.env 示例）

在项目根目录创建 `.env` 文件, 开源参考 .env.example：

```env
# 通义千问 API Key（必填）
LLM_API_KEY=your-dashscope-api-key-here

# Qwen OpenAI 兼容模式 Base URL（可选，不写则使用默认值）
LLM_BASE_URL=https://dashscope.aliyuncs.com/compatible-mode/v1

# 默认模型（可选）
LLM_MODEL=qwen-plus
```

---

## ✨ 主要特性

### 🔍 本地私有知识库
- 文档 → 切片 → 向量 → RAG 检索  
- 不上传任何文档到云端  
- 灵活的切片策略（可替换、可扩展）

### 🤖 通义千问（Qwen）支持
- 兼容 OpenAI API 调用方式  
- 支持 `qwen-plus`、`qwen-max` 等模型  
- 配置简单：`.env` 控制

### 🧠 本地向量库（ChromaDB）
- 内置本地数据库（无需服务器）  
- 持久化到 `./localmind_db/`

### 💬 内置 Chat UI `/chat`
- Vue3 + 无编译静态文件  
- 支持对话历史  
- 支持查看引用的文档片段  
- 现代化视觉风格（深色主题）

---

## 📁 项目结构

```

LocalMind/
├─ main.py              # 后端核心逻辑（FastAPI）
├─ requirements.txt     # 依赖
├─ localmind_db/        # Chroma 持久化向量库（自动生成）
└─ static/
    └─ chat.html         # 前端聊天界面（Vue3 单文件）

````

---

## 🔌 API 说明

### /ingest 导入文本

```json
POST /ingest
{
  "text": "你的内容……",
  "doc_id": "可选",
  "title": "可选"
}
````

### /query 智能问答

```json
POST /query
{
  "question": "你的问题？",
  "top_k": 5
}
```

---

## 🗺 路线图 Roadmap

* [x] Qwen 接入（LLM + embedding）
* [x] 本地向量库（Chroma）+ RAG
* [x] 强隐私：文档不上传
* [x] 前端聊天界面 `/chat`
* [ ] PDF / Word / Markdown 文件解析
* [ ] 多知识库（按项目/主题分类）
* [ ] 收藏对话 / 导出
* [ ] 文档文件夹自动监控（类似 Obsidian Vault）
* [ ] 流式回答（Streaming）
* [ ] 桌面版（Windows/macOS/Linux）
* [ ] 企业私有部署版本（Pro / Enterprise）

> 想关注项目进展？欢迎点一颗 ⭐ Star！

---

## 🧭 Open Core 模式

LocalMind 采用 **Open Core（开放核心）** 商业策略：

### 开源部分（本仓库）

* 核心 RAG 逻辑
* Qwen 接入
* FastAPI 服务
* 本地向量库
* 聊天前端（/chat）

### 商业增强版（计划中）

* 桌面应用（Windows/macOS/Linux）
* 一键安装程序
* PDF/Word/Markdown 自动解析
* 多知识库 UI
* 本地模型加速引擎
* 文件夹自动同步
* 团队协作 / 企业管理后台

> 核心开源保证透明与可信，商业版本支持项目可持续发展。

---

## 📜 License

本项目使用 **Apache License 2.0**

这意味着你可以：

* 商业使用
* 修改
* 分发
* 在衍生项目中闭源核心逻辑

但需保留完整版权和 LICENSE 声明。

---

## ⭐ 支持项目

如果 LocalMind 对你有帮助，请考虑给仓库点个 Star：

👉 [https://github.com/CyberBrainPro/LocalMind](https://github.com/CyberBrainPro/LocalMind)

你的支持会影响项目路线图的优先级排序。

---

<p align="center">Made with ❤️ by CyberBrainPro · 2025</p>
