/**
 * 音频采集 Composable
 *
 * 使用 getUserMedia 采集音频，配置回声消除和降噪
 * 支持前端 VAD（语音活动检测），只在检测到语音时发送数据
 */

import { ref, onUnmounted } from 'vue'

export function useAudioCapture(options = {}) {
  const {
    sampleRate = 16000,
    channelCount = 1,
    echoCancellation = true,
    noiseSuppression = true,
    onAudioChunk = null,
    onAudioLevel = null,
    onSpeechStart = null,
    onSpeechEnd = null,
    vadEnabled = true,
    vadThreshold = 0.02,
    vadSilenceMs = 800,
    vadPrefixMs = 300
  } = options

  const isCapturing = ref(false)
  const hasPermission = ref(false)
  const isSpeaking = ref(false)
  const error = ref(null)

  let mediaStream = null
  let audioContext = null
  let processor = null

  // VAD 状态
  let silenceStart = null
  let speechDetected = false
  let audioBuffer = []
  const maxBufferSize = Math.ceil((vadPrefixMs / 1000) * (sampleRate / 4096))

  async function requestPermission() {
    try {
      const stream = await navigator.mediaDevices.getUserMedia({
        audio: {
          sampleRate,
          channelCount,
          echoCancellation,
          noiseSuppression,
          autoGainControl: true
        }
      })
      stream.getTracks().forEach((track) => track.stop())
      hasPermission.value = true
      return true
    } catch (e) {
      error.value = e.message
      hasPermission.value = false
      return false
    }
  }

  async function startCapture() {
    if (isCapturing.value) return

    silenceStart = null
    speechDetected = false
    audioBuffer = []
    isSpeaking.value = false

    // 如果管线已存在（暂停状态），直接恢复，无需重新申请麦克风
    if (processor && audioContext && mediaStream) {
      isCapturing.value = true
      return
    }

    try {
      mediaStream = await navigator.mediaDevices.getUserMedia({
        audio: {
          sampleRate,
          channelCount,
          echoCancellation,
          noiseSuppression,
          autoGainControl: true
        }
      })

      audioContext = new AudioContext({ sampleRate })
      const source = audioContext.createMediaStreamSource(mediaStream)

      processor = audioContext.createScriptProcessor(4096, 1, 1)

      processor.onaudioprocess = (e) => {
        if (!isCapturing.value) return

        const inputData = e.inputBuffer.getChannelData(0)

        // 计算音频电平 (RMS)
        let sum = 0
        for (let i = 0; i < inputData.length; i++) {
          sum += inputData[i] * inputData[i]
        }
        const rms = Math.sqrt(sum / inputData.length)
        const level = Math.min(1, rms * 5)
        onAudioLevel?.(level)

        // 转换为 16-bit PCM
        const pcmData = new Int16Array(inputData.length)
        for (let i = 0; i < inputData.length; i++) {
          pcmData[i] = Math.max(-32768, Math.min(32767, inputData[i] * 32768))
        }

        // 转换为 base64
        const bytes = new Uint8Array(pcmData.buffer)
        const base64 = btoa(String.fromCharCode(...bytes))

        // VAD 处理
        if (vadEnabled) {
          const isVoice = rms > vadThreshold
          const now = Date.now()

          if (isVoice) {
            silenceStart = null

            if (!speechDetected) {
              speechDetected = true
              isSpeaking.value = true
              onSpeechStart?.()

              for (const bufferedChunk of audioBuffer) {
                onAudioChunk?.(bufferedChunk)
              }
              audioBuffer = []
            }

            onAudioChunk?.(base64)
          } else {
            onAudioChunk?.(base64)

            if (speechDetected) {
              if (!silenceStart) {
                silenceStart = now
              }

              if (now - silenceStart > vadSilenceMs) {
                speechDetected = false
                isSpeaking.value = false
                silenceStart = null
                onSpeechEnd?.()
              }
            }
          }
        } else {
          onAudioChunk?.(base64)
        }
      }

      source.connect(processor)
      processor.connect(audioContext.destination)

      isCapturing.value = true
      hasPermission.value = true
      error.value = null
    } catch (e) {
      error.value = e.message
      isCapturing.value = false
    }
  }

  function pauseCapture() {
    isCapturing.value = false
    isSpeaking.value = false
    speechDetected = false
    silenceStart = null
    audioBuffer = []
  }

  function stopCapture() {
    if (processor) {
      processor.disconnect()
      processor = null
    }
    if (audioContext) {
      audioContext.close()
      audioContext = null
    }
    if (mediaStream) {
      mediaStream.getTracks().forEach((track) => track.stop())
      mediaStream = null
    }
    isCapturing.value = false
    isSpeaking.value = false
    speechDetected = false
    silenceStart = null
    audioBuffer = []
  }

  onUnmounted(() => {
    stopCapture()
  })

  return {
    isCapturing,
    hasPermission,
    isSpeaking,
    error,
    requestPermission,
    startCapture,
    pauseCapture,
    stopCapture
  }
}
