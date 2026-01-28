/**
 * 音频播放 Composable
 * 
 * 使用 Web Audio API 播放音频，实现流式音频缓冲
 * 支持立即停止播放（用于智能打断）
 * Validates: Requirements 2.8, 9.6
 */

import { ref, onUnmounted } from 'vue'

export function useAudioPlayer() {
  const isPlaying = ref(false)
  const error = ref(null)

  let audioContext = null
  let audioQueue = []
  let isProcessing = false
  let currentSource = null  // 当前正在播放的音频源
  let isStopped = false     // 停止标志

  function initContext() {
    if (!audioContext) {
      audioContext = new AudioContext()
    }
    return audioContext
  }

  async function playAudioChunk(audioDataB64) {
    // 如果已停止，忽略新的音频
    if (isStopped) return
    
    try {
      initContext()
      
      // 解码 base64
      const binaryString = atob(audioDataB64)
      const bytes = new Uint8Array(binaryString.length)
      for (let i = 0; i < binaryString.length; i++) {
        bytes[i] = binaryString.charCodeAt(i)
      }
      
      // 添加到队列
      audioQueue.push(bytes.buffer)
      
      // 处理队列
      if (!isProcessing) {
        processQueue()
      }
    } catch (e) {
      error.value = e.message
    }
  }

  async function processQueue() {
    if (isProcessing || audioQueue.length === 0 || isStopped) return
    
    isProcessing = true
    isPlaying.value = true

    while (audioQueue.length > 0 && !isStopped) {
      const buffer = audioQueue.shift()
      try {
        const ctx = initContext()
        const audioBuffer = await ctx.decodeAudioData(buffer.slice(0))
        
        // 如果在解码过程中被停止，退出
        if (isStopped) break
        
        const source = ctx.createBufferSource()
        source.buffer = audioBuffer
        source.connect(ctx.destination)
        
        // 保存当前音频源引用，以便可以停止
        currentSource = source
        
        await new Promise((resolve) => {
          source.onended = () => {
            if (currentSource === source) {
              currentSource = null
            }
            resolve()
          }
          source.start()
        })
      } catch (e) {
        // 如果是因为停止导致的错误，忽略
        if (!isStopped) {
          console.error('Failed to play audio chunk:', e)
        }
      }
    }

    isProcessing = false
    if (!isStopped) {
      isPlaying.value = false
    }
  }

  function stop() {
    // 设置停止标志
    isStopped = true
    
    // 清空队列
    audioQueue = []
    
    // 停止当前正在播放的音频
    if (currentSource) {
      try {
        currentSource.stop()
        currentSource.disconnect()
      } catch (e) {
        // 忽略已经停止的音频源错误
      }
      currentSource = null
    }
    
    isProcessing = false
    isPlaying.value = false
    
    console.log('🔇 音频播放已停止')
  }

  function reset() {
    // 重置停止标志，允许新的音频播放
    isStopped = false
    console.log('🔊 音频播放器已重置，准备接收新音频')
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
    stop,
    reset,
    cleanup
  }
}
