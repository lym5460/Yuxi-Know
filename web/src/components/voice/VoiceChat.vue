<template>
  <div class="voice-chat">
    <div class="status-bar">
      <span class="status-indicator" :class="status"></span>
      <span class="status-text">{{ statusText }}</span>
    </div>
    
    <div class="transcription" v-if="transcription">
      {{ transcription }}
    </div>
    
    <VoiceControls
      :is-recording="isRecording"
      :is-playing="isPlaying"
      @start="startVoice"
      @stop="stopVoice"
      @interrupt="handleInterrupt"
    />
  </div>
</template>

<script setup>
import { ref, computed, onMounted, onUnmounted } from 'vue'
import { createVoiceWebSocket, sendAudio, sendControl } from '@/apis/voice_api'
import { useAudioCapture } from '@/composables/useAudioCapture'
import { useAudioPlayer } from '@/composables/useAudioPlayer'
import VoiceControls from './VoiceControls.vue'

const props = defineProps({
  agentId: { type: String, required: true }
})

const status = ref('idle')
const transcription = ref('')
const isRecording = ref(false)

let ws = null

const { isCapturing, startCapture, stopCapture } = useAudioCapture({
  onAudioChunk: (chunk) => {
    if (ws) sendAudio(ws, chunk)
  }
})

const { isPlaying, playAudioChunk, stop: stopAudio } = useAudioPlayer()

const statusText = computed(() => {
  const texts = {
    idle: '准备就绪',
    listening: '正在听...',
    processing: '处理中...',
    speaking: '正在说话...'
  }
  return texts[status.value] || ''
})

function handleMessage(msg) {
  switch (msg.type) {
    case 'status':
      status.value = msg.status
      break
    case 'transcription':
      transcription.value = msg.text
      break
    case 'audio':
      if (msg.audio_data) playAudioChunk(msg.audio_data)
      break
    case 'error':
      console.error('Voice error:', msg.error)
      break
  }
}

function startVoice() {
  if (!ws) {
    ws = createVoiceWebSocket(props.agentId, {
      onMessage: handleMessage,
      onClose: () => { ws = null }
    })
  }
  sendControl(ws, 'start')
  startCapture()
  isRecording.value = true
}

function stopVoice() {
  sendControl(ws, 'stop')
  stopCapture()
  isRecording.value = false
}

function handleInterrupt() {
  sendControl(ws, 'interrupt')
  stopAudio()
}

onUnmounted(() => {
  if (ws) ws.close()
  stopCapture()
})
</script>

<style lang="less" scoped>
.voice-chat {
  display: flex;
  flex-direction: column;
  align-items: center;
  gap: 16px;
  padding: 24px;
}

.status-bar {
  display: flex;
  align-items: center;
  gap: 8px;
}

.status-indicator {
  width: 12px;
  height: 12px;
  border-radius: 50%;
  background: var(--color-text-quaternary);
  
  &.listening { background: var(--color-success); }
  &.processing { background: var(--color-warning); }
  &.speaking { background: var(--color-primary); }
}

.transcription {
  padding: 12px 16px;
  background: var(--color-bg-container);
  border-radius: 8px;
  min-height: 48px;
  width: 100%;
  max-width: 400px;
}
</style>
