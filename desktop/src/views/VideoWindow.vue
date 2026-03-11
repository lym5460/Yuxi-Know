<template>
  <div class="video-window">
    <div v-if="!mediaUrl" class="video-placeholder">
      <MonitorPlay :size="48" />
      <p>等待视频播放指令...</p>
    </div>
    <template v-else>
      <div v-if="mediaName" class="media-info">{{ mediaName }}</div>
      <video
        v-if="mediaType === 'video'"
        ref="videoRef"
        class="media-element"
        :src="mediaUrl"
        controls
        autoplay
        @loadedmetadata="handleLoaded"
      />
      <audio
        v-else
        ref="videoRef"
        class="media-element audio"
        :src="mediaUrl"
        controls
        autoplay
        @loadedmetadata="handleLoaded"
      />
    </template>
  </div>
</template>

<script setup>
import { ref, onMounted, onUnmounted } from 'vue'
import { MonitorPlay } from 'lucide-vue-next'

const mediaUrl = ref('')
const mediaType = ref('video')
const mediaName = ref('')
const startTime = ref(0)
const videoRef = ref(null)

function handleMessage(event) {
  if (event.data?.type === 'media_command') {
    const p = event.data.payload
    mediaUrl.value = p.media_url || ''
    mediaType.value = p.media_type || 'video'
    mediaName.value = p.media_name || ''
    startTime.value = p.start_time || 0
  } else if (event.data?.type === 'media_stop') {
    mediaUrl.value = ''
  }
}

function handleLoaded() {
  if (videoRef.value && startTime.value > 0) {
    videoRef.value.currentTime = startTime.value
  }
}

onMounted(() => {
  window.addEventListener('message', handleMessage)
})

onUnmounted(() => {
  window.removeEventListener('message', handleMessage)
})
</script>

<style lang="less" scoped>
.video-window {
  width: 100%;
  height: 100vh;
  background: #000;
  display: flex;
  flex-direction: column;
  align-items: center;
  justify-content: center;
}

.video-placeholder {
  display: flex;
  flex-direction: column;
  align-items: center;
  gap: 12px;
  color: rgba(255, 255, 255, 0.4);

  p { margin: 0; font-size: 14px; }
}

.media-info {
  color: rgba(255, 255, 255, 0.7);
  font-size: 13px;
  padding: 8px 16px;
  width: 100%;
  text-align: center;
}

.media-element {
  max-width: 100%;
  max-height: calc(100vh - 40px);
  width: 100%;
  flex: 1;

  &.audio {
    max-height: 54px;
    flex: none;
  }
}
</style>
