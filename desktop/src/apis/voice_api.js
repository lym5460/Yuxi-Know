/**
 * 桌面端语音 API
 * 与 web 端的区别：WebSocket URL 从 serverStore 构建，而非 window.location
 */

import { useUserStore } from '@/stores/user'
import { useServerStore } from '@/stores/server'
import { apiGet, apiPost } from './base'

function getToken() {
  const userStore = useUserStore()
  return userStore.token || null
}

export function getVoiceMessages(threadId) {
  return apiGet(`/api/voice/messages/${threadId}`)
}

export function saveVoiceMessage(threadId, message) {
  return apiPost(`/api/voice/messages/${threadId}`, message)
}

export function createVoiceWebSocket(agentId, handlers = {}) {
  const token = getToken()
  const serverStore = useServerStore()
  const url = serverStore.resolveWsUrl(`/api/voice/ws/voice/${agentId}?token=${token}`)

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
