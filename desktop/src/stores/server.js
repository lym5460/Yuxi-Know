import { defineStore } from 'pinia'
import { ref, computed } from 'vue'

export const useServerStore = defineStore(
  'server',
  () => {
    const serverUrl = ref('')
    const isConfigured = computed(() => !!serverUrl.value)

    function setServerUrl(url) {
      // 去除末尾斜杠
      serverUrl.value = url.replace(/\/+$/, '')
    }

    /**
     * 将相对 API 路径转为绝对 URL
     * @param {string} path - 如 '/api/chat/agent'
     * @returns {string} 完整 URL
     */
    function resolveUrl(path) {
      if (!serverUrl.value) {
        console.warn('服务器地址未配置')
        return path
      }
      return serverUrl.value + path
    }

    /**
     * 构建 WebSocket URL
     * @param {string} path - 如 '/api/voice/ws/voice/xxx'
     * @returns {string} ws:// 或 wss:// URL
     */
    function resolveWsUrl(path) {
      if (!serverUrl.value) return path
      const url = new URL(serverUrl.value)
      const wsProtocol = url.protocol === 'https:' ? 'wss:' : 'ws:'
      return `${wsProtocol}//${url.host}${path}`
    }

    function reset() {
      serverUrl.value = ''
    }

    return {
      serverUrl,
      isConfigured,
      setServerUrl,
      resolveUrl,
      resolveWsUrl,
      reset
    }
  },
  {
    persist: true
  }
)
