<template>
  <BaseToolCall :tool-call="toolCall" :hide-params="true">
    <template #header>
      <div class="sep-header">
        <span class="note">{{ toolName }} 搜索</span>
        <span class="separator" v-if="queryText">|</span>
        <span class="description">{{ queryText }}</span>
      </div>
    </template>
    <template #result="{ resultContent }">
      <div class="media-kb-result">
        <div v-if="parsedResults(resultContent).length > 0" class="result-summary">
          找到 {{ parsedResults(resultContent).length }} 个相关媒体片段
        </div>

        <div v-if="parsedResults(resultContent).length > 0" class="media-results">
          <MediaResultCard
            v-for="(item, index) in parsedResults(resultContent)"
            :key="item.media_id + '-' + index"
            :result="item"
            @play="openPlayer"
          />
        </div>

        <div v-else class="no-results">
          <p>未找到相关媒体内容</p>
        </div>

        <!-- 播放器模态框 -->
        <a-modal
          v-model:open="playerVisible"
          :title="currentMedia?.media_name || '媒体播放'"
          :width="currentMedia?.media_type === 'video' ? '720px' : '480px'"
          :footer="null"
          :destroy-on-close="true"
          class="media-player-modal"
        >
          <MediaPlayer
            v-if="currentMedia"
            :media-url="currentMedia.media_url"
            :media-type="currentMedia.media_type"
            :start-time="currentMedia.start_time"
            :end-time="currentMedia.end_time"
            :media-name="currentMedia.media_name"
          />
        </a-modal>
      </div>
    </template>
  </BaseToolCall>
</template>

<script setup>
import { ref, computed } from 'vue'
import { useUserStore } from '@/stores/user'
import BaseToolCall from '../BaseToolCall.vue'
import MediaResultCard from '../MediaResultCard.vue'
import MediaPlayer from '@/components/MediaPlayer.vue'

const userStore = useUserStore()

const props = defineProps({
  toolCall: {
    type: Object,
    required: true
  }
})

const playerVisible = ref(false)
const currentMedia = ref(null)

const args = computed(() => {
  const raw = props.toolCall.args || props.toolCall.function?.arguments
  if (!raw) return {}
  if (typeof raw === 'object') return raw
  try {
    return JSON.parse(raw)
  } catch {
    return {}
  }
})

const toolName = computed(() => props.toolCall.name || props.toolCall.function?.name || '媒体知识库')

const queryText = computed(() => args.value.query_text || '')

function parsedResults(content) {
  if (!content) return []
  if (typeof content === 'string') {
    try {
      const data = JSON.parse(content)
      return Array.isArray(data) ? data : []
    } catch {
      return []
    }
  }
  return Array.isArray(content) ? content : []
}

function openPlayer(result) {
  // 优先通过本地代理播放，避免外部 URL 403
  let url = result.media_url
  if (result.file_id && result.db_id) {
    url = `/api/knowledge/databases/${result.db_id}/documents/${result.file_id}/stream?token=${userStore.token}`
  }
  currentMedia.value = {
    media_url: url,
    media_type: result.media_type || 'video',
    start_time: Number(result.start_time) || 0,
    end_time: result.end_time != null ? Number(result.end_time) : undefined,
    media_name: result.media_name || ''
  }
  playerVisible.value = true
}
</script>

<style lang="less" scoped>
.media-kb-result {
  background: var(--gray-0);
  border-radius: 8px;

  .result-summary {
    padding: 12px 16px;
    background: var(--gray-25);
    font-size: 12px;
    color: var(--gray-700);
    border-bottom: 1px solid var(--gray-100);
  }

  .media-results {
    padding: 8px;
    display: flex;
    flex-direction: column;
    gap: 6px;
  }

  .no-results {
    text-align: center;
    color: var(--gray-700);
    padding: 20px;
    font-size: 12px;
  }
}
</style>
