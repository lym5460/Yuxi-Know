<template>
  <div class="media-player" :class="{ 'fullscreen-mode': fullscreenMode }">
    <!-- 片段描述信息 -->
    <div v-if="description" class="media-description">
      {{ description }}
    </div>

    <!-- 媒体信息栏 -->
    <div v-if="mediaName || hasTimeRange" class="media-info">
      <span v-if="mediaName" class="media-name">{{ mediaName }}</span>
      <span v-if="hasTimeRange" class="media-time-range">
        {{ formatTime(startTime) }} - {{ formatTime(endTime) }}
      </span>
    </div>

    <!-- 错误状态 -->
    <div v-if="hasError" class="media-error">
      <CircleAlert :size="16" />
      <span>{{ errorMessage }}</span>
    </div>

    <!-- 视频播放器 -->
    <video
      v-else-if="mediaType === 'video'"
      ref="mediaRef"
      class="media-element video-element"
      :src="mediaUrl"
      controls
      preload="metadata"
      @loadedmetadata="handleLoadedMetadata"
      @error="handleMediaError"
    />

    <!-- 音频播放器 -->
    <audio
      v-else
      ref="mediaRef"
      class="media-element audio-element"
      :src="mediaUrl"
      controls
      preload="metadata"
      @loadedmetadata="handleLoadedMetadata"
      @error="handleMediaError"
    />
  </div>
</template>

<script setup>
import { ref, watch, computed } from 'vue'
import { CircleAlert } from 'lucide-vue-next'

const props = defineProps({
  mediaUrl: {
    type: String,
    default: ''
  },
  mediaType: {
    type: String,
    default: 'video',
    validator: (val) => ['video', 'audio'].includes(val)
  },
  startTime: {
    type: Number,
    default: undefined
  },
  endTime: {
    type: Number,
    default: undefined
  },
  description: {
    type: String,
    default: ''
  },
  mediaName: {
    type: String,
    default: ''
  },
  fullscreenMode: {
    type: Boolean,
    default: false
  }
})

const mediaRef = ref(null)
const hasError = ref(false)
const errorMessage = ref('媒体加载失败，请检查链接是否有效')

const hasTimeRange = computed(() => {
  return props.startTime !== undefined && props.endTime !== undefined
})

/**
 * 格式化时间（秒 → mm:ss 或 hh:mm:ss）
 */
function formatTime(seconds) {
  if (seconds === undefined || seconds === null) return '--:--'
  const s = Math.floor(seconds)
  const h = Math.floor(s / 3600)
  const m = Math.floor((s % 3600) / 60)
  const sec = s % 60
  const pad = (n) => String(n).padStart(2, '0')
  return h > 0 ? `${pad(h)}:${pad(m)}:${pad(sec)}` : `${pad(m)}:${pad(sec)}`
}

/**
 * 跳转到指定时间并播放
 */
function seekAndPlay(time) {
  if (mediaRef.value && time !== undefined) {
    hasError.value = false
    mediaRef.value.currentTime = time
    mediaRef.value.play().catch((err) => {
      console.warn('播放失败:', err.message)
    })
  }
}

/**
 * 处理媒体加载错误
 */
function handleMediaError() {
  hasError.value = true
}

/**
 * 媒体元数据加载完成后，自动跳转到 startTime 并播放
 * 解决 destroy-on-close 模态框中 watch 无法捕获初始值的问题
 */
function handleLoadedMetadata() {
  if (props.startTime !== undefined) {
    seekAndPlay(props.startTime)
  }
}

// 监听 startTime 变化，自动跳转播放
watch(
  () => props.startTime,
  (newTime) => {
    if (newTime !== undefined) {
      seekAndPlay(newTime)
    }
  }
)

// 监听 mediaUrl 变化，重置错误状态
watch(
  () => props.mediaUrl,
  () => {
    hasError.value = false
  }
)

// 暴露 seekAndPlay 方法供父组件调用
defineExpose({ seekAndPlay })
</script>

<style lang="less" scoped>
.media-player {
  display: flex;
  flex-direction: column;
  gap: 8px;
  width: 100%;
}

.media-description {
  font-size: 13px;
  color: var(--gray-700);
  line-height: 1.5;
  padding: 8px 12px;
  background: var(--gray-50);
  border-radius: 6px;
}

.media-info {
  display: flex;
  align-items: center;
  gap: 8px;
  font-size: 12px;
  color: var(--gray-600);

  .media-name {
    overflow: hidden;
    text-overflow: ellipsis;
    white-space: nowrap;
    max-width: 240px;
  }

  .media-time-range {
    flex-shrink: 0;
    color: var(--color-primary-500);
    font-variant-numeric: tabular-nums;
  }
}

.media-error {
  display: flex;
  align-items: center;
  gap: 6px;
  padding: 12px 16px;
  background: var(--color-error-50);
  color: var(--color-error-500);
  border-radius: 6px;
  font-size: 13px;
}

.media-element {
  border-radius: 6px;
  width: 100%;
  outline: none;
}

.video-element {
  max-height: 80vh;
  background: var(--gray-1000);
}

.media-player.fullscreen-mode .video-element {
  max-height: 75vh;
}

.audio-element {
  height: 40px;
}
</style>
