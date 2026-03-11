import { defineStore } from 'pinia'
import { ref } from 'vue'
import { agentApi, threadApi } from '@/apis'

export const useChatStore = defineStore('chat', () => {
  const threads = ref([])
  const currentThreadId = ref(null)
  const messages = ref([])
  const isProcessing = ref(false)
  const isLoadingMessages = ref(false)

  async function loadThreads(agentId) {
    if (!agentId) return
    try {
      const result = await threadApi.getThreads(agentId)
      threads.value = result || []
    } catch (e) {
      console.error('加载会话列表失败:', e)
    }
  }

  async function createThread(agentId) {
    try {
      const result = await threadApi.createThread(agentId, '新的对话')
      if (result?.thread_id) {
        currentThreadId.value = result.thread_id
        await loadThreads(agentId)
        messages.value = []
      }
      return result
    } catch (e) {
      console.error('创建会话失败:', e)
    }
  }

  function selectThread(threadId) {
    currentThreadId.value = threadId
    messages.value = []
  }

  async function loadHistory(agentId, threadId) {
    if (!agentId || !threadId) return
    isLoadingMessages.value = true
    try {
      const result = await agentApi.getAgentHistory(agentId, threadId)
      messages.value = result || []
    } catch (e) {
      console.error('加载历史消息失败:', e)
    } finally {
      isLoadingMessages.value = false
    }
  }

  function addMessage(msg) {
    messages.value.push(msg)
  }

  function updateLastAssistantMessage(content) {
    const last = messages.value[messages.value.length - 1]
    if (last && last.role === 'assistant') {
      last.content = content
    }
  }

  function reset() {
    threads.value = []
    currentThreadId.value = null
    messages.value = []
    isProcessing.value = false
  }

  return {
    threads,
    currentThreadId,
    messages,
    isProcessing,
    isLoadingMessages,
    loadThreads,
    createThread,
    selectThread,
    loadHistory,
    addMessage,
    updateLastAssistantMessage,
    reset
  }
})
