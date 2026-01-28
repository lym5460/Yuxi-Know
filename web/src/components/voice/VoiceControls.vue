<template>
  <div class="voice-controls">
    <a-button
      v-if="!isRecording"
      type="primary"
      shape="circle"
      size="large"
      @click="$emit('start')"
    >
      <template #icon><AudioOutlined /></template>
    </a-button>
    
    <a-button
      v-else
      type="primary"
      danger
      shape="circle"
      size="large"
      @click="$emit('stop')"
    >
      <template #icon><PauseOutlined /></template>
    </a-button>
    
    <a-button
      v-if="isPlaying"
      shape="circle"
      @click="$emit('interrupt')"
    >
      <template #icon><StopOutlined /></template>
    </a-button>
  </div>
</template>

<script setup>
import { AudioOutlined, PauseOutlined, StopOutlined } from '@ant-design/icons-vue'

defineProps({
  isRecording: { type: Boolean, default: false },
  isPlaying: { type: Boolean, default: false }
})

defineEmits(['start', 'stop', 'interrupt'])
</script>

<style lang="less" scoped>
.voice-controls {
  display: flex;
  gap: 12px;
  align-items: center;
}
</style>
