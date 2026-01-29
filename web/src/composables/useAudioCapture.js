/**
 * 音频采集 Composable
 *
 * 使用 getUserMedia 采集音频，配置回声消除和降噪
 * 支持前端 VAD（语音活动检测），只在检测到语音时发送数据
 * Validates: Requirements 2.2, 9.1, 9.2, 9.4
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
    // VAD 配置
    vadEnabled = true,
    vadThreshold = 0.02, // 语音检测阈值（RMS）
    vadSilenceMs = 800, // 静音多久后认为语音结束
    vadPrefixMs = 300 // 语音开始前保留的音频时长
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
  let audioBuffer = [] // 缓存最近的音频块，用于保留语音开始前的数据
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

    // 重置 VAD 状态
    silenceStart = null
    speechDetected = false
    audioBuffer = []
    isSpeaking.value = false

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

      // 使用 ScriptProcessor 处理音频（兼容性更好）
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
        // 归一化到 0-1 范围
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
            // 检测到语音
            silenceStart = null

            if (!speechDetected) {
              // 语音开始
              speechDetected = true
              isSpeaking.value = true
              onSpeechStart?.()

              // 发送缓存的音频（语音开始前的数据）
              for (const bufferedChunk of audioBuffer) {
                onAudioChunk?.(bufferedChunk)
              }
              audioBuffer = []
            }

            // 发送当前音频
            onAudioChunk?.(base64)
          } else {
            // 静音 - 始终发送音频，让后端/豆包处理 VAD
            onAudioChunk?.(base64)

            if (speechDetected) {
              // 正在说话中遇到静音
              if (!silenceStart) {
                silenceStart = now
              }

              // 检查是否静音足够长
              if (now - silenceStart > vadSilenceMs) {
                // 语音结束，触发回调但继续发送音频
                speechDetected = false
                isSpeaking.value = false
                silenceStart = null
                onSpeechEnd?.()
              }
            }
          }
        } else {
          // VAD 禁用，直接发送所有音频
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
    stopCapture
  }
}
