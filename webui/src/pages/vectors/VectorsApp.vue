<template>
  <div class="app-shell">
    <div class="shell-header">
      <div class="brand">
        <div class="logo">LM</div>
        <div>
          <div class="title">LocalMind Vectors</div>
          <div class="subtitle">向量数据库预览</div>
        </div>
      </div>
      <div class="header-right">
        <div class="status-dot"></div>
        <span>总记录：<span>{{ total }}</span></span>
        <span class="badge">Vectors</span>
        <a class="nav-link" href="/admin">返回管理</a>
        <a class="nav-link" href="/chat">前往对话</a>
      </div>
    </div>

    <div class="shell-body">
      <div class="panel">
        <div class="panel-header">
          <div>
            <div class="panel-title">向量存储内容</div>
            <div class="panel-desc">查看已导入的文本片段及其元数据，支持分页浏览。</div>
          </div>
          <button class="btn" @click="refresh" :disabled="loading">刷新</button>
        </div>
        <div class="panel-desc">{{ summaryText }}</div>
        <div class="control-row">
          <label class="control-label">
            每页条数
            <input type="number" min="1" max="200" v-model.number="limit" />
          </label>
        </div>

        <div class="list-wrapper">
          <div v-if="!items.length" class="empty-tip">{{ tableMessage }}</div>
          <div v-else class="vector-list">
            <div v-for="item in items" :key="item.id" class="vector-card">
              <div class="card-header">
                <div class="card-id" title="向量 ID">{{ item.id }}</div>
                <button class="btn btn-light" @click="openDetail(item)">查看详情</button>
              </div>
              <div class="card-snippet">{{ sanitizeDocument(item.document) }}</div>
              <div class="card-meta">
                {{ metadataSummary(item.metadata) }}
              </div>
            </div>
          </div>
        </div>

        <div class="pagination">
          <button class="btn" @click="prevPage" :disabled="!canPrev">上一页</button>
          <span class="page-info" v-if="items.length">{{ pageInfo }}</span>
          <button class="btn" @click="nextPage" :disabled="!canNext">下一页</button>
        </div>
      </div>
    </div>

    <div class="shell-footer">
      <div class="footer-left">
        <span>LocalMind · 向量数据浏览</span>
        <span>仅列表区域滚动，便于稳定查看</span>
      </div>
      <div class="footer-links">
        <a href="/admin">Admin</a>
        <a href="/chat">Chat</a>
      </div>
    </div>

    <div v-if="detailItem" class="detail-overlay">
      <div class="detail-modal">
        <button class="detail-close" @click="closeDetail">&times;</button>
        <div class="detail-content">
          <div class="detail-section">
            <div class="detail-label">ID</div>
            <div class="detail-value">{{ detailItem.id }}</div>
          </div>
          <div class="detail-section">
            <div class="detail-label">Document</div>
            <div class="detail-value detail-text">{{ detailItem.document }}</div>
          </div>
          <div class="detail-section">
            <div class="detail-label">Metadata</div>
            <pre class="detail-pre">{{ renderMetadata(detailItem.metadata) }}</pre>
          </div>
        </div>
      </div>
    </div>
  </div>
</template>

<script setup>
import { computed, onMounted, ref, watch } from "vue";

const items = ref([]);
const total = ref(0);
const limit = ref(20);
const offset = ref(0);
const loading = ref(false);
const summaryText = ref("加载中...");
const tableMessage = ref("加载中...");
const detailItem = ref(null);
const pendingFetch = ref(false);

const fetchVectors = async () => {
  if (loading.value) {
    pendingFetch.value = true;
    return;
  }
  loading.value = true;
  tableMessage.value = "加载中...";
  items.value = [];

  const cleanedLimit = Number.isFinite(limit.value) ? limit.value : 20;
  limit.value = Math.min(Math.max(cleanedLimit, 1), 200);

  try {
    const resp = await fetch(`/api/vector-store?limit=${limit.value}&offset=${offset.value}`);
    if (!resp.ok) {
      throw new Error(`请求失败: ${resp.status}`);
    }
    const data = await resp.json();
    total.value = data.total ?? 0;
    limit.value = data.limit ?? limit.value;
    offset.value = data.offset ?? offset.value;
    items.value = data.items || [];

    if (!items.value.length) {
      tableMessage.value = "向量库为空，尚未导入内容。";
      summaryText.value = tableMessage.value;
    } else {
      const start = offset.value + 1;
      const end = Math.min(offset.value + items.value.length, total.value);
      summaryText.value = `展示第 ${start} - ${end} 条，共 ${total.value} 条记录`;
      tableMessage.value = "";
    }
  } catch (e) {
    console.error(e);
    tableMessage.value = `加载失败：${e.message}`;
    summaryText.value = "无法加载向量数据。";
  } finally {
    loading.value = false;
    if (pendingFetch.value) {
      pendingFetch.value = false;
      fetchVectors();
    }
  }
};

const refresh = () => {
  offset.value = 0;
  fetchVectors();
};

const prevPage = () => {
  if (offset.value <= 0) return;
  offset.value = Math.max(0, offset.value - limit.value);
  fetchVectors();
};

const nextPage = () => {
  const nextOffset = offset.value + limit.value;
  if (nextOffset >= total.value) return;
  offset.value = nextOffset;
  fetchVectors();
};

const sanitizeDocument = (doc) => {
  if (!doc) return "";
  const str = String(doc);
  return str.length > 200 ? `${str.slice(0, 200)}...` : str;
};

const renderMetadata = (meta) => {
  if (!meta || typeof meta !== "object") return "";
  try {
    return JSON.stringify(meta, null, 2);
  } catch (e) {
    return "Invalid metadata";
  }
};

const metadataSummary = (meta) => {
  if (!meta || typeof meta !== "object") return "无元数据";
  if (meta.file_name || meta.folder_name) {
    const folder = meta.folder_name || "未知文件夹";
    const file = meta.file_name || meta.doc_id || "未知文件";
    return `${folder} · ${file}`;
  }
  const entries = Object.entries(meta).slice(0, 3);
  if (!entries.length) return "无元数据";
  return entries.map(([key, value]) => `${key}: ${value}`).join(" · ");
};

const openDetail = (item) => {
  detailItem.value = item;
};

const closeDetail = () => {
  detailItem.value = null;
};

const canPrev = computed(() => offset.value > 0);
const canNext = computed(() => offset.value + limit.value < total.value);
const pageInfo = computed(() => {
  if (!items.value.length) return "";
  const start = offset.value + 1;
  const end = Math.min(offset.value + items.value.length, total.value);
  return `第 ${start} - ${end} 条`;
});

watch(
  () => limit.value,
  (newVal, oldVal) => {
    if (newVal === oldVal) return;
    offset.value = 0;
    fetchVectors();
  }
);

onMounted(() => {
  fetchVectors();
});
</script>

<style scoped>
:global(:root) {
  color-scheme: dark light;
  --bg: #020617;
  --panel: #020617;
  --border: rgba(148, 163, 184, 0.35);
  --accent: #3b82f6;
  --accent-soft: rgba(59, 130, 246, 0.16);
  --text: #e5e7eb;
  --text-soft: #94a3b8;
  --header-height: 76px;
  --footer-height: 56px;
}

:global(html) {
  height: 100%;
}

:global(*) {
  box-sizing: border-box;
  margin: 0;
  padding: 0;
}

:global(body) {
  font-family: system-ui, -apple-system, BlinkMacSystemFont, "Segoe UI", sans-serif;
  background: radial-gradient(circle at top, #1f2937 0, #020617 50%, #000 100%);
  color: var(--text);
  margin: 0;
  min-height: 100vh;
  overflow: hidden;
}

.app-shell {
  width: 100%;
  min-height: 100vh;
  position: relative;
  border-radius: 0;
  border: 1px solid var(--border);
  background: radial-gradient(circle at top left, #111827, #020617);
  box-shadow: 0 26px 70px rgba(15, 23, 42, 0.9), 0 0 0 1px rgba(15, 23, 42, 0.8);
  padding-top: var(--header-height);
  padding-bottom: var(--footer-height);
  overflow: hidden;
}

.shell-header {
  position: absolute;
  top: 0;
  left: 0;
  right: 0;
  height: var(--header-height);
  padding: 14px 18px;
  border-bottom: 1px solid var(--border);
  display: flex;
  justify-content: space-between;
  align-items: center;
  backdrop-filter: blur(16px);
  background: linear-gradient(to bottom, rgba(15, 23, 42, 0.95), rgba(15, 23, 42, 0.9));
}

.brand {
  display: flex;
  align-items: center;
  gap: 10px;
}

.logo {
  width: 30px;
  height: 30px;
  border-radius: 12px;
  background: radial-gradient(circle at 30% 15%, #bfdbfe, #60a5fa 40%, #1d4ed8);
  border: 1px solid rgba(191, 219, 254, 0.6);
  display: flex;
  align-items: center;
  justify-content: center;
  font-size: 16px;
  font-weight: 700;
  color: #020617;
  box-shadow: 0 12px 24px rgba(15, 23, 42, 0.9), 0 0 0 1px rgba(15, 23, 42, 0.7);
}

.title {
  font-size: 15px;
  font-weight: 600;
  letter-spacing: 0.03em;
}

.subtitle {
  font-size: 11px;
  color: var(--text-soft);
}

.header-right {
  display: flex;
  align-items: center;
  gap: 10px;
  font-size: 12px;
  color: var(--text-soft);
}

.status-dot {
  width: 8px;
  height: 8px;
  border-radius: 999px;
  background: #22c55e;
  box-shadow: 0 0 0 5px rgba(34, 197, 94, 0.3);
}

.badge {
  padding: 3px 8px;
  border-radius: 999px;
  border: 1px solid var(--border);
  font-size: 10px;
  letter-spacing: 0.08em;
  text-transform: uppercase;
}

.nav-link {
  padding: 6px 10px;
  border-radius: 8px;
  background: rgba(59, 130, 246, 0.15);
  border: 1px solid rgba(59, 130, 246, 0.4);
  color: #93c5fd;
  text-decoration: none;
  font-size: 12px;
  margin-right: 4px;
  transition: 0.15s ease;
}

.nav-link:hover {
  background: rgba(59, 130, 246, 0.35);
  border-color: rgba(147, 197, 253, 0.8);
  color: #e0f2fe;
}

.shell-body {
  position: absolute;
  top: var(--header-height);
  bottom: var(--footer-height);
  left: 0;
  right: 0;
  padding: 16px 24px;
  overflow: hidden;
  min-height: 0;
}

.shell-footer {
  position: absolute;
  bottom: 0;
  left: 0;
  right: 0;
  height: var(--footer-height);
  padding: 0 18px;
  border-top: 1px solid var(--border);
  display: flex;
  align-items: center;
  justify-content: space-between;
  background: rgba(2, 6, 23, 0.92);
  color: var(--text-soft);
  font-size: 12px;
}

.footer-left {
  display: flex;
  flex-direction: column;
  gap: 2px;
}

.footer-links {
  display: flex;
  gap: 12px;
}

.footer-links a {
  color: var(--text);
  text-decoration: none;
  font-size: 12px;
  border-bottom: 1px solid transparent;
}

.footer-links a:hover {
  border-bottom-color: var(--text);
}

.panel {
  border-radius: 18px;
  border: 1px solid var(--border);
  background: radial-gradient(circle at top, #020617 0, #020617 50%, #020617 100%);
  padding: 16px;
  display: flex;
  flex-direction: column;
  gap: 16px;
  height: 100%;
  min-height: 0;
  overflow: hidden;
}

.panel-header {
  display: flex;
  justify-content: space-between;
  align-items: center;
  gap: 12px;
}

.panel-title {
  font-size: 14px;
  font-weight: 500;
}

.panel-desc {
  font-size: 12px;
  color: var(--text-soft);
}

.control-row {
  display: flex;
  flex-wrap: wrap;
  gap: 12px;
  align-items: center;
}

.control-label {
  font-size: 12px;
  color: var(--text-soft);
  display: flex;
  align-items: center;
  gap: 8px;
}

.control-label input {
  width: 90px;
  border-radius: 10px;
  border: 1px solid var(--border);
  background: rgba(15, 23, 42, 0.96);
  color: var(--text);
  padding: 6px 8px;
  font-size: 13px;
  outline: none;
}

.control-label input:focus {
  border-color: var(--accent);
  box-shadow: 0 0 0 1px rgba(59, 130, 246, 0.6);
}

.btn {
  cursor: pointer;
  border-radius: 10px;
  border: 1px solid transparent;
  padding: 7px 12px;
  font-size: 12px;
  display: inline-flex;
  align-items: center;
  gap: 6px;
  white-space: nowrap;
  background: rgba(15, 23, 42, 0.95);
  color: var(--text-soft);
  border-color: var(--border);
}

.btn:disabled {
  opacity: 0.4;
  cursor: not-allowed;
}

.btn-light {
  background: rgba(15, 23, 42, 0.6);
  color: var(--text);
  border: 1px solid var(--border);
}

.list-wrapper {
  flex: 1;
  border-radius: 16px;
  border: 1px solid rgba(31, 41, 55, 0.9);
  background: rgba(2, 6, 23, 0.6);
  padding: 10px;
  overflow-y: auto;
  display: flex;
  flex-direction: column;
  gap: 10px;
  min-height: 0;
}

.vector-list {
  display: flex;
  flex-direction: column;
  gap: 10px;
}

.vector-card {
  border-radius: 14px;
  border: 1px solid rgba(148, 163, 184, 0.2);
  padding: 12px;
  background: rgba(15, 23, 42, 0.9);
  display: flex;
  flex-direction: column;
  gap: 8px;
}

.card-header {
  display: flex;
  justify-content: space-between;
  gap: 12px;
  align-items: center;
}

.card-id {
  font-size: 13px;
  color: var(--text-soft);
  flex: 1;
  overflow: hidden;
  text-overflow: ellipsis;
  white-space: nowrap;
}

.card-snippet {
  font-size: 14px;
  color: var(--text);
  line-height: 1.5;
}

.card-meta {
  font-size: 12px;
  color: var(--text-soft);
}

.pagination {
  color: var(--text-soft);
  display: flex;
  align-items: center;
  justify-content: space-between;
  flex-wrap: wrap;
  gap: 8px;
}

.page-info {
  font-size: 0.9rem;
}

.empty-tip {
  height: 100%;
  display: flex;
  align-items: center;
  justify-content: center;
  color: var(--text-soft);
  font-size: 0.95rem;
}

.detail-overlay {
  position: fixed;
  inset: 0;
  background: rgba(0, 0, 0, 0.65);
  display: flex;
  align-items: center;
  justify-content: center;
  padding: 20px;
}

.detail-modal {
  width: min(720px, 100%);
  max-height: 90vh;
  background: radial-gradient(circle at top left, #111827, #020617);
  border: 1px solid var(--border);
  border-radius: 20px;
  padding: 24px;
  position: relative;
  display: flex;
  flex-direction: column;
  overflow: hidden;
}

.detail-close {
  position: absolute;
  top: 16px;
  right: 16px;
  background: transparent;
  border: none;
  color: var(--text-soft);
  font-size: 22px;
  cursor: pointer;
}

.detail-content {
  margin-top: 10px;
  overflow-y: auto;
  padding-right: 6px;
  display: flex;
  flex-direction: column;
  gap: 14px;
}

.detail-section {
  display: flex;
  flex-direction: column;
  gap: 4px;
}

.detail-label {
  font-size: 12px;
  color: var(--text-soft);
  letter-spacing: 0.04em;
}

.detail-value {
  font-size: 13px;
  color: var(--text);
}

.detail-text {
  white-space: pre-wrap;
  line-height: 1.5;
}

.detail-pre {
  background: rgba(15, 23, 42, 0.9);
  border: 1px solid rgba(148, 163, 184, 0.2);
  border-radius: 12px;
  padding: 12px;
  color: var(--text);
  font-size: 12px;
  overflow-x: auto;
}
</style>
