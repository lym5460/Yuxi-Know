<template>
  <a-modal
    v-model:open="visible"
    :title="title"
    :footer="null"
    width="720px"
    :destroyOnClose="true"
    centered
    @cancel="handleClose"
  >
    <div class="media-player-container">
      <a-spin v-if="loading" tip="加载中..." />
      <div v-else-if="errorMsg" class="error-state">
        <a-result status="error" :title="errorMsg" />
      </div>
      <template v-else>
        <video
          v-if="mediaType === 'video'"
          ref="playerRef"
          :src="mediaUrl"
          controls
          autoplay
          class="media-element"
        />
        <audio
          v-else
          ref="playerRef"
          :src="mediaUrl"
          controls
          autoplay
          class="audio-element"
        />
        <div class="media-info" v-if="details">
          <span v-if="details.resolution_label">{{ details.resolution_label }}</span>
          <span v-if="details.duration">{{ formatDuration(details.duration) }}</span>
          <span v-if="details.size">{{ formatFileSize(details.size) }}</span>
        </div>
      </template>
    </div>
  </a-modal>
</template>

<script setup>
import { ref, watch } from 'vue'
import { useUserStore } from '@/stores/user'
import { mediaApi } from '@/apis/knowledge_api'
import { formatDuration, formatFileSize } from '@/utils/file_utils'

const props = defineProps({
  open: Boolean,
  dbId: String,
  videoNo: String,
  fileId: String,
  mediaType: { type: String, default: 'video' },
  title: { type: String, default: '媒体播放' }
})

const emit = defineEmits(['update:open'])

const userStore = useUserStore()
const visible = ref(false)
const loading = ref(false)
const errorMsg = ref('')
const mediaUrl = ref('')
const details = ref(null)
const playerRef = ref(null)

watch(() => props.open, (val) => { visible.value = val })
watch(visible, (val) => { emit('update:open', val) })

watch(() => [props.open, props.videoNo], async ([open, videoNo]) => {
  if (!open || !videoNo || !props.dbId) return
  loading.value = true
  errorMsg.value = ''
  mediaUrl.value = ''
  details.value = null

  try {
    const data = await mediaApi.getMediaDetails(props.dbId, videoNo)
    details.value = data

    if (data.video_url) {
      mediaUrl.value = data.video_url
    } else if (props.fileId) {
      // Memeries video_url 为空，使用流式播放端点（支持 Range、浏览器缓存）
      mediaUrl.value = `/api/knowledge/databases/${props.dbId}/documents/${props.fileId}/stream?token=${userStore.token}`
    } else {
      errorMsg.value = '无法获取播放地址'
    }
  } catch (e) {
    errorMsg.value = e.message || '加载失败'
  } finally {
    loading.value = false
  }
})

const handleClose = () => {
  if (playerRef.value) {
    playerRef.value.pause()
    playerRef.value.src = ''
  }
}
</script>

<style lang="less" scoped>
.media-player-container {
  display: flex;
  flex-direction: column;
  align-items: center;
  min-height: 200px;
  justify-content: center;
}

.media-element {
  width: 100%;
  max-height: 420px;
  border-radius: 8px;
  background: #000;
}

.audio-element {
  width: 100%;
  margin: 40px 0;
}

.error-state {
  width: 100%;
}

.media-info {
  display: flex;
  gap: 12px;
  margin-top: 8px;
  font-size: 12px;
  color: var(--gray-500);
}
</style>
