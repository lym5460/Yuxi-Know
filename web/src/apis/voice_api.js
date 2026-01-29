/**
 * 语音 API
 *
 * 实现 WebSocket 连接管理和语音配置 API 调用
 * Validates: Requirements 12.1, 12.3
 */

import { useUserStore } from '@/stores/user'
import { apiGet, apiPost } from './base'

/**
 * 获取认证 token
 * @returns {string|null}
 */
function getToken() {
  const userStore = useUserStore()
  return userStore.token || null
}

/**
 * 获取语音消息历史
 * @param {string} threadId - 会话 ID
 * @returns {Promise<Array>} - 语音消息列表
 */
export function getVoiceMessages(threadId) {
  return apiGet(`/api/voice/messages/${threadId}`)
}

/**
 * 保存语音消息
 * @param {string} threadId - 会话 ID
 * @param {Object} message - 消息对象 { role: 'user'|'assistant', content: string }
 * @returns {Promise}
 */
export function saveVoiceMessage(threadId, message) {
  return apiPost(`/api/voice/messages/${threadId}`, message)
}

/**
 * 创建语音 WebSocket 连接
 * @param {string} agentId - 智能体 ID
 * @param {Object} handlers - 事件处理器
 * @returns {WebSocket}
 */
export function createVoiceWebSocket(agentId, handlers = {}) {
  const token = getToken()
  const protocol = window.location.protocol === 'https:' ? 'wss:' : 'ws:'
  const host = window.location.host
  // 使用 /api/voice 路径，与后端路由结构一致
  const url = `${protocol}//${host}/api/voice/ws/voice/${agentId}?token=${token}`

  const ws = new WebSocket(url)

  ws.onopen = () => {
    handlers.onOpen?.()
  }

  ws.onmessage = (event) => {
    try {
      const message = JSON.parse(event.data)
      handlers.onMessage?.(message)
    } catch (e) {
      console.error('Failed to parse message:', e)
    }
  }

  ws.onerror = (error) => {
    handlers.onError?.(error)
  }

  ws.onclose = (event) => {
    handlers.onClose?.(event)
  }

  return ws
}

/**
 * 发送音频数据
 * @param {WebSocket} ws
 * @param {string} audioDataB64 - base64 编码的音频数据
 */
export function sendAudio(ws, audioDataB64) {
  if (ws.readyState === WebSocket.OPEN) {
    ws.send(
      JSON.stringify({
        type: 'audio',
        audio_data: audioDataB64
      })
    )
  }
}

/**
 * 发送控制命令
 * @param {WebSocket} ws
 * @param {'start' | 'stop' | 'interrupt'} action
 */
export function sendControl(ws, action) {
  if (ws.readyState === WebSocket.OPEN) {
    ws.send(
      JSON.stringify({
        type: 'control',
        action
      })
    )
  }
}

/**
 * 发送配置更新
 * @param {WebSocket} ws
 * @param {Object} config
 */
export function sendConfig(ws, config) {
  if (ws.readyState === WebSocket.OPEN) {
    ws.send(
      JSON.stringify({
        type: 'config',
        config
      })
    )
  }
}
