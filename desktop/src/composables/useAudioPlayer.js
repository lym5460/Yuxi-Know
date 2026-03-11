/**
 * 音频播放 Composable
 *
 * 使用 Web Audio API 实现 PCM 流式播放
 * 豆包 TTS 返回 PCM 格式：24kHz, 16bit, 单声道, 小端序
 */

import { ref, onUnmounted } from 'vue'

export function useAudioPlayer() {
  const isPlaying = ref(false)
  const error = ref(null)

  let audioContext = null
  let nextStartTime = 0
  let isStopped = false
  let scheduledSources = []

  function getAudioContext() {
    if (!audioContext) {
      audioContext = new (window.AudioContext || window.webkitAudioContext)({ sampleRate: 24000 })
    }
    if (audioContext.state === 'suspended') {
      audioContext.resume()
    }
    return audioContext
  }

  function pcmToFloat32(pcmData) {
    const samples = pcmData.length / 2
    const float32 = new Float32Array(samples)
    const view = new DataView(pcmData.buffer, pcmData.byteOffset, pcmData.byteLength)

    for (let i = 0; i < samples; i++) {
      const int16 = view.getInt16(i * 2, true)
      float32[i] = int16 / 32768
    }
    return float32
  }

  function playAudioChunk(audioDataB64) {
    if (isStopped) return

    try {
      const ctx = getAudioContext()

      const binaryString = atob(audioDataB64)
      const pcmData = new Uint8Array(binaryString.length)
      for (let i = 0; i < binaryString.length; i++) {
        pcmData[i] = binaryString.charCodeAt(i)
      }

      const float32Data = pcmToFloat32(pcmData)

      const audioBuffer = ctx.createBuffer(1, float32Data.length, 24000)
      audioBuffer.getChannelData(0).set(float32Data)

      const source = ctx.createBufferSource()
      source.buffer = audioBuffer
      source.connect(ctx.destination)

      const startTime = Math.max(ctx.currentTime, nextStartTime)
      source.start(startTime)
      nextStartTime = startTime + audioBuffer.duration

      scheduledSources.push(source)
      isPlaying.value = true

      source.onended = () => {
        const idx = scheduledSources.indexOf(source)
        if (idx > -1) scheduledSources.splice(idx, 1)
        if (scheduledSources.length === 0) {
          isPlaying.value = false
        }
      }
    } catch (e) {
      error.value = e.message
      console.error('音频播放失败:', e)
    }
  }

  function flush() {
    // PCM 流式播放不需要 flush
  }

  function stop() {
    isStopped = true

    for (const source of scheduledSources) {
      try {
        source.stop()
      } catch {
        // 忽略已停止的错误
      }
    }
    scheduledSources = []
    nextStartTime = 0
    isPlaying.value = false
  }

  function reset() {
    stop()
    isStopped = false
  }

  function cleanup() {
    stop()
    if (audioContext) {
      audioContext.close()
      audioContext = null
    }
  }

  onUnmounted(() => {
    cleanup()
  })

  return {
    isPlaying,
    error,
    playAudioChunk,
    flush,
    stop,
    reset,
    cleanup
  }
}
