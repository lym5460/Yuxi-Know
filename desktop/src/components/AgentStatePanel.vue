<template>
  <div class="agent-state-panel">
    <div class="panel-header">
      <div class="panel-tabs">
        <button
          class="tab-btn"
          :class="{ active: activeTab === 'files' }"
          @click="activeTab = 'files'"
        >
          <FolderOpen :size="14" />
          <span>文件 ({{ fileCount }})</span>
        </button>
        <button
          class="tab-btn"
          :class="{ active: activeTab === 'todos' }"
          @click="activeTab = 'todos'"
        >
          <ListTodo :size="14" />
          <span>任务 ({{ completedCount }}/{{ todos.length }})</span>
        </button>
      </div>
      <div class="panel-actions">
        <button class="icon-btn" @click="$emit('refresh')" title="刷新">
          <RefreshCw :size="14" />
        </button>
        <button class="icon-btn" @click="$emit('close')" title="关闭">
          <X :size="14" />
        </button>
      </div>
    </div>

    <div class="panel-body">
      <!-- 文件列表 -->
      <div v-if="activeTab === 'files'" class="files-list">
        <div v-if="!fileCount" class="empty-hint">暂无文件</div>
        <div
          v-for="file in normalizedFiles"
          :key="file.path"
          class="file-item"
          @click="openFile(file)"
        >
          <FileText :size="14" class="file-icon" />
          <span class="file-name">{{ getFileName(file.path) }}</span>
          <button class="download-btn" @click.stop="downloadFile(file)" title="下载">
            <Download :size="13" />
          </button>
        </div>
      </div>

      <!-- 任务列表 -->
      <div v-if="activeTab === 'todos'" class="todos-list">
        <div v-if="!todos.length" class="empty-hint">暂无任务</div>
        <div
          v-for="(todo, idx) in todos"
          :key="idx"
          class="todo-item"
          :class="todo.status"
        >
          <CircleCheck v-if="todo.status === 'completed'" :size="14" class="todo-icon completed" />
          <LoaderCircle v-else-if="todo.status === 'in_progress'" :size="14" class="todo-icon in-progress spin" />
          <Circle v-else-if="todo.status === 'pending'" :size="14" class="todo-icon pending" />
          <CircleX v-else :size="14" class="todo-icon cancelled" />
          <span class="todo-text" :class="{ done: todo.status === 'completed' }">
            {{ todo.status === 'in_progress' ? (todo.activeForm || todo.content) : todo.content }}
          </span>
        </div>
      </div>
    </div>

    <!-- 文件预览弹窗 -->
    <a-modal
      v-model:open="fileModalVisible"
      :title="currentFilePath"
      width="70%"
      :footer="null"
    >
      <div class="file-preview">
        <MarkdownRenderer v-if="isCurrentFileMarkdown" :content="currentFileContent" />
        <pre v-else class="file-raw">{{ currentFileContent }}</pre>
      </div>
    </a-modal>
  </div>
</template>

<script setup>
import { ref, computed } from 'vue'
import {
  FolderOpen, ListTodo, RefreshCw, X, FileText, Download,
  CircleCheck, LoaderCircle, Circle, CircleX
} from 'lucide-vue-next'
import { save } from '@tauri-apps/plugin-dialog'
import { writeTextFile } from '@tauri-apps/plugin-fs'
import MarkdownRenderer from './MarkdownRenderer.vue'

const props = defineProps({
  agentState: { type: Object, default: null }
})

defineEmits(['close', 'refresh'])

const activeTab = ref('files')
const fileModalVisible = ref(false)
const currentFilePath = ref('')
const currentFileContent = ref('')

const todos = computed(() => props.agentState?.todos || [])

const completedCount = computed(() =>
  todos.value.filter(t => t.status === 'completed').length
)

// 兼容字典和数组两种格式
const normalizedFiles = computed(() => {
  const raw = props.agentState?.files
  if (!raw) return []
  const result = []
  if (typeof raw === 'object' && !Array.isArray(raw)) {
    Object.entries(raw).forEach(([path, data]) => {
      result.push({ path, ...data })
    })
  } else if (Array.isArray(raw)) {
    raw.forEach(item => {
      if (typeof item === 'object' && item !== null) {
        Object.entries(item).forEach(([path, data]) => {
          result.push({ path, ...data })
        })
      }
    })
  }
  return result
})

const fileCount = computed(() => normalizedFiles.value.length)

const isCurrentFileMarkdown = computed(() =>
  /\.(md|markdown)$/i.test(currentFilePath.value)
)

function getFileName(path) {
  return path?.split('/').pop() || path
}

function formatContent(content) {
  if (Array.isArray(content)) return content.join('\n')
  if (typeof content === 'string') return content
  return JSON.stringify(content, null, 2)
}

function openFile(file) {
  currentFilePath.value = file.path
  currentFileContent.value = formatContent(file.content)
  fileModalVisible.value = true
}

async function downloadFile(file) {
  try {
    const fileName = getFileName(file.path)
    const filePath = await save({
      defaultPath: fileName,
      filters: [{ name: '所有文件', extensions: ['*'] }]
    })
    if (!filePath) return
    const content = formatContent(file.content)
    await writeTextFile(filePath, content)
  } catch (e) {
    console.error('下载文件失败:', e)
  }
}
</script>

<style lang="less" scoped>
.agent-state-panel {
  display: flex;
  flex-direction: column;
  height: 100%;
  background: var(--gray-50);
  border-left: 1px solid var(--glass-border);
}

.panel-header {
  display: flex;
  align-items: center;
  justify-content: space-between;
  padding: 8px 10px;
  border-bottom: 1px solid var(--glass-border);
  flex-shrink: 0;
}

.panel-tabs {
  display: flex;
  gap: 2px;
}

.tab-btn {
  display: flex;
  align-items: center;
  gap: 4px;
  padding: 4px 10px;
  border: none;
  border-radius: var(--radius-sm);
  background: transparent;
  color: var(--gray-500);
  font-size: 12px;
  cursor: pointer;
  transition: all 0.2s;

  &:hover {
    color: var(--gray-700);
    background: rgba(0, 212, 255, 0.06);
  }

  &.active {
    color: var(--color-primary-500);
    background: rgba(0, 212, 255, 0.1);
  }
}

.panel-actions {
  display: flex;
  gap: 2px;

  .icon-btn {
    display: flex;
    align-items: center;
    justify-content: center;
    width: 24px;
    height: 24px;
    border: none;
    border-radius: var(--radius-sm);
    background: transparent;
    color: var(--gray-400);
    cursor: pointer;
    transition: all 0.2s;

    &:hover {
      color: var(--color-primary-500);
      background: rgba(0, 212, 255, 0.08);
    }
  }
}

.panel-body {
  flex: 1;
  overflow-y: auto;
  padding: 8px;
}

.empty-hint {
  text-align: center;
  padding: 24px;
  color: var(--gray-400);
  font-size: 13px;
}

// 文件列表
.file-item {
  display: flex;
  align-items: center;
  gap: 8px;
  padding: 6px 10px;
  border-radius: var(--radius-sm);
  cursor: pointer;
  font-size: 13px;
  color: var(--gray-700);
  transition: all 0.2s;

  &:hover {
    background: rgba(0, 212, 255, 0.06);
  }

  .file-icon {
    flex-shrink: 0;
    color: var(--color-primary-500);
  }

  .file-name {
    flex: 1;
    overflow: hidden;
    text-overflow: ellipsis;
    white-space: nowrap;
  }

  .download-btn {
    display: flex;
    align-items: center;
    justify-content: center;
    width: 22px;
    height: 22px;
    border: none;
    border-radius: var(--radius-sm);
    background: transparent;
    color: var(--gray-400);
    cursor: pointer;
    opacity: 0;
    transition: all 0.2s;

    &:hover {
      color: var(--color-primary-500);
      background: rgba(0, 212, 255, 0.1);
    }
  }

  &:hover .download-btn {
    opacity: 1;
  }
}

// 任务列表
.todo-item {
  display: flex;
  align-items: flex-start;
  gap: 8px;
  padding: 6px 10px;
  font-size: 13px;

  .todo-icon {
    flex-shrink: 0;
    margin-top: 2px;

    &.completed { color: #4ade80; }
    &.in-progress { color: var(--color-primary-500); }
    &.pending { color: var(--gray-400); }
    &.cancelled { color: var(--gray-400); }
  }

  .todo-text {
    flex: 1;
    color: var(--gray-700);
    line-height: 1.5;

    &.done {
      color: var(--gray-500);
      text-decoration: line-through;
    }
  }
}

// 文件预览
.file-preview {
  max-height: 60vh;
  overflow-y: auto;
}

.file-raw {
  margin: 0;
  padding: 12px;
  font-size: 13px;
  line-height: 1.5;
  white-space: pre-wrap;
  word-break: break-word;
  background: var(--gray-100);
  border-radius: var(--radius-sm);
}

.spin {
  animation: spin 1s linear infinite;
}

@keyframes spin {
  from { transform: rotate(0deg); }
  to { transform: rotate(360deg); }
}
</style>
