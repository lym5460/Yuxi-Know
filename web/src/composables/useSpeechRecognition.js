/**
 * 浏览器语音识别 Composable
 * 
 * 使用 Web Speech API 实现实时语音转文字预览
 * 用于在后端 Whisper 返回最终结果前，给用户即时反馈
 */

import { ref, onUnmounted } from 'vue'

export function useSpeechRecognition(options = {}) {
  const {
    lang = 'zh-CN',
    continuous = true,
    interimResults = true,
    onResult = null,
    onFinalResult = null,
    onError = null,
    onEnd = null
  } = options

  const isSupported = ref(false)
  const isListening = ref(false)
  const transcript = ref('')
  const interimTranscript = ref('')
  const error = ref(null)

  let recognition = null

  // 检查浏览器支持
  const SpeechRecognition = window.SpeechRecognition || window.webkitSpeechRecognition
  isSupported.value = !!SpeechRecognition

  function start() {
    if (!isSupported.value) {
      error.value = '浏览器不支持语音识别'
      return false
    }

    if (isListening.value) return true

    try {
      recognition = new SpeechRecognition()
      recognition.lang = lang
      recognition.continuous = continuous
      recognition.interimResults = interimResults

      recognition.onstart = () => {
        isListening.value = true
        error.value = null
      }

      recognition.onresult = (event) => {
        let interim = ''
        let final = ''

        for (let i = event.resultIndex; i < event.results.length; i++) {
          const result = event.results[i]
          if (result.isFinal) {
            final += result[0].transcript
          } else {
            interim += result[0].transcript
          }
        }

        if (final) {
          transcript.value += final
          onFinalResult?.(final)
        }

        interimTranscript.value = interim
        onResult?.(transcript.value + interim, interim)
      }

      recognition.onerror = (event) => {
        // 忽略 no-speech 和 aborted 错误，这些是正常情况
        if (event.error === 'no-speech' || event.error === 'aborted') {
          return
        }
        error.value = event.error
        onError?.(event.error)
      }

      recognition.onend = () => {
        isListening.value = false
        onEnd?.()
        
        // 如果还需要继续监听，自动重启
        if (continuous && isListening.value) {
          recognition.start()
        }
      }

      recognition.start()
      return true
    } catch (e) {
      error.value = e.message
      return false
    }
  }

  function stop() {
    if (recognition) {
      recognition.stop()
      recognition = null
    }
    isListening.value = false
  }

  function reset() {
    transcript.value = ''
    interimTranscript.value = ''
  }

  onUnmounted(() => {
    stop()
  })

  return {
    isSupported,
    isListening,
    transcript,
    interimTranscript,
    error,
    start,
    stop,
    reset
  }
}
