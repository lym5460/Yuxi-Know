import { apiGet, apiPost, apiPut, apiDelete } from './base'
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
  },

  getAgentConfigs: (agentId) => apiGet(`/api/chat/agent/${agentId}/configs`),

  getAgentConfigProfile: (agentId, configId) =>
    apiGet(`/api/chat/agent/${agentId}/configs/${configId}`),

  updateAgentConfigProfile: (agentId, configId, payload) =>
    apiPut(`/api/chat/agent/${agentId}/configs/${configId}`, payload),

  getAgentState: (agentId, threadId) =>
    apiGet(`/api/chat/agent/${agentId}/state?thread_id=${threadId}`)
}

// 系统资源 API（用于配置编辑时获取可选项）
export const systemApi = {
  getConfig: () => apiGet('/api/system/config'),
  getTools: () => apiGet('/api/system/tools'),
  getSkills: () => apiGet('/api/system/skills'),
  getAccessibleDatabases: () => apiGet('/api/knowledge/databases/accessible')
}

export const multimodalApi = {
  uploadImage: (file) => {
    const formData = new FormData()
    formData.append('file', file)
    return apiPost('/api/chat/image/upload', formData)
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
    apiPut(`/api/chat/thread/${threadId}`, { title }),

  deleteThread: (threadId) =>
    apiDelete(`/api/chat/thread/${threadId}`),

  uploadThreadAttachment: (threadId, file) => {
    const formData = new FormData()
    formData.append('file', file)
    return apiPost(`/api/chat/thread/${threadId}/attachments`, formData)
  },

  getThreadAttachments: (threadId) =>
    apiGet(`/api/chat/thread/${threadId}/attachments`),

  deleteThreadAttachment: (threadId, fileId) =>
    apiDelete(`/api/chat/thread/${threadId}/attachments/${fileId}`)
}
