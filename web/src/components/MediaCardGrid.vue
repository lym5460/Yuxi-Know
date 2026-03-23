<template>
  <div class="media-card-grid-container">
    <MediaPlayerModal
      v-model:open="playerVisible"
      :db-id="store.databaseId"
      :video-no="currentVideoNo"
      :file-id="currentFileId"
      :media-type="currentMediaType"
      :title="currentTitle"
    />

    <div class="panel-header">
      <div class="upload-btn-group">
        <a-button type="primary" size="small" class="upload-btn" @click="showAddFilesModal">
          <FileUp size="14" style="margin-right: 4px" />
          上传
        </a-button>
      </div>
      <div class="panel-actions">
        <a-input
          v-model:value="searchText"
          placeholder="搜索"
          size="small"
          class="action-searcher"
          allow-clear
        >
          <template #prefix>
            <Search size="14" style="color: var(--gray-400)" />
          </template>
        </a-input>
        <a-button
          type="text"
          @click="handleRefresh"
          :loading="refreshing"
          title="刷新"
          class="panel-action-btn"
        >
          <template #icon><RotateCw size="16" /></template>
        </a-button>
      </div>
    </div>

    <div class="card-grid" v-if="filteredFiles.length > 0">
      <div
        v-for="file in filteredFiles"
        :key="file.file_id"
        class="media-card"
        :class="{ playable: isPlayable(file) }"
        @click="openPlayer(file)"
      >
        <div :class="['card-icon', file.media_type === 'video' ? 'icon-bg-video' : 'icon-bg-audio']">
          <Video v-if="file.media_type === 'video'" :size="22" />
          <Music v-else :size="22" />
        </div>
        <div class="card-body">
          <div class="card-name" v-if="renamingFileId !== file.file_id" :title="file.filename">
            {{ file.filename }}
          </div>
          <a-input
            v-else
            v-model:value="renameValue"
            size="small"
            class="rename-input"
            @pressEnter="confirmRename(file)"
            @blur="confirmRename(file)"
            @keydown.esc="cancelRename"
            @click.stop
            autofocus
          />
          <div class="card-meta">
            <span v-if="file.duration != null" class="meta-item">
              {{ formatDuration(file.duration) }}
            </span>
            <span v-if="file.size" class="meta-item">
              {{ formatFileSize(file.size) }}
            </span>
            <span :class="['status-tag', statusClass(file.status)]">
              {{ getStatusText(file.status) }}
            </span>
          </div>
        </div>
        <div class="card-actions" @click.stop>
          <a-tooltip v-if="isPlayable(file)" title="播放">
            <a-button type="text" size="small" class="action-btn play-btn" @click="openPlayer(file)">
              <Play :size="14" />
            </a-button>
          </a-tooltip>
          <a-tooltip title="重命名">
            <a-button type="text" size="small" class="action-btn" @click="startRename(file)">
              <Pencil :size="14" />
            </a-button>
          </a-tooltip>
          <a-popconfirm
            title="确定删除此文件？"
            ok-text="删除"
            cancel-text="取消"
            ok-type="danger"
            @confirm="handleDelete(file)"
            :disabled="isProcessing(file.status)"
          >
            <a-tooltip title="删除">
              <a-button
                type="text"
                size="small"
                class="action-btn delete-btn"
                :disabled="isProcessing(file.status)"
              >
                <Trash2 :size="14" />
              </a-button>
            </a-tooltip>
          </a-popconfirm>
        </div>
      </div>
    </div>

    <div v-else class="empty-state">
      <a-empty description="暂无媒体文件" />
    </div>
  </div>
</template>

<script setup>
import { ref, computed } from 'vue'
import { useDatabaseStore } from '@/stores/database'
import { documentApi } from '@/apis/knowledge_api'
import { Video, Music, FileUp, Search, RotateCw, Trash2, Play, Pencil } from 'lucide-vue-next'
import { formatDuration, formatFileSize } from '@/utils/file_utils'
import { message } from 'ant-design-vue'
import MediaPlayerModal from '@/components/MediaPlayerModal.vue'

const emit = defineEmits(['showAddFilesModal'])
const store = useDatabaseStore()

const searchText = ref('')
const playerVisible = ref(false)
const currentVideoNo = ref('')
const currentMediaType = ref('video')
const currentTitle = ref('')
const currentFileId = ref('')

const refreshing = computed(() => store.state.refrashing)

// 改名
const renamingFileId = ref('')
const renameValue = ref('')

const startRename = (file) => {
  renamingFileId.value = file.file_id
  renameValue.value = file.filename || ''
}

const confirmRename = async (file) => {
  const newName = renameValue.value.trim()
  if (!newName || newName === file.filename) {
    renamingFileId.value = ''
    return
  }
  try {
    await documentApi.renameDocument(store.databaseId, file.file_id, newName)
    message.success('重命名成功')
    store.getDatabaseInfo(undefined, true)
  } catch (e) {
    message.error(e.message || '重命名失败')
  } finally {
    renamingFileId.value = ''
  }
}

const cancelRename = () => {
  renamingFileId.value = ''
}

const files = computed(() => {
  const all = Object.values(store.database.files || {})
  return all.filter((f) => !f.is_folder)
})

const filteredFiles = computed(() => {
  const q = searchText.value.trim().toLowerCase()
  if (!q) return files.value
  return files.value.filter((f) => f.filename?.toLowerCase().includes(q))
})

const getStatusText = (status) => {
  const map = {
    uploaded: '已上传',
    indexing: '处理中',
    indexed: '已就绪',
    error_indexing: '失败',
    done: '已就绪',
    failed: '失败',
    processing: '处理中'
  }
  return map[status] || status
}

const statusClass = (status) => {
  if (status === 'done' || status === 'indexed') return 'success'
  if (status === 'failed' || status === 'error_indexing') return 'error'
  if (status === 'indexing' || status === 'processing') return 'processing'
  return 'waiting'
}

const isPlayable = (file) => {
  return file.memeries_video_no && (file.status === 'done' || file.status === 'indexed')
}

const isProcessing = (status) => {
  return ['processing', 'parsing', 'indexing'].includes(status)
}

const openPlayer = (file) => {
  if (!isPlayable(file)) return
  currentVideoNo.value = file.memeries_video_no
  currentMediaType.value = file.media_type || 'video'
  currentTitle.value = file.filename || '媒体播放'
  currentFileId.value = file.file_id || ''
  playerVisible.value = true
}

const showAddFilesModal = () => {
  emit('showAddFilesModal', { isFolder: false })
}

const handleRefresh = () => {
  store.getDatabaseInfo(undefined, true)
}

const handleDelete = (file) => {
  store.handleDeleteFile(file.file_id)
}
</script>

<style lang="less" scoped>
.media-card-grid-container {
  display: flex;
  flex-direction: column;
  height: 100%;
  overflow: hidden;
}

.panel-header {
  display: flex;
  justify-content: space-between;
  align-items: center;
  padding: 8px 4px;
  flex-shrink: 0;

  .upload-btn-group {
    display: flex;
    gap: 4px;
  }

  .upload-btn {
    display: flex;
    align-items: center;
    border-radius: 6px;
    font-size: 13px;
  }

  .panel-actions {
    display: flex;
    align-items: center;
    gap: 2px;
  }

  .action-searcher {
    width: 160px;
    border-radius: 6px;
  }

  .panel-action-btn {
    color: var(--gray-600);
    border-radius: 6px;
    width: 28px;
    height: 28px;
    display: flex;
    align-items: center;
    justify-content: center;
  }
}

.card-grid {
  display: grid;
  grid-template-columns: repeat(auto-fill, minmax(260px, 1fr));
  grid-auto-rows: min-content;
  align-content: start;
  gap: 8px;
  padding: 4px;
  overflow-y: auto;
  flex: 1;
}

.media-card {
  display: flex;
  align-items: center;
  gap: 10px;
  padding: 10px 12px;
  border-radius: 10px;
  border: 1px solid var(--gray-200);
  background: var(--gray-0);
  cursor: default;
  transition: border-color 0.2s, background-color 0.2s;
  position: relative;

  &.playable {
    cursor: pointer;

    &:hover {
      border-color: var(--main-400);
      background: var(--main-10);
    }
  }

  &:hover .card-actions {
    opacity: 1;
  }
}

.card-icon {
  flex-shrink: 0;
  width: 38px;
  height: 38px;
  border-radius: 8px;
  display: flex;
  align-items: center;
  justify-content: center;

  &.icon-bg-video {
    background: #fff0f6;
    color: #eb2f96;
  }

  &.icon-bg-audio {
    background: #e6fffb;
    color: #13c2c2;
  }
}

.card-body {
  flex: 1;
  min-width: 0;
}

.card-name {
  font-size: 13px;
  color: var(--gray-900);
  white-space: nowrap;
  overflow: hidden;
  text-overflow: ellipsis;
  line-height: 1.4;
}

.rename-input {
  font-size: 13px;
}

.card-meta {
  display: flex;
  align-items: center;
  gap: 6px;
  margin-top: 3px;
  font-size: 12px;
  color: var(--gray-500);
}

.status-tag {
  font-size: 11px;
  padding: 0 5px;
  border-radius: 3px;
  line-height: 18px;
  white-space: nowrap;

  &.success {
    color: var(--color-success-700);
    background: var(--color-success-50);
  }

  &.error {
    color: var(--color-error-700);
    background: var(--color-error-50);
  }

  &.processing {
    color: var(--color-info-700);
    background: var(--color-info-50);
    animation: pulse 1.5s infinite;
  }

  &.waiting {
    color: var(--color-warning-700);
    background: var(--color-warning-50);
  }
}

@keyframes pulse {
  0%, 100% { opacity: 1; }
  50% { opacity: 0.5; }
}

.card-actions {
  opacity: 0;
  transition: opacity 0.15s;
  flex-shrink: 0;
  display: flex;
  gap: 2px;

  .action-btn {
    width: 28px;
    height: 28px;
    display: flex;
    align-items: center;
    justify-content: center;
    border-radius: 6px;
    color: var(--gray-500);

    &:hover {
      color: var(--gray-700);
      background: var(--gray-100);
    }

    &.play-btn:hover {
      color: var(--main-700);
      background: var(--main-50);
    }

    &.delete-btn:hover {
      color: var(--color-error-500);
      background: var(--color-error-50);
    }

    &:disabled {
      color: var(--gray-300);
      cursor: not-allowed;

      &:hover {
        background: transparent;
        color: var(--gray-300);
      }
    }
  }
}

.empty-state {
  flex: 1;
  display: flex;
  align-items: center;
  justify-content: center;
}
</style>
