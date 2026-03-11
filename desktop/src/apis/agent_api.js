import { apiGet, apiPost, apiDelete } from './base'
import { useUserStore } from '@/stores/user'
import { useServerStore } from '@/stores/server'

export const agentApi = {
  getAgents: () => apiGet('/api/chat/agent'),

  getAgentDetail: (agentId) => apiGet(`/api/chat/agent/${agentId}`),

  getDefaultAgent: () => apiGet('/api/chat/default_agent'),

  getAgentHistory: (agentId, threadId) =>
    apiGet(`/api/chat/agent/${agentId}/history?thread_id=${threadId}`),

  sendAgentMessage: (agentId, data, options = {}) => {
    const { signal, headers: extraHeaders, ...restOptions } = options || {}
    const serverStore = useServerStore()
    const userStore = useUserStore()
    const url = serverStore.resolveUrl(`/api/chat/agent/${agentId}`)

    return fetch(url, {
      method: 'POST',
      body: JSON.stringify(data),
      signal,
      headers: {
        'Content-Type': 'application/json',
        ...userStore.getAuthHeaders(),
        ...(extraHeaders || {})
      },
      ...restOptions
    })
  },

  resumeAgentChat: (agentId, data, options = {}) => {
    const { signal, headers: extraHeaders, ...restOptions } = options || {}
    const serverStore = useServerStore()
    const userStore = useUserStore()
    const url = serverStore.resolveUrl(`/api/chat/agent/${agentId}/resume`)

    return fetch(url, {
      method: 'POST',
      body: JSON.stringify(data),
      signal,
      headers: {
        'Content-Type': 'application/json',
        ...userStore.getAuthHeaders(),
        ...(extraHeaders || {})
      },
      ...restOptions
    })
  }
}

export const threadApi = {
  getThreads: (agentId, limit = 100, offset = 0) =>
    apiGet(`/api/chat/threads?agent_id=${agentId}&limit=${limit}&offset=${offset}`),

  createThread: (agentId, title, metadata) =>
    apiPost('/api/chat/thread', {
      agent_id: agentId,
      title: title || '新的对话',
      metadata: metadata || {}
    }),

  updateThread: (threadId, title) =>
    apiPost(`/api/chat/thread/${threadId}`, { title }),

  deleteThread: (threadId) =>
    apiDelete(`/api/chat/thread/${threadId}`)
}
