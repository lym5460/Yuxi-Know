<template>
  <div class="media-result-card" @click="handlePlay">
    <div class="media-icon">
      <Video v-if="result.media_type === 'video'" :size="18" />
      <Music v-else :size="18" />
    </div>
    <div class="media-info">
      <div class="media-name" :title="result.media_name">{{ result.media_name }}</div>
      <div class="media-time">{{ formatTime(result.start_time) }} - {{ formatTime(result.end_time) }}</div>
    </div>
    <div class="media-score">{{ formatScore(result.score) }}</div>
  </div>
</template>

<script setup>
import { Video, Music } from 'lucide-vue-next'

const props = defineProps({
  result: {
    type: Object,
    required: true,
    // shape: { media_id, media_name, media_type, start_time, end_time, score, media_url }
  }
})

const emit = defineEmits(['play'])

/**
 * 将秒数格式化为 mm:ss
 */
function formatTime(seconds) {
  const num = Number(seconds) || 0
  const mins = Math.floor(num / 60)
  const secs = Math.floor(num % 60)
  return `${String(mins).padStart(2, '0')}:${String(secs).padStart(2, '0')}`
}

/**
 * 将 0~1 的分数格式化为百分比
 */
function formatScore(score) {
  const num = Number(score) || 0
  return `${(num * 100).toFixed(0)}%`
}

function handlePlay() {
  emit('play', props.result)
}
</script>

<style lang="less" scoped>
.media-result-card {
  display: flex;
  align-items: center;
  gap: 10px;
  padding: 10px 14px;
  border: 1px solid var(--gray-150);
  border-radius: 8px;
  background: var(--gray-0);
  cursor: pointer;
  transition: background 0.2s ease;

  &:hover {
    background: var(--gray-25);
  }

  .media-icon {
    display: flex;
    align-items: center;
    justify-content: center;
    width: 34px;
    height: 34px;
    border-radius: 8px;
    background: var(--color-primary-50);
    color: var(--main-700);
    flex-shrink: 0;
  }

  .media-info {
    flex: 1;
    min-width: 0;

    .media-name {
      font-size: 13px;
      font-weight: 500;
      color: var(--gray-800);
      white-space: nowrap;
      overflow: hidden;
      text-overflow: ellipsis;
    }

    .media-time {
      font-size: 12px;
      color: var(--gray-600);
      margin-top: 2px;
    }
  }

  .media-score {
    font-size: 12px;
    color: var(--gray-600);
    background: var(--gray-50);
    padding: 2px 8px;
    border-radius: 10px;
    white-space: nowrap;
    flex-shrink: 0;
  }
}
</style>
